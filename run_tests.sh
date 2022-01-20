#!/usr/bin/env bash


qt_libs=("PySide2" "PySide6" "PyQt5" "PyQt6")
exit_codes=(0 0 0 0)
missing_libs=(0 0 0 0)
failures=0
present_libs_count=0
missing_libs_count=0

for (( idx=0; idx<${#qt_libs[@]}; idx++ ))
do
    i=${qt_libs[$idx]}
    if pip show -q $i
    then
        echo "Running tests using $i"
        present_libs_count=$((present_libs_count + 1))
        QT_API=pyside2 pytest ./tests
        code=$?
        exit_codes[$idx]=$code
        if [ $code -ne 0 ]
        then
            failures=$((failures + 1))
        fi
    else
        echo "Skipping $i tests since it is not installed"
        missing_libs[$idx]=1
        missing_libs_count=$((missing_libs_count + 1))
    fi
done

echo "Ran all tests with ${present_libs_count} Qt implementations"
echo "The test suite failed for ${failures} of them"
echo "And ${missing_libs_count} Qt implementations were missing"

if [ $failures -gt 0 ]
then
    exit $failures
fi

if [ $missing_libs_count -eq ${#qt_libs[@]} ]
then
    echo "No Qt librariers were installed!"
    exit 1
fi

