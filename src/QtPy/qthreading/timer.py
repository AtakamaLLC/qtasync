from typing import TYPE_CHECKING, Callable, Any

from src.QtPy.env import QTimer
from src.QtPy.util import qt_timeout
from src.QtPy.types.unbound import SIGNAL_TYPE
from src.QtPy.types.bound import PYTHON_TIME

if TYPE_CHECKING:
    from src.QtPy.env import QObject


class PythonicQTimer(QTimer):
    timeout: SIGNAL_TYPE

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
