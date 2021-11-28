from enum import Enum
from typing import Callable, Any, Iterable, Optional, Iterator, TypeVar, Union, TYPE_CHECKING
from concurrent.futures import Executor, Future

from PySide2.QtCore import QObject, Signal, QThreadPool, QRunnable, Slot

from .locks import PythonicQMutex

if TYPE_CHECKING:
    from PySide2.QtCore import SignalInstance  # noqa: F401

_SIGNAL_TYPE = Union["Signal", "SignalInstance"]


class FutureStatus(Enum):
    PENDING = 1
    RUNNING = 2
    CANCELLED = 3
    CANCELLED_AND_NOTIFIED = 4
    FINISHED = 5


class _QRunnable(QRunnable):
    def __init__(self, fn: Callable):
        super().__init__()
        self._fn = fn

    def run(self):
        self._fn()


class PythonicQFuture(QObject, Future):
    def __init__(self, fn: Callable, *fn_args, parent: "QObject" = None, **fn_kwargs):
        super().__init__(parent=parent)
        self._fn = fn
        self._fn_args = fn_args
        self._fn_kwargs = fn_kwargs

        self._runnable = _QRunnable(self._run)
        self._result: Optional[Any] = None
        self._exception: Optional[BaseException] = None

        self._state_mutex = PythonicQMutex()
        self._state: "FutureStatus" = FutureStatus.PENDING

    @property
    def runnable(self) -> "_QRunnable":
        return self._runnable

    def cancel(self) -> bool:
        pass

    def cancelled(self) -> bool:
        with self._state_mutex:
            return self._state in [FutureStatus.CANCELLED, FutureStatus.CANCELLED_AND_NOTIFIED]

    def running(self) -> bool:
        with self._state_mutex:
            return self._state == FutureStatus.RUNNING

    def done(self) -> bool:
        with self._state_mutex:
            return self._state in [FutureStatus.CANCELLED, FutureStatus.CANCELLED_AND_NOTIFIED, FutureStatus.FINISHED]

    def result(self, timeout: Optional[float] = None):
        pass

    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        pass

    def add_done_callback(self, fn: Callable[["PythonicQFuture"], Any]) -> None:
        pass

    # Testing and Executor usage
    def set_running_or_notify_cancel(self) -> bool:
        pass

    def set_result(self, result) -> None:
        pass

    def set_exception(self, exception: Optional[BaseException]) -> None:
        pass

    # Protected
    @Slot
    def _run(self):
        res = self._fn(*self._fn_args, **self._fn_kwargs)


class QThreadPoolExecutor(Executor):
    def __init__(self, qthread_pool: "QThreadPool" = None):
        self._pool = qthread_pool or QThreadPool.globalInstance()

    def submit(self, fn, /, *args, **kwargs) -> PythonicQFuture:
        future = PythonicQFuture(fn, *args, **kwargs)
        self._pool.start(future.runnable)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        pass
