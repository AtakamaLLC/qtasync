import logging
import importlib
import sys
import os
from typing import TYPE_CHECKING, Type, Optional

from .types.unbound import SIGNAL_TYPE

if TYPE_CHECKING:
    # For static type checking, feel free to set the Qt library of your choice here
    from PySide2 import QtCore as _TypedQtCore
    from PySide2 import QtWidgets as _TypedQtWidgets


_log = logging.getLogger(__name__)

_QtModule = None
QtModuleName = None
PYSIDE2_MODULE_NAME = "PySide2"
PYSIDE6_MODULE_NAME = "PySide6"
PYQT5_MODULE_NAME = "PyQt5"
PYQT6_MODULE_NAME = "PyQt6"

# If QT_API env variable is given, use that or fail trying
_qtapi_env = os.getenv("QT_API", "").strip().lower()
if _qtapi_env:
    env_to_mod_map = {
        "pyqt5": PYQT5_MODULE_NAME,
        "pyqt6": PYQT6_MODULE_NAME,
        "pyside6": PYSIDE6_MODULE_NAME,
        "pyside2": PYSIDE2_MODULE_NAME,
    }
    if _qtapi_env in env_to_mod_map:
        QtModuleName = env_to_mod_map[_qtapi_env]
    else:
        raise ImportError(
            "QT_API environment variable set ({}) but not one of [{}].".format(
                _qtapi_env, ", ".join(env_to_mod_map.keys())
            )
        )

    _log.info("Forcing use of {} as Qt Implementation".format(QtModuleName))
    _QtModule = importlib.import_module(QtModuleName)

# If a Qt lib is already imported, use that
if not _QtModule:
    for QtModuleName in ("PySide2", "PySide6", "PyQt5", "PyQt6"):
        if QtModuleName in sys.modules:
            _QtModule = sys.modules[QtModuleName]
            break

# Try importing qt libs
if not _QtModule:
    for QtModuleName in ("PySide2", "PySide6", "PyQt5", "PyQt6"):
        try:
            _QtModule = importlib.import_module(QtModuleName)
        except ImportError:
            continue
        else:
            break


if not _QtModule:
    raise ImportError("No Qt implementations found")

_log.info("Using Qt Implementation: {}".format(QtModuleName))

if QtModuleName == "PyQt5":
    from PyQt5 import QtCore as _QtCore
    from PyQt5 import QtWidgets as _QtWidgets
elif QtModuleName == "PyQt6":
    from PyQt6 import QtCore as _QtCore
    from PyQt6 import QtWidgets as _QtWidgets
elif QtModuleName == "PySide2":
    from PySide2 import QtCore as _QtCore
    from PySide2 import QtWidgets as _QtWidgets
elif QtModuleName == "PySide6":
    from PySide6 import QtCore as _QtCore
    from PySide6 import QtWidgets as _QtWidgets
else:
    raise ImportError("Failed to import QCoreApplication")

# Expose Qt components and modules for importation
# QtCore
QtCore: "_TypedQtCore" = _QtCore
_QCoreApplication: Type["_TypedQtCore.QCoreApplication"] = _QtCore.QCoreApplication
try:
    Slot: "_TypedQtCore.Slot" = _QtCore.Slot
except AttributeError:
    Slot: "_TypedQtCore.Slot" = _QtCore.pyqtSlot
try:
    Signal: "_TypedQtCore.Signal" = _QtCore.Signal
except AttributeError:
    Signal: "_TypedQtCore.pyqtSignal" = _QtCore.pyqtSignal
try:
    SignalInstance: Type["_TypedQtCore.SignalInstance"] = _QtCore.SignalInstance
except AttributeError:
    SignalInstance: Type["_TypedQtCore.pyqtBoundSignal"] = _QtCore.pyqtBoundSignal
QObject: Type["_TypedQtCore.QObject"] = _QtCore.QObject
QSocketNotifier: Type["_TypedQtCore.QSocketNotifier"] = _QtCore.QSocketNotifier
QMutexLocker: Type["_TypedQtCore.QMutexLocker"] = _QtCore.QMutexLocker
QThread: Type["_TypedQtCore.QThread"] = _QtCore.QThread
QSemaphore: Type["_TypedQtCore.QSemaphore"] = _QtCore.QSemaphore
QMutex: Type["_TypedQtCore.QMutex"] = _QtCore.QMutex
if QtModuleName in (PYQT6_MODULE_NAME, PYSIDE6_MODULE_NAME):
    QRecursiveMutex: Optional[
        Type["_TypedQtCore.QRecursiveMutex"]
    ] = _QtCore.QRecursiveMutex
else:
    QRecursiveMutex = None
QWaitCondition: Type["_TypedQtCore.QWaitCondition"] = _QtCore.QWaitCondition
QTimer: Type["_TypedQtCore.QTimer"] = _QtCore.QTimer
QThreadPool: Type["_TypedQtCore.QThreadPool"] = _QtCore.QThreadPool
QRunnable: Type["_TypedQtCore.QRunnable"] = _QtCore.QRunnable
QEvent: Type["_TypedQtCore.QEvent"] = _QtCore.QEvent
QDeadlineTimer: Type["_TypedQtCore.QDeadlineTimer"] = _QtCore.QDeadlineTimer


# QtWidgets
QApplication: Type["_TypedQtWidgets.QApplication"] = _QtWidgets.QApplication


# Subclass of whatever QApplication is with some type hints and implementation-independent shims
class QCoreApplication(_QCoreApplication):
    aboutToQuit: SIGNAL_TYPE
    applicationNameChanged: SIGNAL_TYPE
    applicationVersionChanged: SIGNAL_TYPE
    organizationDomainChanged: SIGNAL_TYPE
    organizationNameChanged: SIGNAL_TYPE

    def send_posted_events(self, receiver: "QObject" = None, event_type=0):
        if QtModuleName in (PYQT5_MODULE_NAME, PYQT6_MODULE_NAME):
            return super().sendPostedEvents(receiver=receiver, eventType=event_type)
        else:
            return super().sendPostedEvents(receiver=receiver, event_type=event_type)
