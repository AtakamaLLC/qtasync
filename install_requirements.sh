#!/usr/bin/env bash

python -m pip install --upgrade pip
python -m pip install poetry
poetry install
poetry install -E PySide2 || true
poetry install -E PySide6 || true
poetry install -E PyQt5 || true
poetry install -E PyQt6 || true
