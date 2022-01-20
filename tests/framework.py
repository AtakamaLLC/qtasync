import logging
from typing import List, Dict, Optional, Set, Callable, Type
from unittest import TestCase

from src.env import QCoreApplication, QtCore, QApplication
from src.util import QtLoggingMap
from .util import (
    TempQObject,
    replace_log_level,
    replace_qapp_style,
    replace_qpa_platform,
    replace_qt_message_handler,
    install_exception_hook,
    get_os_style,
)
from .fixtures import process_events

log = logging.getLogger(__name__)


class SmartGuiTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_qobjs: List["TempQObject"] = []
        self._qt_messages: Dict["QtCore.QtMsgType", List[str]] = {}
        self._unhandled_exceptions: List[Exception] = []
        self.presenter: Optional["QtCore.QCoreApplication"] = None

    @staticmethod
    def ignored_qt_warnings() -> Set[str]:
        """
        Override to modify the set of Qt warnings which are ignored and will not trigger a test failure

        :return: A set of strings which, if present in a Qt warning, will exempt that warning from inducing a test
            failure. The string is case-sensitive.
        """
        return set()

    @staticmethod
    def qapp_class() -> Type["QCoreApplication"]:
        """
        Override if you do not want a QCoreApplication
        """
        return QCoreApplication

    def create_presenter(self):
        self.presenter = QCoreApplication.instance() or QCoreApplication([])

    # Test Utilities
    def create_temp_qobject(self) -> "TempQObject":
        obj = TempQObject()
        self._register_temp_qobj(obj)
        return obj

    def add_exception(self, exception: Optional[Exception]):
        # We might want a mutex here, but it also doesn't really matter which exception fails the tests as long as
        # they are all in the logs, which they will be
        self._unhandled_exceptions.append(exception)

    def get_unhandled_exceptions(self) -> List[Exception]:
        return self._unhandled_exceptions

    def ignore_exception_block(self):
        pass

    @property
    def render_mode(self) -> bool:
        return False

    # Internals
    def _ensure_state_reset(self):
        self.addCleanup(self._test_qobjs.clear)
        self.addCleanup(self._qt_messages.clear)
        self.addCleanup(self._unhandled_exceptions.clear)

    def _register_temp_qobj(self, obj: "TempQObject"):
        # Track all temp qobjects and remove them from the list when they are destroyed
        self._test_qobjs.append(obj)
        obj.destroyed.connect(self._mk_temp_qobj_destruction_handler(obj))

    def _mk_temp_qobj_destruction_handler(self, obj: TempQObject) -> Callable[[], None]:
        def on_destruction():
            self._test_qobjs.remove(obj)

        return on_destruction

    def _qt_message_handler(
        self,
        msg_type: "QtCore.QtMsgType",
        context: "QtCore.QMessageLogContext",
        message: str,
    ):
        if msg_type == QtCore.QtWarningMsg and any(
            ignore in message for ignore in self.ignored_qt_warnings()
        ):
            msg_type = QtCore.QtInfoMsg
        py_log_level = QtLoggingMap.get_python_logging_level(msg_type)
        # pylint: disable=atakama-fstring-error
        log.log(
            py_log_level,
            "#QT %s: %s (%s:%s, %s)",
            msg_type,
            message,
            context.file,
            context.line,
            context.file,
        )
        self._qt_messages.setdefault(msg_type, []).append(message)

    def _delete_temp_qobjs(self):
        # Delete all temp qobjects
        for obj in self._test_qobjs:
            obj.deleteLater()
        # Then manually process the deletions
        process_events(self.presenter)

    def verify_no_exceptions(self):
        if len(self._unhandled_exceptions) > 0:
            # Raise the first unhandled exception but log all of them
            for idx, ex in enumerate(self._unhandled_exceptions):
                log.error(
                    "Unhandled exception %s/%s during test",
                    idx,
                    len(self._unhandled_exceptions),
                    exc_info=ex,
                )
            raise self._unhandled_exceptions[0]

    def verify_no_qt_warnings(self):
        total_fail_messages = 0
        for qt_fail_log_lvl in [
            QtCore.QtMsgType.QtWarningMsg,
            QtCore.QtMsgType.QtCriticalMsg,
            QtCore.QtMsgType.QtFatalMsg,
        ]:
            for message in self._qt_messages.setdefault(qt_fail_log_lvl, []):
                # Print header before first qt log line
                if total_fail_messages == 0:
                    log.info("---- Dumping bad Qt log messages again ----")
                log.error(message)
                total_fail_messages += 1

        self.assertEqual(0, total_fail_messages)

    def setUp(self):
        super().setUp()
        # Ensure state is reset after test completion
        self._ensure_state_reset()

        # Replace some core resources with ones for this test, like logging handlers and the Qt QPA Plugin
        self.addCleanup(replace_log_level(logging.DEBUG))
        self.addCleanup(replace_qt_message_handler(self._qt_message_handler))
        self.addCleanup(install_exception_hook(self))
        if isinstance(self.qapp_class(), QApplication):
            # Only need to replace qpa platform and system style if the qapp is capable of rendering
            self.addCleanup(
                replace_qpa_platform(None if self.render_mode else "minimal")
            )
            self.addCleanup(replace_qapp_style(get_os_style()))

        # Create core app
        self.create_presenter()
        # While this is done during tearDown, we want to ensure that
        self.addCleanup(self._delete_temp_qobjs)

    def tearDown(self):
        super().tearDown()
        # TODO: Ensure all attributes and methods of presenter are not mocks
        """
        Tear down procedure is as follows:
            1. Run presenter cleanup, which will do the following
                - Stop all model services (MainPresenter only)
                - Close all open windows
                - Delete the global resource parent
                - Process deletions
            2. Delete temp resources
                - Delete temp qobjects
                - Process deletions
            3. Verify that no unhandled exceptions were raised during the test
            4. Verify that resources have been freed and destroyed
            5. Verify that no Qt warnings or errors were emitted during the test
            6. Verify that no changes have been made which will persist between tests
                - This happens during cleanup, see setUp()
        """
        # Step 2
        self._delete_temp_qobjs()

        # Step 3
        self.verify_no_exceptions()

        # Step 4
        self.verify_no_qt_warnings()
