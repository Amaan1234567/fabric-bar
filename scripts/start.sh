#!/bin/bash

source /home/amaan/Documents/fabric-bar/venv/bin/activate
cd /home/amaan/Documents/fabric-bar

python start_shell.py & disown
python side-monitors.py --monitor-id 1 & disown