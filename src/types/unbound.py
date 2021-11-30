from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from PySide2.QtCore import Signal, SignalInstance  # noqa: F401

SIGNAL_TYPE = Union["Signal", "SignalInstance"]
