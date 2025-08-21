#!/bin/bash
apt-get update && apt-get install -y python3-pip
pip3 install dask distributed

nohup dask-scheduler --host 0.0.0.0 --port 8786 &> scheduler.log &
