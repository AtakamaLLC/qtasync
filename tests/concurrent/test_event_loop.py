import logging
import time
from unittest import TestCase

from PySide2.QtCore import QCoreApplication, QObject

from src.concurrent.futures import (
    QThreadPoolExecutor,
    PythonicQEventLoop,
    PythonicQTimer,
)

from ..fixtures import process_events

log = logging.getLogger(__name__)


class TestEventLoop(TestCase):
    def setUp(self) -> None:
        logging.basicConfig()
        self.qapp = QCoreApplication.instance() or QCoreApplication()
        self._test_resource = QObject()
        PythonicQTimer.singleShot(
            5000, lambda: self.qapp.exit(1), parent=self._test_resource
        )

    def tearDown(self) -> None:
        self._test_resource.deleteLater()
        self._test_resource = None
        process_events(self.qapp)

    def test_call_soon(self):
        loop = PythonicQEventLoop()
        loop.set_default_executor(QThreadPoolExecutor())
        loop.call_soon(self.qapp.quit)
        loop.run_forever()
        self.assertEqual(0, loop.last_exit_code())

    def test_is_running(self):
        loop = PythonicQEventLoop()
        loop.set_default_executor(QThreadPoolExecutor())

        async def is_running():
            nonlocal loop
            self.assertTrue(loop.is_running())

        loop.run_until_complete(is_running())
