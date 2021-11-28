#!/usr/bin/env bash

QT_API=pyside2 pytest ./tests
QT_API=pyside6 pytest ./tests
QT_API=pyqt5 pytest ./tests
QT_API=pyqt6 pytest ./tests
