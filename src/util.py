from typing import Union, Optional

from PySide2.QtCore import QDeadlineTimer

from .types.bound import QT_TIME, PYTHON_TIME


def qt_timeout(time_secs: Union[float, PYTHON_TIME]) -> QT_TIME:
    return QT_TIME(int(time_secs * 1000))


def py_timeout(time_msecs: Union[int, QT_TIME]) -> PYTHON_TIME:
    return PYTHON_TIME(time_msecs / 1000.0)


def mk_q_deadline_timer(timeout: Optional[PYTHON_TIME]) -> "QDeadlineTimer":
    return QDeadlineTimer(QDeadlineTimer.Forever) if timeout is None else QDeadlineTimer(qt_timeout(timeout))
