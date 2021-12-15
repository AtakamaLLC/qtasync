import logging
import os
import subprocess
import socket
import functools
import time
from enum import Enum
from typing import TYPE_CHECKING, Callable, Any, Optional, Union, Sequence, Dict
from concurrent.futures import Executor, Future, CancelledError, InvalidStateError
from concurrent.futures import TimeoutError as FutureTimeoutError
import asyncio

from PySide2.QtCore import (
    QObject,
    Signal,
    QThreadPool,
    QRunnable,
    QCoreApplication,
    QTimer,
)

from .locks import PythonicQMutex, PythonicQWaitCondition
from ..util import qt_timeout
from ..types.bound import PYTHON_TIME
from ..types.unbound import SIGNAL_TYPE

if TYPE_CHECKING:
    from types import CoroutineType
    from PySide2.QtCore import SignalInstance  # noqa: F401

log = logging.getLogger(__name__)


ASYNCIO_TIME = Union[int, float]


class FutureStatus(Enum):
    PENDING = 1
    RUNNING = 2
    CANCELLED = 3
    CANCELLED_AND_NOTIFIED = 4
    FINISHED = 5


class _QRunnable(QRunnable):
    def __init__(self, future: "PythonicQFuture", fn: Callable, args, kwargs):
        super().__init__()
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as ex:
            self.future.set_exception(ex)
            # Copied from concurrent.futures.thread._WorkItem.run()
            # self = None
        else:
            self.future.set_result(result)


class PythonicQFuture(QObject, Future):
    _finished: SIGNAL_TYPE = Signal()

    def __init__(self, parent: "QObject" = None):
        super().__init__(parent=parent)
        self._id = os.urandom(8).hex()

        self._result: Optional[Any] = None
        self._exception: Optional[BaseException] = None

        self._cond = PythonicQWaitCondition()
        self._state: "FutureStatus" = FutureStatus.PENDING

    @property
    def future_id(self) -> str:
        return self._id

    def cancel(self) -> bool:
        with self._cond:
            if self._state in [FutureStatus.FINISHED, FutureStatus.RUNNING]:
                return False
            elif self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]:
                return True

            self._state = FutureStatus.CANCELLED
            self._cond.notify_all()

    def cancelled(self) -> bool:
        with self._cond:
            return self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]

    def running(self) -> bool:
        with self._cond:
            return self._state == FutureStatus.RUNNING

    def done(self) -> bool:
        with self._cond:
            return self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
                FutureStatus.FINISHED,
            ]

    def __get_result(self):
        if self._exception:
            raise self._exception
        else:
            return self._result

    def result(self, timeout: Optional[PYTHON_TIME] = None):
        with self._cond:
            if self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]:
                raise CancelledError()
            elif self._state == FutureStatus.FINISHED:
                return self.__get_result()

            if not self._cond.wait(timeout=timeout):
                raise FutureTimeoutError

            if self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]:
                raise CancelledError()
            elif self._state == FutureStatus.FINISHED:
                return self.__get_result()
            else:
                raise FutureTimeoutError()

    def exception(
        self, timeout: Optional[PYTHON_TIME] = None
    ) -> Optional[BaseException]:
        with self._cond:
            if self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]:
                raise CancelledError()
            elif self._state == FutureStatus.FINISHED:
                return self._exception

            self._cond.wait(timeout=timeout)

            if self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
            ]:
                raise CancelledError()
            elif self._state == FutureStatus.FINISHED:
                return self._exception
            else:
                raise TimeoutError()

    def add_done_callback(self, fn: Callable[["PythonicQFuture"], Any]) -> None:
        with self._cond:
            if not self._state in [
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
                FutureStatus.FINISHED,
            ]:
                self._finished.connect(lambda: fn(self))
                return

        try:
            fn(self)
        except:  # noqa: E722
            log.exception("Error when calling PythonicQFuture done callback")

    # Testing and Executor usage
    def set_running_or_notify_cancel(self) -> bool:
        with self._cond:
            if self._state == FutureStatus.CANCELLED:
                self._state = FutureStatus.CANCELLED_AND_NOTIFIED
                return False
            elif self._state == FutureStatus.PENDING:
                self._state = FutureStatus.RUNNING
                return True
            else:
                log.critical("Future %s in unexpected state: %s", id(self), self._state)
                raise RuntimeError("Future in unexpected state")

    def set_result(self, result) -> None:
        with self._cond:
            if self._state in (
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
                FutureStatus.FINISHED,
            ):
                raise InvalidStateError("{}: {!r}".format(self._state, self))
            self._result = result
            self._state = FutureStatus.FINISHED
            self._cond.notify_all()
            self._finished.emit()

    def set_exception(self, exception: Optional[BaseException]) -> None:
        with self._cond:
            if self._state in (
                FutureStatus.CANCELLED,
                FutureStatus.CANCELLED_AND_NOTIFIED,
                FutureStatus.FINISHED,
            ):
                raise InvalidStateError("{}: {!r}".format(self._state, self))
            self._exception = exception
            self._state = FutureStatus.FINISHED
            self._cond.notify_all()
            self._finished.emit()


class QThreadPoolExecutor(Executor):
    def __init__(self, qthread_pool: "QThreadPool" = None):
        self._pool = qthread_pool or QThreadPool.globalInstance()
        self._shutdown_mutex = PythonicQMutex()
        self._is_shutdown = False

    def submit(self, fn, /, *args, **kwargs) -> PythonicQFuture:
        with self._shutdown_mutex:
            if self._is_shutdown:
                raise RuntimeError
            future = PythonicQFuture(parent=self._pool)
            runnable = _QRunnable(future, fn, args, kwargs)
            self._pool.start(runnable)
            return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_mutex:
            self._is_shutdown = True

        if cancel_futures:
            self._pool.clear()

        if wait:
            self._pool.waitForDone()


# Based partiall on https://github.com/CabbageDevelopment/qasync/blob/master/qasync/__init__.py
class PythonicQEventLoop(asyncio.AbstractEventLoop):
    def __init__(self):
        super().__init__()
        asyncio.set_event_loop(self)
        self._qapp = QCoreApplication.instance() or QCoreApplication()
        self._last_exit_code: Optional[int] = None
        self._resource_parent = QObject()
        self._executor: Optional["QThreadPoolExecutor"] = None
        self._state_mutex = PythonicQMutex(recursive=True)
        self._is_running = False
        self._is_closed = False
        self._task_factory: Optional[Callable[["CoroutineType"], "asyncio.Task"]] = None

        # Debug vars
        self._debug_enabled = False
        self._exception_handler: Optional[Callable[[Dict], None]] = None

    def _assert_not_running(self):
        with self._state_mutex:
            if self._is_running:
                raise RuntimeError("PythonicQEventLoop is already running")

    def _assert_not_closed(self):
        with self._state_mutex:
            if self._is_closed:
                raise RuntimeError("PythonicQEventLoop has already closed")

    def last_exit_code(self) -> Optional[int]:
        return self._last_exit_code

    def run_forever(self) -> None:
        with self._state_mutex:
            self._assert_not_running()
            self._is_running = True
        try:
            self._last_exit_code = self._qapp.exec_()
        finally:
            with self._state_mutex:
                self._is_running = False

    def run_until_complete(self, future: Union["PythonicQFuture", "CoroutineType"]):
        self._assert_not_running()
        fut = asyncio.ensure_future(future, loop=self)
        fut.add_done_callback(lambda _: self.stop)
        self.run_forever()
        return fut.result()

    def stop(self):
        self._qapp.quit()

    def is_running(self) -> bool:
        with self._state_mutex:
            return self._is_running

    def is_closed(self) -> bool:
        with self._state_mutex:
            return self._is_closed

    def close(self):
        with self._state_mutex:
            self._assert_not_running()
            if self._is_closed:
                return

            try:
                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)

                self._resource_parent.deleteLater()
            finally:
                self._is_closed = True

    async def shutdown_asyncgens(self):
        raise NotImplementedError

    async def shutdown_default_executor(self):
        raise NotImplementedError

    # Methods scheduling callbacks.  All these return Handles.

    def _timer_handle_cancelled(self, handle):
        raise NotImplementedError

    def call_soon(self, callback, *args, context=None):
        return self.call_later(0, callback, *args, context=context)

    def call_later(
        self, delay: ASYNCIO_TIME, callback: Callable, *args, context=None
    ) -> "QHandle":
        timer = PythonicQTimer.singleShot(
            delay, functools.partial(callback, *args), parent=self._resource_parent
        )
        return QHandle(callback, args, self, timer, context=context)

    def call_at(
        self, when: ASYNCIO_TIME, callback: Callable, *args, context=None
    ) -> "QHandle":
        return self.call_later(when - time.time(), callback, *args, context=context)

    def time(self):
        return time.monotonic()

    def create_future(self) -> "PythonicQFuture":
        return PythonicQFuture(parent=self._resource_parent)

    # Method scheduling a coroutine object: create a task.

    def create_task(self, coro: "CoroutineType", *, name=None) -> "asyncio.Task":
        self._assert_not_closed()
        if not self._task_factory:
            task = asyncio.tasks.Task(coro, loop=self, name=name)
        else:
            task = self._task_factory(coro)
            task.set_name(name)
        return task

    # Methods for interacting with threads.

    def call_soon_threadsafe(self, callback, *args):
        raise NotImplementedError

    async def run_in_executor(
        self, executor: Optional["Executor"], func: Callable, *args
    ) -> "Future":
        executor = executor or self._executor
        return asyncio.wrap_future(executor.submit(func, *args), loop=self)

    def set_default_executor(self, executor: "Executor"):
        self._executor = executor

    # Network I/O methods returning Futures.

    async def getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
        raise NotImplementedError

    async def getnameinfo(self, sockaddr, flags=0):
        raise NotImplementedError

    async def create_connection(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
        sock=None,
        local_addr=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        happy_eyeballs_delay=None,
        interleave=None,
    ):
        raise NotImplementedError

    async def create_server(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        family=socket.AF_UNSPEC,
        flags=socket.AI_PASSIVE,
        sock=None,
        backlog=100,
        ssl=None,
        reuse_address=None,
        reuse_port=None,
        ssl_handshake_timeout=None,
        start_serving=True,
    ):
        raise NotImplementedError

    async def sendfile(self, transport, file, offset=0, count=None, *, fallback=True):
        raise NotImplementedError

    async def start_tls(
        self,
        transport,
        protocol,
        sslcontext,
        *,
        server_side=False,
        server_hostname=None,
        ssl_handshake_timeout=None,
    ):
        raise NotImplementedError

    async def create_unix_connection(
        self,
        protocol_factory,
        path=None,
        *,
        ssl=None,
        sock=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
    ):
        raise NotImplementedError

    async def create_unix_server(
        self,
        protocol_factory,
        path=None,
        *,
        sock=None,
        backlog=100,
        ssl=None,
        ssl_handshake_timeout=None,
        start_serving=True,
    ):
        raise NotImplementedError

    async def create_datagram_endpoint(
        self,
        protocol_factory,
        local_addr=None,
        remote_addr=None,
        *,
        family=0,
        proto=0,
        flags=0,
        reuse_address=None,
        reuse_port=None,
        allow_broadcast=None,
        sock=None,
    ):
        raise NotImplementedError

    # Pipes and subprocesses.

    async def connect_read_pipe(self, protocol_factory, pipe):
        raise NotImplementedError

    async def connect_write_pipe(self, protocol_factory, pipe):
        raise NotImplementedError

    async def subprocess_shell(
        self,
        protocol_factory,
        cmd,
        *,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    ):
        raise NotImplementedError

    async def subprocess_exec(
        self,
        protocol_factory,
        *args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    ):
        raise NotImplementedError

    def add_reader(self, fd, callback, *args):
        raise NotImplementedError

    def remove_reader(self, fd):
        raise NotImplementedError

    def add_writer(self, fd, callback, *args):
        raise NotImplementedError

    def remove_writer(self, fd):
        raise NotImplementedError

    # Completion based I/O methods returning Futures.

    async def sock_recv(self, sock, nbytes):
        raise NotImplementedError

    async def sock_recv_into(self, sock, buf):
        raise NotImplementedError

    async def sock_sendall(self, sock, data):
        raise NotImplementedError

    async def sock_connect(self, sock, address):
        raise NotImplementedError

    async def sock_accept(self, sock):
        raise NotImplementedError

    async def sock_sendfile(self, sock, file, offset=0, count=None, *, fallback=None):
        raise NotImplementedError

    # Signal handling.

    def add_signal_handler(self, sig, callback, *args):
        raise NotImplementedError

    def remove_signal_handler(self, sig):
        raise NotImplementedError

    # Task factory.

    def set_task_factory(
        self, factory: Optional[Callable[["CoroutineType"], "asyncio.Task"]]
    ):
        self._task_factory = factory

    def get_task_factory(self) -> Optional[Callable[["CoroutineType"], "asyncio.Task"]]:
        return self._task_factory

    # Error handlers.

    def get_exception_handler(self) -> Optional[Callable[[Dict], None]]:
        return self._exception_handler or self.default_exception_handler

    def set_exception_handler(self, handler: Optional[Callable[[Dict], None]]):
        self._exception_handler = handler

    def default_exception_handler(self, context: Dict):
        log.exception(context)

    def call_exception_handler(self, context: Dict):
        self.get_exception_handler()(context)

    # Debug flag management.

    def get_debug(self) -> bool:
        return self._debug_enabled

    def set_debug(self, enabled: bool):
        self._debug_enabled = enabled


class PythonicQTimer(QTimer):
    def cancel(self):
        self.stop()

    @classmethod
    def singleShot(
        cls, duration: PYTHON_TIME, func: Callable[[], Any], parent: "QObject" = None
    ) -> "PythonicQTimer":
        t = cls(parent=parent)
        t.setSingleShot(True)
        t.setInterval(qt_timeout(duration))
        t.timeout.connect(func)
        t.start()
        return t


class QHandle(asyncio.Handle):
    def __init__(
        self,
        callback: Callable[..., Any],
        args: Sequence[Any],
        loop: "PythonicQEventLoop",
        timer: "PythonicQTimer",
        context=None,
    ):
        super().__init__(callback, args, loop, context=context)
        self._timer = timer

    def cancel(self):
        self._timer.cancel()
