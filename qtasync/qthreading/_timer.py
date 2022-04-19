from typing import TYPE_CHECKING, Callable, Any

from qtasync._env import QTimer
from qtasync._util import qt_timeout
from qtasync.types.unbound import SIGNAL_TYPE
from qtasync.types.bound import PYTHON_TIME

if TYPE_CHECKING:
    from qtasync._env import QObject


class QtTimer(QTimer):
    timeout: SIGNAL_TYPE

    def cancel(self):
        self.stop()

    @classmethod
    def singleShot(
        cls, duration: PYTHON_TIME, func: Callable[[], Any], parent: "QObject" = None
    ) -> "QtTimer":
        t = cls(parent=parent)
        t.setSingleShot(True)
        t.setInterval(qt_timeout(duration))
        t.timeout.connect(func)
        t.start()
        return t
