import os
import logging
from typing import TYPE_CHECKING, Optional
from pytest import fixture

from QtPy.env import QtDebugMsg, QtInfoMsg, QtWarningMsg, QtCriticalMsg, QtFatalMsg
from tests.util import (
    TempQObject,
    replace_log_level,
    replace_qt_message_handler,
    install_exception_hook,
)

if TYPE_CHECKING:
    from QtPy.env import QtCore


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)


if os.name == "nt":
    collect_ignore = ["src/concurrent/asyncio/_unix.py"]
else:
    collect_ignore = ["src/concurrent/asyncio/_windows.py"]


@fixture(scope="session")
def application():
    from QtPy.env import QCoreApplication

    return QCoreApplication.instance() or QCoreApplication([])


class QtLoggingMap:
    _log_level_map: dict["QtCore.QtMsgType", int] = {
        QtDebugMsg: logging.DEBUG,
        QtInfoMsg: logging.INFO,
        QtWarningMsg: logging.WARNING,
        QtCriticalMsg: logging.ERROR,
        QtFatalMsg: logging.FATAL,
    }

    @classmethod
    def get_python_logging_level(cls, qt_log_level: "QtCore.QtMsgType") -> int:
        return cls._log_level_map[qt_log_level]


class QtTestContext:
    def __init__(self):
        self._test_qobjs: list["TempQObject"] = []
        self._qt_messages: dict["QtCore.QtMsgType", list[str]] = {}
        self._unhandled_exceptions: list[Exception] = []
        self._ignored_qt_warnings = set()

    def add_ignored_qt_warning(self, warning: str):
        self._ignored_qt_warnings.add(warning)

    def add_exception(self, exception: Optional[Exception]):
        # We might want a mutex here, but it also doesn't really matter which exception fails the tests as long as
        # they are all in the logs, which they will be
        self._unhandled_exceptions.append(exception)

    def get_unhandled_exceptions(self) -> list[Exception]:
        return self._unhandled_exceptions

    def qt_message_handler(
        self,
        msg_type: "QtCore.QtMsgType",
        context: "QtCore.QMessageLogContext",
        message: str,
    ):
        if msg_type == QtWarningMsg and any(
            ignore in message for ignore in self._ignored_qt_warnings
        ):
            msg_type = QtInfoMsg
        py_log_level = QtLoggingMap.get_python_logging_level(msg_type)
        # pylint: disable=atakama-fstring-error
        logging.log(
            py_log_level,
            "#QT %s: %s (%s:%s, %s)",
            msg_type,
            message,
            context.file,
            context.line,
            context.file,
        )
        self._qt_messages.setdefault(msg_type, []).append(message)

    def verify_no_exceptions(self):
        if len(self._unhandled_exceptions) > 0:
            # Raise the first unhandled exception but log all of them
            for idx, ex in enumerate(self._unhandled_exceptions):
                logging.error(
                    "Unhandled exception %s/%s during test",
                    idx,
                    len(self._unhandled_exceptions),
                    exc_info=ex,
                )
            raise self._unhandled_exceptions[0]

    def verify_no_qt_warnings(self):
        total_fail_messages = 0
        for qt_fail_log_lvl in [
            QtWarningMsg,
            QtCriticalMsg,
            QtFatalMsg,
        ]:
            for message in self._qt_messages.setdefault(qt_fail_log_lvl, []):
                # Print header before first qt log line
                if total_fail_messages == 0:
                    logging.info("---- Dumping bad Qt log messages again ----")
                logging.error(message)
                total_fail_messages += 1

        assert total_fail_messages == 0


@fixture(autouse=True)
def qt_test():
    test_context = QtTestContext()
    cleanup_fns = [
        replace_log_level(logging.DEBUG),
        replace_qt_message_handler(test_context.qt_message_handler),
        install_exception_hook(test_context),
    ]

    yield test_context

    test_context.verify_no_exceptions()
    test_context.verify_no_qt_warnings()

    for fn in cleanup_fns:
        fn()
