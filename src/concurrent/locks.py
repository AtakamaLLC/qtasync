from typing import Optional

from PySide2.QtCore import QMutex, QObject, QWaitCondition

from ..types.unbound import SIGNAL_TYPE
from ..types.bound import QT_TIME, PYTHON_TIME
from ..util import qt_timeout, mk_q_deadline_timer


class PythonicQMutex:
    def __init__(self, default_timeout: PYTHON_TIME = 0, recursive: bool = False):
        self._mutex = QMutex(QMutex.Recursive if recursive else QMutex.NonRecursive)
        self._default_timeout = qt_timeout(default_timeout)

    def __enter__(self):
        if not self.tryLock(self._default_timeout):
            raise TimeoutError("QMutex timed out")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mutex.unlock()

    def lock(self):
        return self._mutex.lock()

    def unlock(self):
        return self._mutex.unlock()

    def tryLock(self, timeout: QT_TIME = 0) -> bool:
        return self._mutex.tryLock(timeout)

    def try_lock(self) -> bool:
        return self._mutex.try_lock()

    def isRecursive(self) -> bool:
        return self._mutex.isRecursive()


class PythonicQWaitCondition:
    def __init__(self):
        self._mutex = PythonicQMutex()
        self._cond = QWaitCondition()

    def __enter__(self):
        self._mutex.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mutex.unlock()

    def acquire(self):
        self._mutex.lock()

    def release(self):
        self._mutex.unlock()

    def wait(self, timeout: PYTHON_TIME = None) -> bool:
        return self._cond.wait(self._mutex._mutex, mk_q_deadline_timer(timeout))

    def notify_all(self):
        self._cond.wakeAll()

    def notify(self):
        self._cond.wakeOne()


class QThreadEvent(QObject):
    destroyed: SIGNAL_TYPE

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._is_set = False
        self._flag_mutex = PythonicQMutex()
        self._cond = PythonicQWaitCondition()

    def is_set(self) -> bool:
        with self._flag_mutex:
            return self._is_set

    def set(self):
        with self._flag_mutex:
            if not self._is_set:
                self._is_set = True
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

        return self._cond.wait(timeout)


