import logging
from typing import Type, Union, Callable, Any, Optional
from threading import Condition, Event, Thread, Semaphore, Lock, RLock
from unittest.mock import patch

import pytest

from QtAsync import set_timeout_compatibility_mode
from QtAsync._env import QThread
from QtAsync.qthreading import (
    QtLock,
    QtRLock,
    QtCondition,
    QtEvent,
    QtThread,
    QtSemaphore,
)


log = logging.getLogger(__name__)

MUTEX = Union[Lock, RLock, QtLock, QtRLock]
THREAD_EVT = Union[Event, QtEvent]
CONDITION = Union[Condition, QtCondition]
THREAD_CLS = Union[Type[Thread], Type[QtThread]]
SEMAPHORE = Union[Semaphore, QtSemaphore]


@pytest.fixture(params=[Thread, QtThread])
def thread_cls(request):
    thread_cls: THREAD_CLS = request.param
    yield thread_cls


@pytest.fixture(params=[Event, QtEvent])
def thread_event(request):
    evt_cls: Union[Type["Event"], Type["QtEvent"]] = request.param
    evt = evt_cls()
    yield evt


def get_mutex(thread_type, recursive: bool = False) -> Type[MUTEX]:
    if issubclass(thread_type, Thread):
        return RLock if recursive else Lock
    elif issubclass(thread_type, QThread):
        return QtRLock if recursive else QtLock
    else:
        raise RuntimeError("Unexpected thread type %s", thread_type)


def get_thread_event(thread_type) -> Type[THREAD_EVT]:
    if issubclass(thread_type, Thread):
        return Event
    elif issubclass(thread_type, QThread):
        return QtEvent
    else:
        raise RuntimeError("Unexpected thread type %s", thread_type)


def get_condition(thread_type) -> Type[CONDITION]:
    if issubclass(thread_type, Thread):
        return Condition
    elif issubclass(thread_type, QThread):
        return QtCondition
    else:
        raise RuntimeError("Unexpected thread type %s", thread_type)


def get_semaphore(thread_type) -> Type[SEMAPHORE]:
    if issubclass(thread_type, Thread):
        return Semaphore
    elif issubclass(thread_type, QThread):
        return QtSemaphore
    else:
        raise RuntimeError("Unexpected thread type %s", thread_type)


def test_qt_lock():
    lock = QtLock()
    assert not lock._is_owned()
    lock.acquire()
    assert lock._is_owned()
    lock.release()
    assert not lock._is_owned()


def test_qt_recursive_lock():
    lock = QtRLock()
    assert not lock._is_owned()
    assert lock._recursion_count() == 0
    lock.acquire(blocking=False)
    assert lock._is_owned()
    assert lock._recursion_count() == 1
    lock.acquire(blocking=False)
    assert lock._is_owned()
    assert lock._recursion_count() == 2
    lock.release()
    assert lock._is_owned()
    assert lock._recursion_count() == 1
    lock.release()
    assert not lock._is_owned()
    assert lock._recursion_count() == 0


def test_thread_event_set(thread_cls: THREAD_CLS):
    thread_event = get_thread_event(thread_cls)()
    assert not thread_event.is_set()
    thread_event.set()
    assert thread_event.is_set()


def test_condition_single_thread(thread_cls: THREAD_CLS):
    condition = get_condition(thread_cls)()
    with condition:
        assert not condition.wait(timeout=0.1)

    with pytest.raises(RuntimeError):
        condition.wait(timeout=0.1)

    with pytest.raises(RuntimeError):
        condition.release()


def test_condition_double_acquire(thread_cls: THREAD_CLS):
    lock = get_mutex(thread_cls, False)()
    condition = get_condition(thread_cls)(lock=lock)
    with condition:
        assert not condition.acquire(blocking=False)


def test_condition_wait_for(thread_cls: THREAD_CLS):
    cond = get_condition(thread_cls)()
    evt = get_thread_event(thread_cls)()
    some_arr = []

    def fn():
        nonlocal some_arr
        assert evt.wait(timeout=1.0)
        with cond:
            some_arr.append("val")
            cond.notify_all()

    t = thread_cls(target=fn)
    t.start()

    with cond:
        evt.set()
        assert cond.wait_for(lambda: len(some_arr) > 0, timeout=1.0)

    t.join(1.0)
    assert not t.is_alive()


def test_condition_wait_for_timeout_none(thread_cls: THREAD_CLS):
    cond = get_condition(thread_cls)()
    evt = get_thread_event(thread_cls)()
    some_arr = []

    def fn():
        nonlocal some_arr
        assert evt.wait(timeout=1.0)
        with cond:
            some_arr.append("val")
            cond.notify_all()

    t = thread_cls(target=fn)
    t.start()
    with cond:
        evt.set()
        assert cond.wait_for(lambda: len(some_arr) > 0, timeout=None)

    t.join(1.0)
    assert not t.is_alive()


def test_cond_var():
    def start_py_thread(func: Callable[[], None]) -> Thread:
        t = Thread(target=func, daemon=True)
        t.start()
        return t

    def stop_py_thread(t: Thread) -> None:
        t.join(20)
        assert not t.is_alive()

    # First, check the test is sane and works for normal CVs
    check_cond_var(Condition(), Event(), start_py_thread, stop_py_thread, 10)
    check_cond_var(Condition(), Event(), start_py_thread, stop_py_thread)

    def start_qthread(func: Callable[[], None]) -> QtThread:
        t = QtThread(target=func)
        t.finished.connect(t.deleteLater)
        t.start()
        return t

    def stop_qthread(t: QtThread) -> None:
        t.wait(20000)
        assert t.isFinished()

    # Now check that it works for our subclass
    check_cond_var(QtCondition(), QtEvent(), start_qthread, stop_qthread, 10)
    check_cond_var(QtCondition(), QtEvent(), start_qthread, stop_qthread)


def check_cond_var(
    cv: Union[Condition, QtCondition],
    evt: Union[QtEvent, Event],
    start_thread: Callable[[Callable[[], None]], Any],
    stop_thread: Callable[[Any], None],
    cv_wait_timeout: Optional[float] = None,
) -> None:
    arr: list[str] = []
    with pytest.raises(RuntimeError):
        # Gotta hold the lock if we want to acquire
        cv.wait(1)

    # Releasing without acquiring isn't allowed
    with pytest.raises(RuntimeError):
        cv.release()

    # Can't acquire non-blocking with a timeout
    with pytest.raises(ValueError):
        cv.acquire(blocking=False, timeout=1)

    # Timeout expirations handled appropriately
    with cv:
        assert not cv.wait(0)
        assert not cv.wait(0.1)

    # Adapted from the threading.Condition example in the Python docs
    recvd = None

    def receiver() -> None:
        nonlocal recvd

        with cv:
            evt.set()
            cv.wait_for(lambda: len(arr) > 0, timeout=cv_wait_timeout)
            recvd = arr.pop(0)

    recv_thread = start_thread(receiver)

    # Don't start the sender until we're confirmed waiting. Event is set()
    # while the CV lock is held, so we know the sender won't be able to
    # acquire it til the wait has actually started.
    evt.wait()

    def sender() -> None:
        with cv:
            arr.append("data!")
            cv.notify_all()

    send_thread = start_thread(sender)

    stop_thread(send_thread)
    stop_thread(recv_thread)

    assert not arr
    assert recvd == "data!"


def test_condition_multiple_threads(thread_cls: THREAD_CLS):
    condition = get_condition(thread_cls)()
    semaphore = get_semaphore(thread_cls)(value=0)
    num_threads = 10
    wait_results = []

    def _wait_on_cond(cond: CONDITION):
        nonlocal wait_results
        with cond:
            semaphore.release()
            wait_results.append(cond.wait(timeout=1.0 * num_threads))

    threads = [
        thread_cls(target=_wait_on_cond, args=[condition])
        for _i in range(0, num_threads)
    ]
    for i, t in enumerate(threads):
        t.start()
        assert semaphore.acquire(blocking=True, timeout=1.0)

    with condition:
        condition.notify_all()

    for t in threads:
        t.join(timeout=1.0)
        assert not t.is_alive()

    assert all(wait_results)
    assert len(wait_results) == num_threads


def test_thread_event_wait(thread_cls: THREAD_CLS):
    thread_event = get_thread_event(thread_cls)()
    t = thread_cls(target=lambda timeout=1.0: thread_event.wait(timeout=timeout))
    t.start()
    assert t.is_alive()
    t.join(0.1)
    assert t.is_alive()

    thread_event.set()
    t.join(0.1)
    assert not t.is_alive()


def test_semaphore(thread_cls: THREAD_CLS):
    sem_cls = get_semaphore(thread_cls)
    sem = sem_cls(value=2)
    assert sem.acquire(blocking=False)
    assert sem.acquire(blocking=False)
    assert not sem.acquire(blocking=False)

    t = thread_cls(target=sem.release, args=[2])
    t.start()
    assert sem.acquire(blocking=True, timeout=1.0)
    assert sem.acquire(blocking=False)
    assert not sem.acquire(blocking=False)
    t.join(timeout=1.0)
    assert not t.is_alive()


def test_mutex_with_time_conversion():
    set_timeout_compatibility_mode(True)
    try:
        mutex = QtLock()

        with patch.object(mutex, "_mutex") as qt_mutex:
            # Float is python timeout duration in seconds, converted to milliseconds
            mutex.acquire(timeout=1.0)
            qt_mutex.tryLock.assert_called_once_with(1000)
            qt_mutex.reset_mock()

            # Integer is Qt timeout duration in milliseconds, unchanged
            mutex.acquire(timeout=1)
            qt_mutex.tryLock.assert_called_once_with(1)
    finally:
        set_timeout_compatibility_mode(False)
