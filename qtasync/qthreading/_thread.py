import threading
from typing import TYPE_CHECKING, Optional

from qtasync._env import QThread
from qtasync._util import qt_timeout
from qtasync.types.bound import PYTHON_TIME

if TYPE_CHECKING:
    from qtasync._env import QObject


class QtThread(QThread):
    def __init__(
        self,
        target=None,
        name=None,
        args: list = None,
        kwargs: dict = None,
        *,
        daemon=None,
        parent: "QObject" = None
    ):
        super().__init__(parent=parent)
        self._fn = target
        self._name = name
        self._args = args or []
        self._kwargs = kwargs or {}
        self._daemon = daemon
        self._py_thread: Optional["threading.Thread"] = None

    def run(self):
        self._py_thread = threading.current_thread()
        self._py_thread.setName(self._name)
        self._fn(*self._args, **self._kwargs)
        self._py_thread._is_stopped = True

    def join(self, timeout: PYTHON_TIME = None):
        self.wait(qt_timeout(timeout))

    @property
    def ident(self) -> Optional[int]:
        return None if not self._py_thread else self._py_thread.ident

    def is_alive(self) -> bool:
        return self.isRunning()
