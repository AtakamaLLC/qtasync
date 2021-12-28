import logging
import os
import sys
from typing import TYPE_CHECKING, Optional, Callable
from unittest.mock import Mock

from src.env import QObject, QApplication
from src.types.unbound import MESSAGE_HANDLER_TYPE, SIGNAL_TYPE
from src.util import install_custom_qt_message_handler

from .enums import FailureCodes

if TYPE_CHECKING:
    from src.env import QtCore


RESTORE_FN_TYPE = Callable[[], None]


def install_exception_hook(smart_test: "SmartGuiTest") -> RESTORE_FN_TYPE:
    existing_ex_hook = sys.excepthook

    # Install a custom exception hook to save a ref to any exceptions that occur
    # and then fail the test accordingly
    def fail_on_ex(exc_type, exc_val, exc_tb):
        # Special attribute you can jam into an exception if it is supposed to be raised
        if getattr(exc_val, "ignore", False):
            return existing_ex_hook(exc_type, exc_val, exc_tb)
        try:
            smart_test.add_exception(type(exc_val))
        except TypeError as err:
            smart_test.add_exception(err)
        smart_test.presenter.queued_exit(FailureCodes.EXCEPTION_RAISED)
        return existing_ex_hook(exc_type, exc_val, exc_tb)

    sys.excepthook = fail_on_ex

    def restore_old_ex_hook(old_hook=existing_ex_hook):
        sys.excepthook = old_hook

    return restore_old_ex_hook


def replace_qpa_platform(new_qpa_plugin: Optional[str]) -> RESTORE_FN_TYPE:
    old_qpa_platform = os.environ.pop("QT_QPA_PLATFORM", None)

    if old_qpa_platform is not None:

        def restore_qpa_platform(qpa_platform: str = old_qpa_platform):
            os.environ["QT_QPA_PLATFORM"] = qpa_platform

    else:
        # If there was no old platform, or it was None (for some reason), don't set a value in the environ map since
        # we don't want the key to be defined in the first place
        def restore_qpa_platform():
            pass

    if new_qpa_plugin is not None:
        os.environ["QT_QPA_PLATFORM"] = new_qpa_plugin
    return restore_qpa_platform


def replace_qt_message_handler(new_handler: MESSAGE_HANDLER_TYPE) -> RESTORE_FN_TYPE:
    old_handler = install_custom_qt_message_handler(new_handler)

    def restore_message_handler(handler=old_handler):
        install_custom_qt_message_handler(handler)

    return restore_message_handler


def replace_log_level(new_log_level) -> RESTORE_FN_TYPE:
    original_root_log_level = logging.getLogger().level

    def restore_log_level(log_level=original_root_log_level):
        logging.getLogger().setLevel(log_level)

    logging.getLogger().setLevel(new_log_level)
    return restore_log_level


def replace_qapp_style(new_style: str) -> RESTORE_FN_TYPE:
    original_style = QApplication.style()
    original_style_name = original_style.objectName() if original_style else None

    def restore_qapp_style(style=original_style_name):
        QApplication.setStyle(style)

    QApplication.setStyle(new_style)
    return restore_qapp_style


def get_os_style() -> Optional[str]:
    if os.name == "nt":
        return "Windows"
    else:
        return "Fusion"


class TempQObject(QObject):
    destroyed: SIGNAL_TYPE
    objectNameChanged: SIGNAL_TYPE


class TempPresenter(TempQObject):
    def __init__(self, presenter: "QtCore.QCoreApplication"):
        super().__init__()
        self.NAME = "temp_qobj_{}".format(os.urandom(8).hex())
        self.ID = self.NAME
        self.QML = "temp_presenter_qml"
        self.presenter = presenter
        self.show_success = Mock()
        self.show_error = Mock()
        self.context = None
        self.containing_window = Mock()
        self.raise_window = Mock()


class IgnoredRuntimeError(RuntimeError):
    """
    If you raise this exception during a headless live or interactive test, it will not cause the test to fail. You do
    not want to raise this exception type in production code, as exceptions are suppressed in production anyway (not to
    mention that knowing the original exception type is important for debugging).

    A typical use-case of this class is to test the exception-handling logic of some component. For example, a
    SafeQThread will emit an exceptionOccurred signal if the task function raises an exception. This will, however,
    cause the test to fail if it occurs in a SmartGuiTest's test due to the modified system exception hook.

    Thus, you would want to do the following:


    Look at install_exception_hook() to see how the ignored attribute is inspected.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.ignore = True


class IgnoredIndexError(IndexError):
    @property
    def ignore(self):
        return True
