import logging
import importlib
import sys
import os
from typing import TYPE_CHECKING, Type

from .types.unbound import SIGNAL_TYPE

if TYPE_CHECKING:
    # For static type checking, feel free to set the Qt library of your choice here
    from PySide2 import QtCore as _TypedQtCore

_log = logging.getLogger(__name__)

_QtModule = None
_QtModuleName = None

# If QT_API env variable is given, use that or fail trying
_qtapi_env = os.getenv("QT_API", "").strip().lower()
if _qtapi_env:
    env_to_mod_map = {
        "pyqt5": "PyQt5",
        "pyqt6": "PyQt6",
        "pyside6": "PySide6",
        "pyside2": "PySide2",
    }
    if _qtapi_env in env_to_mod_map:
        _QtModuleName = env_to_mod_map[_qtapi_env]
    else:
        raise ImportError(
            "QT_API environment variable set ({}) but not one of [{}].".format(
                _qtapi_env, ", ".join(env_to_mod_map.keys())
            )
        )

    _log.info("Forcing use of {} as Qt Implementation".format(_QtModuleName))
    _QtModule = importlib.import_module(_QtModuleName)

# If a Qt lib is already imported, use that
if not _QtModule:
    for _QtModuleName in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        if _QtModuleName in sys.modules:
            _QtModule = sys.modules[_QtModuleName]
            break

# Try importing qt libs
if not _QtModule:
    for _QtModuleName in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        try:
            _QtModule = importlib.import_module(_QtModuleName)
        except ImportError:
            continue
        else:
            break


if not _QtModule:
    raise ImportError("No Qt implementations found")

_log.info("Using Qt Implementation: {}".format(_QtModuleName))

_QtCore = importlib.import_module(_QtModuleName + ".QtCore", package=_QtModuleName)
# _QtGui = importlib.import_module(QtModuleName + ".QtGui", package=QtModuleName)

#
# if QtModuleName == "PyQt5":
#     from PyQt5 import QtCore
# elif QtModuleName == "PyQt6":
#     from PyQt6 import QtCore
# elif QtModuleName == "PySide2":
#     from PySide2 import QtCore
# elif QtModuleName == "PySide6":
#     from PySide6 import QtCore
# else:
#     raise ImportError("Failed to import QCoreApplication")

_QCoreApplication: Type["_TypedQtCore.QCoreApplication"] = _QtCore.QCoreApplication
Slot: "_TypedQtCore.Slot" = _QtCore.Slot
try:
    Signal: "_TypedQtCore.Signal" = _QtCore.Signal
except AttributeError:
    Signal: "_TypedQtCore.Signal" = _QtCore.pyqtSignal
QObject: Type["_TypedQtCore.QObject"] = _QtCore.QObject
QSocketNotifier: Type["_TypedQtCore.QSocketNotifier"] = _QtCore.QSocketNotifier
QMutexLocker: Type["_TypedQtCore.QMutexLocker"] = _QtCore.QMutexLocker
QThread: Type["_TypedQtCore.QThread"] = _QtCore.QThread
QSemaphore: Type["_TypedQtCore.QSemaphore"] = _QtCore.QSemaphore
QMutex: Type["_TypedQtCore.QMutex"] = _QtCore.QMutex


# Subclass of whatever QApplication is with some type hints
class QCoreApplication(_QCoreApplication):
    aboutToQuit: SIGNAL_TYPE
    applicationNameChanged: SIGNAL_TYPE
    applicationVersionChanged: SIGNAL_TYPE
    organizationDomainChanged: SIGNAL_TYPE
    organizationNameChanged: SIGNAL_TYPE


# __all__ = ["QCoreApplication", "Slot", "Signal", "QObject", "QSocketNotifier"]
