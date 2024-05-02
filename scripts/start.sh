#!/bin/bash

# Install Python 3.10
sudo apt update
sudo apt install -y python3.10 python3.10-venv


# # Install pip for Python 3.10
# wget https://bootstrap.pypa.io/get-pip.py
# sudo python3.10 get-pip.py
# rm get-pip.py

# Update pip
python3.10 -m pip install --upgrade pip

# Create and activate virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install dev requirements from pyproject.toml
python3.10 -m pip install -e ".[dev]"

# Start VSCode
if command -v code &> /dev/null
then
    code .
else
    echo "vscode could not be found."
fi
