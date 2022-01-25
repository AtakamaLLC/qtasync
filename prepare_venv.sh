#!/usr/bin/env bash

python -m pip install --upgrade pip
python -m pip install virtualenv
python -m virtualenv env


function activate_venv_nix() {
  source env/bin/activate
}

function activate_venv_win() {
  source env/Scripts/activate
}

if [ "$(uname)" == "Darwin" ]; then
    # Do something under Mac OS X platform
    activate_venv_nix
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    # Do something under GNU/Linux platform
    activate_venv_nix
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then
    # Do something under 32 bits Windows NT platform
    activate_venv_win
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
    # Do something under 64 bits Windows NT platform
    activate_venv_win
fi
