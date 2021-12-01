import logging
import time
from unittest import TestCase

from PySide2.QtCore import QCoreApplication, QThreadPool, QThread

from src.concurrent.futures import PythonicQFuture, QThreadPoolExecutor, PythonicQMutex

from ..fixtures import process_events

log = logging.getLogger(__name__)


class TestPythonicQFuture(TestCase):
    def setUp(self) -> None:
        logging.basicConfig()
        self.qapp = QCoreApplication.instance() or QCoreApplication()

    def tearDown(self) -> None:
        process_events(self.qapp)

    def test_basic_future(self):
        future_executed = False

        def some_fn(pos_arg, kwarg=False):
            nonlocal future_executed
            if pos_arg == 4 and kwarg:
                future_executed = True

        pool = QThreadPoolExecutor()
        pool.submit(some_fn, 4, kwarg=True)
        pool.shutdown()

        self.assertTrue(future_executed)

    def test_cancel_future(self):
        queued_runnable_finished = False

        pool = QThreadPool()
        # Only one thread, which will be blocked, to allow us to test cancellation for queued threads
        pool.setMaxThreadCount(1)
        executor = QThreadPoolExecutor(qthread_pool=pool)

        mutex = PythonicQMutex()
        mutex.lock()

        def blocking_runnable():
            log.info("Waiting on blocked mutex")
            mutex.lock()
            log.info("Blocked mutex unlocked")
            return 5

        def queued_runnable():
            nonlocal queued_runnable_finished
            queued_runnable_finished = True
            log.error("Queued runnable executed")

        blocking_future = executor.submit(blocking_runnable)
        queued_future = executor.submit(queued_runnable)

        # Sleep until the blocking future has started
        initial_time = time.monotonic()
        while not blocking_future.running():
            # And process events while we're sleeping
            process_events(self.qapp)

            # Should take less than one second
            if (time.monotonic() - initial_time) > 1:
                raise TimeoutError

        queued_future.cancel()
        mutex.unlock()

        executor.shutdown()
        self.assertEqual(5, blocking_future.result())
        self.assertFalse(queued_runnable_finished)
        self.assertTrue(queued_future.cancelled())
        mutex.unlock()

        pool.deleteLater()

    def test_wait_for_result(self):
        executor = QThreadPoolExecutor()

        def fn():
            QThread.currentThread().sleep(1)
            return 2

        future = executor.submit(fn)

        self.assertEqual(2, future.result(timeout=3))

    def test_exception(self):
        executor = QThreadPoolExecutor()

        def fn():
            raise RuntimeError

        future = executor.submit(fn)

        self.assertIsInstance(future.exception(timeout=1), RuntimeError)
        with self.assertRaises(RuntimeError):
            future.result(timeout=1)

    def test_done_callback(self):
        executor = QThreadPoolExecutor()
        mutex = PythonicQMutex()
        mutex.lock()

        def fn():
            mutex.unlock()
            return 3

        future = executor.submit(fn)
        future.add_done_callback()
