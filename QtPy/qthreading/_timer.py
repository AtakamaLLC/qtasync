from typing import TYPE_CHECKING, Callable, Any

from QtPy._env import QTimer
from QtPy._util import qt_timeout
from QtPy.types.unbound import SIGNAL_TYPE
from QtPy.types.bound import PYTHON_TIME

if TYPE_CHECKING:
    from QtPy._env import QObject


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
