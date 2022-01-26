# -*- coding: utf-8 -*-
from setuptools import setup

packages = [
    "qtpy",
    "qtpy.qasyncio",
    "qtpy.qconcurrent",
    "qtpy.qthreading",
    "qtpy.types",
]

package_data = {"": ["*"]}

install_requires = ["poetry>=1.1.12,<2.0.0"]

extras_require = {
    "PyQt5": ["PyQt5>=5.15.6,<6.0.0", "PyQt5-stubs>=5.15.2,<6.0.0"],
    "PyQt6": ["PyQt6>=6.2.2,<7.0.0"],
    "PySide2": ["PySide2==5.15.2"],
    "PySide6": ["PySide6>=6.2.2,<7.0.0"],
}

setup_kwargs = {
    "name": "qtpy",
    "version": "0.1.0",
    "description": "",
    "long_description": None,
    "author": "Brian Cefali",
    "author_email": "brian@atakama.com",
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "python_requires": ">=3.9,<3.10",
}


setup(**setup_kwargs)
