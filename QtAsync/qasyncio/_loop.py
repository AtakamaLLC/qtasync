import sys
import logging
import asyncio
import itertools
import time
from typing import Callable

from QtAsync._env import QCoreApplication, QSocketNotifier, QObject
from QtAsync.qconcurrent._futures import QtThreadPoolExecutor
from QtAsync.types.unbound import SIGNAL_TYPE
from QtAsync.types.bound import PYTHON_TIME
from QtAsync.qasyncio._util import _SimpleTimer, _make_signaller, _fileno

log = logging.getLogger(__name__)


class _QEventLoop(asyncio.BaseEventLoop):
    def __init__(self, *args, **kwargs):
        self.__app = QCoreApplication.instance()
        assert self.__app is not None, "No QCoreApplication has been instantiated"
        self.__last_exit_code = None
        self.__is_running = False
        self.__debug_enabled = False
        self.__default_executor = None
        self.__exception_handler = None
        self._read_notifiers = {}
        self._write_notifiers = {}
        self._rsc_parent = QObject()
        self._timer = _SimpleTimer(parent=self._rsc_parent)

        self.__call_soon_signaller = signaller = _make_signaller(object, tuple)
        self.__call_soon_signal: SIGNAL_TYPE = signaller.signal
        signaller.signal.connect(
            lambda callback, _args: self.call_soon(callback, *_args)
        )
        super().__init__(*args, **kwargs)
        self.set_debug(True)

    def _before_run_forever(self):
        raise NotImplementedError

    def _after_run_forever(self):
        raise NotImplementedError

    def _check_closed(self):
        raise NotImplementedError

    def run_forever(self):
        """Run eventloop forever."""

        if self.__is_running:
            raise RuntimeError("Event loop already running")

        self.__is_running = True
        self._before_run_forever()

        try:
            self.__log_debug("Starting Qt event loop")
            asyncio.events._set_running_loop(self)  # noqa
            try:
                self.__last_exit_code = self.__app.exec_()
            except AttributeError:
                self.__last_exit_code = self.__app.exec()
            except:  # noqa: E722
                log.exception("Failed to run QCoreApplication event loop")
                self.__last_exit_code = -1
            self.__log_debug(
                "Qt event loop ended with result %s", self.__last_exit_code
            )
            return self.__last_exit_code
        finally:
            asyncio.events._set_running_loop(None)  # noqa
            self._after_run_forever()
            self.__is_running = False

    def run_until_complete(self, future):
        """Run until Future is complete."""

        if self.__is_running:
            raise RuntimeError("Event loop already running")

        self.__log_debug("Running %s until complete", future)
        future = asyncio.ensure_future(future, loop=self)

        def stop(*_args):
            self.stop()

        future.add_done_callback(stop)
        try:
            self.run_forever()
        finally:
            future.remove_done_callback(stop)
        self.__app.processEvents()  # run loop one last time to process all the events
        if not future.done():
            raise RuntimeError("Event loop stopped before Future completed.")

        self.__log_debug("Future %s finished running", future)
        return future.result()

    def stop(self):
        """Stop event loop."""
        if not self.__is_running:
            self.__log_debug("Already stopped")
            return

        self.__log_debug("Stopping event loop...")
        self.__is_running = False
        self.__app.exit()
        self.__log_debug("Stopped event loop")

    def is_running(self):
        """Return True if the event loop is running, False otherwise."""
        return self.__is_running

    def close(self):
        """
        Release all resources used by the event loop.

        The loop cannot be restarted after it has been closed.
        """
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        if self.is_closed():
            return

        self.__log_debug("Closing event loop...")
        if self.__default_executor is not None:
            self.__default_executor.shutdown()

        super().close()
        self._timer.stop()
        self._rsc_parent.deleteLater()
        self._timer = None
        self._rsc_parent = None

        for notifier in itertools.chain(
            self._read_notifiers.values(), self._write_notifiers.values()
        ):
            notifier.setEnabled(False)

        self._read_notifiers = None
        self._write_notifiers = None

    def call_later(self, delay: PYTHON_TIME, callback: Callable, *args, context=None):
        """Register callback to be invoked after a certain delay."""
        if asyncio.iscoroutinefunction(callback):
            raise TypeError("coroutines cannot be used with call_later")
        if not callable(callback):
            raise TypeError(
                "callback must be callable: {}".format(type(callback).__name__)
            )
        self._check_closed()

        self.__log_debug(
            "Registering callback %s to be invoked with arguments %s after %s second(s)",
            callback,
            args,
            delay,
        )

        return self._add_callback(
            asyncio.Handle(callback, args, self, context=context), delay
        )

    def _add_callback(self, handle: "asyncio.Handle", delay: PYTHON_TIME = 0):
        return self._timer.add_callback(handle, delay)

    def call_soon(self, callback: Callable, *args, context=None):
        """Register a callback to be run on the next iteration of the event loop."""
        return self.call_later(0, callback, *args, context=context)

    def call_at(self, when: PYTHON_TIME, callback: Callable, *args, context=None):
        """Register callback to be invoked at a certain time."""
        return self.call_later(when - self.time(), callback, *args, context=context)

    def time(self) -> PYTHON_TIME:
        """Get time according to event loop's clock."""
        return PYTHON_TIME(time.monotonic())

    def _add_reader(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for reading."""
        self._check_closed()

        try:
            existing = self._read_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated["int"].disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QSocketNotifier(_fileno(fd), QSocketNotifier.Type.Read)
        notifier.setEnabled(True)
        self.__log_debug("Adding reader callback for file descriptor %s", fd)
        notifier.activated["int"].connect(
            lambda: self.__on_notifier_ready(
                self._read_notifiers, notifier, fd, callback, args
            )  # noqa: C812
        )
        self._read_notifiers[fd] = notifier

    def _remove_reader(self, fd):
        """Remove reader callback."""
        if self.is_closed():
            return

        self.__log_debug("Removing reader callback for file descriptor %s", fd)
        try:
            notifier = self._read_notifiers.pop(fd)
        except KeyError:
            return False
        else:
            notifier.setEnabled(False)
            return True

    def _add_writer(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for writing."""
        self._check_closed()
        try:
            existing = self._write_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated["int"].disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QSocketNotifier(
            _fileno(fd),
            QSocketNotifier.Type.Write,
        )
        notifier.setEnabled(True)
        self.__log_debug("Adding writer callback for file descriptor %s", fd)
        notifier.activated["int"].connect(
            lambda: self.__on_notifier_ready(
                self._write_notifiers, notifier, fd, callback, args
            )  # noqa: C812
        )
        self._write_notifiers[fd] = notifier

    def _remove_writer(self, fd):
        """Remove writer callback."""
        if self.is_closed():
            return

        self.__log_debug("Removing writer callback for file descriptor %s", fd)
        try:
            notifier = self._write_notifiers.pop(fd)
        except KeyError:
            return False
        else:
            notifier.setEnabled(False)
            return True

    def __notifier_cb_wrapper(self, notifiers, notifier, fd, callback, args):
        # This wrapper gets called with a certain delay. We cannot know
        # for sure that the notifier is still the current notifier for
        # the fd.
        if notifiers.get(fd, None) is not notifier:
            return
        try:
            callback(*args)
        finally:
            # The notifier might have been overriden by the
            # callback. We must not re-enable it in that case.
            if notifiers.get(fd, None) is notifier:
                notifier.setEnabled(True)
            else:
                notifier.activated["int"].disconnect()

    def __on_notifier_ready(self, notifiers, notifier, fd, callback, args):
        if fd not in notifiers:
            log.warning(
                "Socket notifier for fd %s is ready, even though it should "
                "be disabled, not calling %s and disabling",
                fd,
                callback,
            )
            notifier.setEnabled(False)
            return

        # It can be necessary to disable QSocketNotifier when e.g. checking
        # ZeroMQ sockets for events
        assert notifier.isEnabled()
        self.__log_debug("Socket notifier for fd %s is ready", fd)
        notifier.setEnabled(False)
        self.call_soon(
            self.__notifier_cb_wrapper, notifiers, notifier, fd, callback, args
        )

    # Methods for interacting with threads.

    def call_soon_threadsafe(self, callback, *args, context=None):
        """Thread-safe version of call_soon."""
        self.__call_soon_signal.emit(callback, args)

    def run_in_executor(self, executor, callback, *args):
        """Run callback in executor.

        If no executor is provided, the default executor will be used, which defers execution to
        a background thread.
        """
        self.__log_debug("Running callback %s with args %s in executor", callback, args)
        if isinstance(callback, asyncio.Handle):
            assert not args
            assert not isinstance(callback, asyncio.TimerHandle)
            if callback.cancelled():
                f = asyncio.Future()
                f.set_result(None)
                return f
            callback, args = callback._callback, callback._args

        if executor is None:
            self.__log_debug("Using default executor")
            executor = self.__default_executor

        if executor is None:
            self.__log_debug("Creating default executor")
            executor = self.__default_executor = QtThreadPoolExecutor()

        return asyncio.wrap_future(executor.submit(callback, *args))

    def set_default_executor(self, executor):
        self.__default_executor = executor

    # Error handlers.

    def set_exception_handler(self, handler):
        log.info("Changing exception handler to %s", handler)
        self.__exception_handler = handler

    def default_exception_handler(self, context):
        """Handle exceptions.

        This is the default exception handler.

        This is called when an exception occurs and no exception
        handler is set, and can be called by a custom exception
        handler that wants to defer to the default behavior.

        context parameter has the same meaning as in
        `call_exception_handler()`.
        """
        self.__log_debug("Default exception handler executing")
        message = context.get("message")
        if not message:
            message = "Unhandled exception in event loop"

        try:
            exception = context["exception"]
        except KeyError:
            exc_info = False
        else:
            exc_info = (type(exception), exception, exception.__traceback__)

        log_lines = [message]
        for key in [k for k in sorted(context) if k not in {"message", "exception"}]:
            log_lines.append("{}: {!r}".format(key, context[key]))

        self.__log_error("\n".join(log_lines), exc_info=exc_info)

    def call_exception_handler(self, context):
        log.info("call exception handler, %s", context)
        if self.__exception_handler is None:
            try:
                self.default_exception_handler(context)
            except Exception:
                # Second protection layer for unexpected errors
                # in the default implementation, as well as for subclassed
                # event loops with overloaded "default_exception_handler".
                self.__log_error(
                    "Exception in default exception handler", exc_info=True
                )

            return

        try:
            self.__exception_handler(self, context)
        except Exception as exc:
            # Exception in the user set custom exception handler.
            try:
                # Let's try the default handler.
                self.default_exception_handler(
                    {
                        "message": "Unhandled error in custom exception handler",
                        "exception": exc,
                        "context": context,
                    }
                )
            except Exception:
                # Guard 'default_exception_handler' in case it's
                # overloaded.
                self.__log_error(
                    "Exception in default exception handler while handling an unexpected error "
                    "in custom exception handler",
                    exc_info=True,
                )

    # Debug flag management.

    def get_debug(self):
        return self.__debug_enabled

    def set_debug(self, enabled):
        super().set_debug(enabled)
        self.__debug_enabled = enabled
        self._timer.set_debug(enabled)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        self.close()

    def __log_debug(self, *args, **kwargs):
        if self.__debug_enabled:
            log.debug(*args, **kwargs)

    @classmethod
    def __log_error(cls, *args, **kwds):
        # In some cases, the error method itself fails, don't have a lot of options in that case
        try:
            log.error(*args, **kwds)
        except:  # noqa E722
            sys.stderr.write("{!r}, {!r}\n".format(args, kwds))
