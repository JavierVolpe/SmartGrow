#!/bin/bash

cd /home/debian/SmartGrow || exit
source venv/bin/activate

nohup python app.py > log_app.log 2>&1 &
nohup python log_data.py > log_data.log 2>&1 &
