#!/usr/bin/env bash

echo "Running tests using PySide2"
QT_API=pyside2 pytest ./tests
pyside2_exit_code=$?
echo "Running tests using PySide6"
QT_API=pyside6 pytest ./tests
pyside6_exit_code=$?
echo "Running tests using PyQt5"
QT_API=pyqt5 pytest ./tests
pyqt5_exit_code=$?
echo "Running tests using PyQt6"
QT_API=pyqt6 pytest ./tests
pyqt6_exit_code=$?

if [ $pyside2_exit_code -eq 0 ]
then
    echo "PySide2 tests ran successfully"
else
    echo "PySide2 tests failed!"
fi

if [ $pyside6_exit_code -eq 0 ]
then
    echo "PySide6 tests ran successfully"
else
    echo "PySide6 tests failed!"
fi

if [ $pyqt5_exit_code -eq 0 ]
then
    echo "PyQt5 tests ran successfully"
else
    echo "PyQt5 tests failed!"
fi

if [ $pyqt6_exit_code -eq 0 ]
then
    echo "PyQt6 tests ran successfully"
else
    echo "PyQt6 tests failed!"
fi

