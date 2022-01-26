import logging
import traceback
from typing import Union, Optional, Dict

from QtPy import (
    _automatically_convert_timeout,
    _timeout_warning_threshold_max,
    _timeout_warning_threshold_min,
    _on_timeout_violation,
)
from QtPy.env import QDeadlineTimer, QtCore

from .types.bound import QT_TIME, PYTHON_TIME
from .types.unbound import MESSAGE_HANDLER_TYPE


log = logging.getLogger(__name__)


def qt_timeout(time_secs: Union[float, PYTHON_TIME]) -> QT_TIME:
    if _automatically_convert_timeout and isinstance(time_secs, int):
        # If the auto convert global flag is set, do not convert python timeout to qt timeout (seconds -> milliseconds)
        # This does, however, assume that the parameter is passed in as a float and not a small integer, if the caller
        # is intending for the timeout value's unit to be evaluated as seconds not ms

        # Ex. A call to QMutex may look like mutex.tryLock(1000), however PythonicQMutex's timeout is a float number of
        #   seconds to wait, not milliseconds. If the caller naively calls pyqmutex.acquire(timeout=1000), then the
        #   mutex will wait for 1000 seconds rather than 1.
        qt_time = QT_TIME(time_secs)
    else:
        qt_time = QT_TIME(time_secs * 1000)

    if _automatically_convert_timeout and (
        (qt_time / 1000.0) < _timeout_warning_threshold_min
        or time_secs > _timeout_warning_threshold_max
    ):
        log.warning(
            "Timeout violates warning threshold (%s < %s < %s)\n%s",
            _timeout_warning_threshold_min,
            time_secs,
            _timeout_warning_threshold_max,
            "".join(traceback.format_stack()),
        )
        if _on_timeout_violation:
            _on_timeout_violation()
    return qt_time


def py_timeout(time_msecs: Union[int, QT_TIME]) -> PYTHON_TIME:
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
