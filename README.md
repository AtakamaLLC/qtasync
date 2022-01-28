# QtPy

## Overview
Add `asyncio` support to applications running a `QCoreApplication` or one of its subprocesses by
utilizing the `QCoreApplication` event loop as a `asyncio.BaseEventLoop`.

## Requirements
* Supported Python Versions: Python 3.9
* Supported Qt Libraries: PyQt5, PyQt6, PySide2, PySide6

## Installation

`PySideExtensions` is not yet on PyPi, so it must be installed from GitHub.

### pip
Using ssh:
`pip install git+ssh://git@github.com/AtakamaLLC/QtPy.git@main`

Using https:
`pip install git+https://github.com/AtakamaLLC/QtPy.git@main`

### poetry
Using ssh:
`poetry add git+ssh://git@github.com/AtakamaLLC/QtPy.git#main`

Using https:
`poetry add git+https://github.com/AtakamaLLC/QtPy.git#main`


## Use

If you have multiple Python implementations of Qt installed, aet the `QT_API` environment variable to the name of the
library you want to use (`PySide2`, `PySide6`, `PyQt5`, or `PyQt6`)

There are three modules in this library to implement Qt-compatible versions of `threading`, `concurrent`, and `asyncio`.
and they are named similarly: `QtPy.qthreading`, `QtPy.qconcurrent`, and `QtPy.qasyncio`.

The nomenclature is different from the Python modules and classes they mimic to resolve ambiguity and prevent namespace
issues. The objects defined here are prefixed with "Qt".

For example, `QtPy.qthreading.QtRLock` is a Qt-friendly implementation of `threading.RLock`. The interface is largely
the same as the Python equivalent and can be used interchangeably in many cases.


## Supported Modules

### Threading
| Python Class | QtPy Class |
| ------------ | ---------- |
| `threading.Lock` | `QtPy.qthreading.QtLock` |
| `threading.RLock` | `QtPy.qthreading.QtRLock` |
| `threading.Condition` | `QtPy.qthreading.QtCondition` |
| `threading.Event` | `QtPy.qthreading.QtEvent` |
| `threading.Semaphore` | `QtPy.qthreading.QtSemaphore` |
| `threading.Thread` | `QtPy.qthreading.QtThread` |
| `threading.Timer` | `QtPy.qthreading.QtTimer` |

### Concurrent
| Python Class | QtPy Class |
| ------------ | ---------- |
| `concurrent.futures.Future` | `QtPy.qconcurrent.QtFuture` |
| `concurrent.futures.ThreadPoolExecutor` | `QtPy.qconcurrent.QtThreadPoolExecutor` |

### Asyncio

| Python Class | QtPy Class |
| ------------ | ---------- |
| `asyncio.ProactorEventLoop` | `QtPy.qasyncio.QtProactorEventLoop` |
| `asyncio.SelectorEventLoop` | `QtPy.qasyncio.QtSelectorEventLoop` |

Additionally, there is a third object, `QtEventLoop`, which will select one of the two above implementations
depending on the active operating system. If running Windows, use `QtProactorEventLoop`, and if not, use
`QtSelectorEventLoop`.
