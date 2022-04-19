import logging
from typing import Union, Optional, Dict

from qtasync import get_timeout_compatibility_mode
from qtasync._env import QDeadlineTimer, QtCore

from .types.bound import QT_TIME, PYTHON_TIME
from .types.unbound import MESSAGE_HANDLER_TYPE


log = logging.getLogger(__name__)


def qt_timeout(time_secs: Union[float, PYTHON_TIME, None]) -> Optional[QT_TIME]:
    if time_secs is None:
        return None
    if get_timeout_compatibility_mode() and isinstance(time_secs, int):
        # If timeout compatibility mode is set, then integer timeouts are treated like Qt timeouts–durations measured
        # in milliseconds–and if it is a float then it is treated like a python time duration (seconds as a float)
        return QT_TIME(time_secs)
    else:
        return QT_TIME(time_secs * 1000)


def py_timeout(time_msecs: Union[int, QT_TIME, None]) -> Optional[PYTHON_TIME]:
    if time_msecs is None:
        return None
    return PYTHON_TIME(time_msecs / 1000.0)


def mk_q_deadline_timer(timeout: Optional[PYTHON_TIME]) -> "QDeadlineTimer":
    # TODO: Why doesn't ForeverConstant work?
    return (
        QDeadlineTimer(QDeadlineTimer.ForeverConstant.Forever)
        if timeout is None
        else QDeadlineTimer(qt_timeout(timeout))
    )


class QtLoggingMap:
    _log_level_map: Dict["QtCore.QtMsgType", int] = {
        QtCore.QtMsgType.QtDebugMsg: logging.DEBUG,
        QtCore.QtMsgType.QtInfoMsg: logging.INFO,
        QtCore.QtMsgType.QtWarningMsg: logging.WARNING,
        QtCore.QtMsgType.QtCriticalMsg: logging.ERROR,
        QtCore.QtMsgType.QtFatalMsg: logging.FATAL,
    }

    @classmethod
    def get_python_logging_level(cls, qt_log_level: "QtCore.QtMsgType") -> int:
        return cls._log_level_map[qt_log_level]


def qt_message_handler(
    msg_type: "QtCore.QtMsgType",
    context: "QtCore.QMessageLogContext",
    message: str,
    logger: "logging.Logger" = None,
):
    _log = logger or log
    py_log_level = QtLoggingMap.get_python_logging_level(msg_type)
    # pylint: disable=atakama-fstring-error
    _log.log(
        py_log_level,
        "#QT %s: %s (%s:%s, %s)",
        msg_type,
        message,
        context.file,
        context.line,
        context.file,
    )


def install_default_qt_message_handler():
    install_custom_qt_message_handler(qt_message_handler)


def install_custom_qt_message_handler(
    handler: MESSAGE_HANDLER_TYPE,
) -> Optional[Union[MESSAGE_HANDLER_TYPE, object]]:
    """
    :param handler: A new message handler function for all Qt log messages
    :return: The old message handling function if one was registered, else None. The return type is a union of object
        due to how the shiboken bindings were created, but the return value will not be an object and rather be None
        or a function.
    """
    return QtCore.qInstallMessageHandler(handler)
