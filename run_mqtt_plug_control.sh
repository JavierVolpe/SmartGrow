#!/bin/bash

# Path to your virtual environment
VENV_PATH="/home/debian/SmartHome/venv/bin/activate"

# Path to your Python script
SCRIPT_PATH="/home/debian/SmartHome/device_control.py"

# Activate the virtual environment
source "$VENV_PATH"

# Run the Python script with the provided argument (on/off)
python "$SCRIPT_PATH" "$1"

# Deactivate the virtual environment
deactivate
