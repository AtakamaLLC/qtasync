from PySide2.QtCore import QMutex


class PythonicQMutex:
    def __init__(self, default_timeout_ms: int = None, mode=QMutex.NonRecursive):
        self._mutex = QMutex(mode)
        self._default_timeout = default_timeout_ms

    def __enter__(self):
        if not self.tryLock(self._default_timeout):
            raise TimeoutError("QMutex timed out")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mutex.unlock()

    def lock(self):
        return self._mutex.lock()

    def unlock(self):
        return self._mutex.unlock()

    def tryLock(self, timeout: int = 0) -> bool:
        return self._mutex.tryLock(timeout)

    def try_lock(self) -> bool:
        return self._mutex.try_lock()

    def isRecursive(self) -> bool:
        return self._mutex.isRecursive()
