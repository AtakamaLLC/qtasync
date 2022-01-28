# QtPy

## Overview
Add `asyncio` support to applications running a `QCoreApplication` or one of its subprocesses by
utilizing the `QCoreApplication` event loop as a `asyncio.BaseEventLoop`.

## Requirements
* Supported Python Versions: Python 3.9
* Supported Qt Libraries: PyQt5, PyQt6, PySide2, PySide6

## Installation

`PySideExtensions` is not yet on PyPi, so it must be installed from GitHub.


## Use

If you have multiple Python implementations of Qt installed, aet the `QT_API` environment variable to the name of the
library you want to use (`PySide2`, `PySide6`, `PyQt5`, or `PyQt6`)

There are three modules in this library to implement Qt-compatible versions of `threading`, `concurrent`, and `asyncio`.
and they are named similarly: `QtPy.qthreading`, `QtPy.qconcurrent`, and `QtPy.qasyncio`.

The nomenclature is different from the Python modules and classes they mimic.

Pythonic{Object} is a Pythonified version of that Qt object.

For example, `QMutex` is modeled with `PythonicQMutex` and supports the same interface as `threading.Lock`.
