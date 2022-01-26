from typing import TYPE_CHECKING, Union, Optional, Callable

if TYPE_CHECKING:
    from src.QtPy.env import Signal, SignalInstance, QtCore  # noqa: F401

SIGNAL_TYPE = Union["Signal", "SignalInstance"]
MESSAGE_HANDLER_TYPE = Optional[
    Callable[["QtCore.QtMsgType", "QtCore.QMessageLogContext", str], None]
]
