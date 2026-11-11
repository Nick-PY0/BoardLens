#!/bin/zsh
cd "${0:A:h}" || exit 1
if command -v python3 >/dev/null 2>&1; then
    python3 launch.py
elif [ -x /usr/bin/python3 ]; then
    /usr/bin/python3 launch.py
else
    echo "Install Python 3.12 from https://www.python.org/downloads/ and run this again."
    exit 1
fi
if [ $? -ne 0 ]; then
    echo "Press Enter to close."
    read REPLY
fi
