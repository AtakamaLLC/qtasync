# QtPy

## Overview
Add `asyncio` support to applications running a `QCoreApplication` or one of its subprocesses by
utilizing the `QCoreApplication` event loop as a `asyncio.BaseEventLoop`.

## Requirements
* Supported Python Versions: Python 3.7+
* Supported Qt Libraries: PyQt5, PyQt6, PySide2, PySide6

## Installation

`PySideExtensions` is not yet on PyPi, so it must be installed from GitHub.


## Use

If you have multiple Python implementations of Qt installed, aet the `QT_API` environment variable according to the
following table:

| QT_API value | Qt Implementation |
| ------------ | ----------------- |
| pyside2 | PySide2 |
| pyside6 | PySide6 |
| pyqt5 | PyQt5 |
| pyqt6 | PyQt6 |
