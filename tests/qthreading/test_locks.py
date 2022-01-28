import logging
from typing import Type, Union
from threading import Condition, Event, Thread, Semaphore, Lock, RLock
from unittest.mock import patch

import pytest

from QtPy import set_timeout_compatibility_mode
from QtPy._env import QThread
from QtPy.qthreading import (
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


def test_thread_event_set(thread_cls: THREAD_CLS):
    thread_event = get_thread_event(thread_cls)()
    assert not thread_event.is_set()
    thread_event.set()
    assert thread_event.is_set()


def test_condition_single_thread(thread_cls: THREAD_CLS):
    condition = get_condition(thread_cls)()
    with condition:
        assert not condition.wait(timeout=0.1)


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
