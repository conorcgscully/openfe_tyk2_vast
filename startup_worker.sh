#!/bin/bash
HEAD_PRIVATE_IP="REPLACE_WITH_HEAD_PRIVATE_IP"

apt-get update && apt-get install -y python3-pip
pip3 install dask distributed requests

export CUDA_VISIBLE_DEVICES=0
nohup dask-worker tcp://$HEAD_PRIVATE_IP:8786 \
  --nthreads 1 --nprocs 1 --memory-limit 0 &> worker-$(hostname).log &
