import logging
import time
import pytest

from QtPy._env import QThreadPool, QThread

from QtPy.qconcurrent._futures import (
    QtFuture,
    QtThreadPoolExecutor,
    QtLock,
)

from ..util import process_events

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
log = logging.getLogger(__name__)


def test_basic_future():
    future_executed = False

    def some_fn(pos_arg, kwarg=False):
        nonlocal future_executed
        if pos_arg == 4 and kwarg:
            future_executed = True

    pool = QtThreadPoolExecutor()
    pool.submit(some_fn, 4, kwarg=True)
    pool.shutdown()

    assert future_executed


def test_cancel_future(application):
    queued_runnable_finished = False

    pool = QThreadPool()
    # Only one thread, which will be blocked, to allow us to test cancellation for queued threads
    pool.setMaxThreadCount(1)
    executor = QtThreadPoolExecutor(qthread_pool=pool)

    mutex = QtLock()
    mutex.acquire()

    def blocking_runnable():
        log.info("Waiting on blocked mutex")
        mutex.acquire()
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
        process_events(application)

        # Should take less than one second
        if (time.monotonic() - initial_time) > 1:
            raise TimeoutError

    queued_future.cancel()
    mutex.release()

    executor.shutdown()
    assert 5 == blocking_future.result()
    assert not queued_runnable_finished
    assert queued_future.cancelled()
    mutex.release()

    pool.deleteLater()


def test_wait_for_result():
    executor = QtThreadPoolExecutor()

    def fn():
        QThread.currentThread().sleep(1)
        return 2

    future = executor.submit(fn)

    assert 2 == future.result(timeout=None)


def test_exception():
    executor = QtThreadPoolExecutor()

    def fn():
        raise RuntimeError

    future = executor.submit(fn)

    assert isinstance(future.exception(timeout=1), RuntimeError)
    with pytest.raises(RuntimeError):
        future.result(timeout=1)


def test_done_callback(application):
    executor = QtThreadPoolExecutor()
    mutex = QtLock()
    mutex.acquire()
    did_callback = False

    def fn():
        with mutex:
            return 3

    def on_done(f: "QtFuture"):
        nonlocal did_callback
        assert 3 == f.result()
        did_callback = True

    future = executor.submit(fn)
    # Case 1: Callback added before future finished
    future.add_done_callback(on_done)
    mutex.release()
    assert 3 == future.result(timeout=600)
    # Events must be processed so that the finished signal is emitted and processed
    process_events(application)
    assert did_callback

    # Case 2: Callback added after future finished
    did_callback2 = False

    def after_done(f: "QtFuture"):
        nonlocal did_callback2
        assert 3 == f.result()
        did_callback2 = True

    future.add_done_callback(after_done)
    assert did_callback2
