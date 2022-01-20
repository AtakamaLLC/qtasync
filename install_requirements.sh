#!/usr/bin/env bash

while read -r req
do
  if [[ $req == PySide* ]] || [[ $req == PyQt* ]]
  then
    python -m pip install "$req" || true
  else
    python -m pip install "$req"
  fi
done < requirements.txt
