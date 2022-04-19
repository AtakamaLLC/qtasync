# QtAsync

## Overview
This project is intended to be a shim to allow Python applications to utilize Qt without needing to rewrite common
threading or asynchronous logic specifically for the interfaces offered by Qt. Rather, one can write application business 
logic largely the same as if Qt were not used. This library exports a series of objects that utilize Qt implementations with
Python semantics and interfaces to make it inoperable with their Python equivalents.

In particular, this library focuses on providing support for concurrency, multi-threading, and event loops. The Python
libraries that this library intends to support with Qt implementations are [threading](https://docs.python.org/3.9/library/threading.html), [concurrent.futures](https://docs.python.org/3.9/library/concurrent.futures.html), and [asyncio](https://docs.python.org/3.9/library/asyncio.html).

Much of the `qtasync.qasyncio` module was derived from [qasync](https://github.com/CabbageDevelopment/qasync).


## Requirements
* Supported Python Versions: Python 3.9
* Supported Qt Libraries: [PyQt5](https://pypi.org/project/PyQt5/), [PyQt6](https://pypi.org/project/PyQt6/), [PySide2](https://pypi.org/project/PySide2/), [PySide6](https://pypi.org/project/PySide6/)

## Installation

`qtasync` is not yet on PyPi, so it must be installed from GitHub.

### pip
Using ssh:
`pip install git+ssh://git@github.com/AtakamaLLC/QtAsync.git@main`

Using https:
`pip install git+https://github.com/AtakamaLLC/QtAsync.git@main`

### poetry
Using ssh:
`poetry add git+ssh://git@github.com/AtakamaLLC/QtAsync.git#main`

Using https:
`poetry add git+https://github.com/AtakamaLLC/QtAsync.git#main`


## Use

If you have multiple Python implementations of Qt installed, aet the `QT_API` environment variable to the name of the
library you want to use (`PySide2`, `PySide6`, `PyQt5`, or `PyQt6`)

There are three modules in this library to implement Qt-compatible versions of `threading`, `concurrent`, and `asyncio`.
and they are named similarly: `qtasync.qthreading`, `qtasync.qconcurrent`, and `qtasync.qasyncio`.

The nomenclature is different from the Python modules and classes they mimic to resolve ambiguity and prevent namespace
issues. The objects defined here are prefixed with "Qt".

For example, `qtasync.qthreading.QtRLock` is a Qt-friendly implementation of `threading.RLock`. The interface is largely
the same as the Python equivalent and can be used interchangeably in many cases.


## Supported Modules

### Threading
| Python Class | QtAsync Class |
| ------------ | ---------- |
| `threading.Lock` | `qtasync.qthreading.QtLock` |
| `threading.RLock` | `qtasync.qthreading.QtRLock` |
| `threading.Condition` | `qtasync.qthreading.QtCondition` |
| `threading.Event` | `qtasync.qthreading.QtEvent` |
| `threading.Semaphore` | `qtasync.qthreading.QtSemaphore` |
| `threading.Thread` | `qtasync.qthreading.QtThread` |
| `threading.Timer` | `qtasync.qthreading.QtTimer` |

### Concurrent
| Python Class | QtAsync Class |
| ------------ | ---------- |
| `concurrent.futures.Future` | `qtasync.qconcurrent.QtFuture` |
| `concurrent.futures.ThreadPoolExecutor` | `qtasync.qconcurrent.QtThreadPoolExecutor` |

### Asyncio

| Python Class | QtAsync Class |
| ------------ | ---------- |
| `asyncio.ProactorEventLoop` | `qtasync.qasyncio.QtProactorEventLoop` |
| `asyncio.SelectorEventLoop` | `qtasync.qasyncio.QtSelectorEventLoop` |

Additionally, there is a third object, `QtEventLoop`, which will select one of the two above implementations
depending on the active operating system. If running Windows, use `QtProactorEventLoop`, and if not, use
`QtSelectorEventLoop`.

### Missing Support?
The Qt implementations of their respective Python objects may be incomplete. If you need support for additional features
or behavior, you can either submit a pull request or request the change in this repository's [issue tracker](https://github.com/AtakamaLLC/QtAsync/issues).


## Examples
Take a look at the test suites in the tests folder for detailed use of library components.

In particular, `tests.qthreading.test_locks.py` tests the `qtasync.qthreading` module with both the Python object and
its QtAsync equivalent, demonstrating the interoperability between the two.

For example:
```python
from qtasync.qthreading import (
    QtLock,
    QtEvent,
    QtThread,
)

def not_thread_safe_fn():
    # Thread-unsafe logic
    pass

# QtLock and QtRLock can be used like threading.Lock and threading.RLock, including `with` blocks
lock = QtLock()
with lock:
    not_thread_safe_fn()

# QtEvent, like threading.Event, allows thread synchronization
evt = QtEvent()

def wait_then_print(idx):
    evt.wait()
    print(f"Thread {idx} done")

threads = [QtThread(target=wait_then_print, args=[i]) for i in range(0, 10)]
for t in threads:
    t.start()

evt.set()
for t in threads:
    t.join(timeout=1)
```
