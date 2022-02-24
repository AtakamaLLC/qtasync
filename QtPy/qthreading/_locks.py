import logging
from typing import Optional, Union, Tuple, Callable, Any

from QtPy._env import (
    QSemaphore,
    QMutex,
    QRecursiveMutex,
    QWaitCondition,
    QtModuleName,
    PYQT5_MODULE_NAME,
    PYQT6_MODULE_NAME,
    PYSIDE6_MODULE_NAME,
    QElapsedTimer,
)

from QtPy.types.bound import QT_TIME, PYTHON_TIME
from QtPy._util import qt_timeout, mk_q_deadline_timer, py_timeout

log = logging.getLogger(__name__)


def _get_ident() -> int:
    import threading

    try:
        return threading.get_native_id()
    except:  # noqa
        return threading.get_ident()


class _QtLock:
    def __init__(self, default_timeout: PYTHON_TIME = -1, recursive: bool = False):
        """
        :param default_timeout: A divergence from Python's Lock/RLock, this parameter can
            be used to set a timeout used by the mutex when acquired in a `with` block (or
            if you explicitly call __enter__())
        :param recursive: Whether or not the mutex can be re-acquired by the same thread
        """
        if QtModuleName in (PYQT6_MODULE_NAME, PYSIDE6_MODULE_NAME):
            self._mutex = QRecursiveMutex() if recursive else QMutex()
        else:
            self._mutex = QMutex(QMutex.Recursive if recursive else QMutex.NonRecursive)
        self._default_timeout: QT_TIME = qt_timeout(default_timeout)

    # Python methods to match threading.Lock/RLock's interface
    def __enter__(self):
        if not self._try_lock(timeout=self._default_timeout):
            raise TimeoutError("QMutex timed out")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, blocking=True, timeout: PYTHON_TIME = -1.0):
        if blocking:
            # Negative timeout in a QMutex behaves the same as a Python lock
            return self._try_lock(timeout=qt_timeout(timeout))
        else:
            if timeout != -1.0:
                raise ValueError("Cannot specify a timeout for a non-blocking call")
            return self._try_lock()

    def release(self):
        self._mutex.unlock()

    @property
    def default_timeout(self) -> float:
        return self._default_timeout

    @default_timeout.setter
    def default_timeout(self, new_timeout: float):
        self._default_timeout = qt_timeout(new_timeout)

    def is_recursive(self) -> bool:
        return self._mutex.isRecursive()

    def _try_lock(self, timeout: QT_TIME = None) -> bool:
        if timeout is None:
            if QtModuleName in (PYQT5_MODULE_NAME, PYQT6_MODULE_NAME):
                return self._mutex.tryLock()
            else:
                return self._mutex.try_lock()
        else:
            return self._mutex.tryLock(timeout)

    def _acquire_restore(self, _state):
        raise NotImplementedError

    def _release_save(self):
        raise NotImplementedError

    def _is_owned(self) -> bool:
        raise NotImplementedError


class QtRLock(_QtLock):
    def __init__(self, default_timeout: PYTHON_TIME = -1):
        super().__init__(default_timeout=default_timeout, recursive=True)
        self._owner = None
        self._count = 0

    def _try_lock(self, timeout: QT_TIME = None) -> bool:
        me = _get_ident()
        if self._owner == me:
            self._count += 1
            return True
        ret = super()._try_lock(timeout=timeout)
        if ret:
            self._owner = me
            self._count = 1
        return ret

    def release(self):
        if self._owner != _get_ident():
            raise RuntimeError("Cannot release un-acquired QtRLock")
        self._count -= 1
        if self._count == 0:
            self._owner = None
            super().release()

    def _acquire_restore(self, state: Tuple[int, int]):
        self.acquire()
        self._count, self._owner = state

    def _release_save(self) -> Tuple[int, int]:
        if self._count == 0:
            raise RuntimeError("Cannot release un-acquired QtRLock")
        count = self._count
        self._count = 0
        owner = self._owner
        self._owner = None
        # self.release()
        return count, owner

    def _is_owned(self) -> bool:
        return _get_ident() == self._owner


class QtLock(_QtLock):
    def __init__(self, default_timeout: PYTHON_TIME = -1):
        super().__init__(default_timeout=default_timeout, recursive=False)

    def _acquire_restore(self, _state):
        # self.acquire()
        pass

    def _release_save(self):
        # self.release()
        pass

    def _is_owned(self):
        if self.acquire(blocking=False):
            self.release()
            return False
        else:
            return True


class QtCondition:
    def __init__(self, lock: Union["QtLock", "QtRLock"] = None):
        self._mutex = lock or QtLock()
        # Cannot use a recursive mutex in Qt 5
        # See: https://github.com/qt/qtbase/blob/5.15.2/src/corelib/thread/qwaitcondition_unix.cpp#L217
        #  and https://github.com/qt/qtbase/blob/5.15.2/src/corelib/thread/qwaitcondition_win.cpp#L171
        # TODO: If using Qt 6, allow recursive mutexes as long as the mutex is not recursively locked
        #   see: https://github.com/qt/qtbase/blob/6.3/src/corelib/thread/qwaitcondition_win.cpp#L189
        assert not isinstance(self._mutex, QtRLock)
        self._cond = QWaitCondition()

    # Python methods to match threading.Condition
    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, blocking=True, timeout: PYTHON_TIME = -1.0):
        return self._mutex.acquire(blocking=blocking, timeout=timeout)

    def release(self):
        if not self._mutex._is_owned():
            raise RuntimeError("Cannot release un-acquired lock")
        self._mutex.release()

    def wait(self, timeout: PYTHON_TIME = None) -> bool:
        # Since the underlying mutex is not recursive, we can ensure that the mutex is locked by simply attempting to
        # lock it without blocking
        if not self._mutex._is_owned():
            raise RuntimeError("Cannot wait on un-acquired lock")

        state = self._mutex._release_save()
        try:
            if timeout is None:
                return self._cond.wait(self._mutex._mutex)
            else:
                if QtModuleName == PYQT5_MODULE_NAME:
                    # For some reason, the QDeadlineTimer does not work with PyQt5 and wait() instantly returns
                    return self._cond.wait(
                        self._mutex._mutex, msecs=qt_timeout(timeout)
                    )
                else:
                    return self._cond.wait(
                        self._mutex._mutex, mk_q_deadline_timer(timeout)
                    )
        finally:
            self._mutex._acquire_restore(state)

    def wait_for(self, predicate: Callable[[], Any], timeout: PYTHON_TIME = None):
        """
        Largely a copy of threading.Condition.wait_for()
        """
        timer = None
        waittime = qt_timeout(timeout)
        result = predicate()
        while not result:
            if waittime is not None:
                if timer is None:
                    timer = QElapsedTimer()
                    timer.start()
                else:
                    # New waittime is remaining wait time minus the time elapsed since the timer was last (re)started
                    waittime -= timer.restart()
                    if waittime <= 0:
                        break
            self.wait(py_timeout(waittime))
            result = predicate()
        return result

    def notify_all(self):
        if not self._mutex._is_owned():
            raise RuntimeError("Cannot notify all on un-acquired lock")
        self._cond.wakeAll()

    def notify(self):
        if not self._mutex._is_owned():
            raise RuntimeError("Cannot notify on un-acquired lock")
        self._cond.wakeOne()


class QtEvent:
    def __init__(self):
        self._is_set = False
        self._flag_mutex = QtLock()
        self._cond = QtCondition()

    def is_set(self) -> bool:
        with self._flag_mutex:
            return self._is_set

    def set(self):
        with self._flag_mutex:
            if not self._is_set:
                self._is_set = True
                with self._cond:
                    self._cond.notify_all()

    def clear(self):
        with self._flag_mutex:
            self._is_set = False

    def wait(self, timeout: Optional[PYTHON_TIME] = None) -> bool:
        """
        This wait function is designed to emulate threading.Event.wait()

        :param timeout: The time to wait before timing out in seconds
        """
        # Lock the event flag first
        with self._flag_mutex:
            if self._is_set:
                return True

        with self._cond:
            return self._cond.wait(timeout)


class QtSemaphore(QSemaphore):
    def __init__(self, value=1):
        super().__init__(n=value)

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def release(self, n=1):
        return super().release(n=n)

    def acquire(self, blocking=True, timeout: PYTHON_TIME = None) -> bool:
        if blocking:
            return self.tryAcquire(1, qt_timeout(timeout))
        else:
            return self.tryAcquire(1)
