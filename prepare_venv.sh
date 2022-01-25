#!/usr/bin/env bash

python -m pip install --upgrade pip
python -m pip install virtualenv
mv env env-bk || true
python -m virtualenv env
