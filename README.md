# QtAsync

## Overview
Add `asyncio` support to applications running a `QCoreApplication` or one of its subprocesses by
utilizing the `QCoreApplication` event loop as a `asyncio.BaseEventLoop`.

## Requirements
* Supported Python Versions: Python 3.9
* Supported Qt Libraries: PyQt5, PyQt6, PySide2, PySide6

## Installation

`QtAsync` is not yet on PyPi, so it must be installed from GitHub.

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
and they are named similarly: `QtAsync.qthreading`, `QtAsync.qconcurrent`, and `QtAsync.qasyncio`.

The nomenclature is different from the Python modules and classes they mimic to resolve ambiguity and prevent namespace
issues. The objects defined here are prefixed with "Qt".

For example, `QtAsync.qthreading.QtRLock` is a Qt-friendly implementation of `threading.RLock`. The interface is largely
the same as the Python equivalent and can be used interchangeably in many cases.


## Supported Modules

### Threading
| Python Class | QtAsync Class |
| ------------ | ---------- |
| `threading.Lock` | `QtAsync.qthreading.QtLock` |
| `threading.RLock` | `QtAsync.qthreading.QtRLock` |
| `threading.Condition` | `QtAsync.qthreading.QtCondition` |
| `threading.Event` | `QtAsync.qthreading.QtEvent` |
| `threading.Semaphore` | `QtAsync.qthreading.QtSemaphore` |
| `threading.Thread` | `QtAsync.qthreading.QtThread` |
| `threading.Timer` | `QtAsync.qthreading.QtTimer` |

### Concurrent
| Python Class | QtAsync Class |
| ------------ | ---------- |
| `concurrent.futures.Future` | `QtAsync.qconcurrent.QtFuture` |
| `concurrent.futures.ThreadPoolExecutor` | `QtAsync.qconcurrent.QtThreadPoolExecutor` |

### Asyncio

| Python Class | QtAsync Class |
| ------------ | ---------- |
| `asyncio.ProactorEventLoop` | `QtAsync.qasyncio.QtProactorEventLoop` |
| `asyncio.SelectorEventLoop` | `QtAsync.qasyncio.QtSelectorEventLoop` |

Additionally, there is a third object, `QtEventLoop`, which will select one of the two above implementations
depending on the active operating system. If running Windows, use `QtProactorEventLoop`, and if not, use
`QtSelectorEventLoop`.
