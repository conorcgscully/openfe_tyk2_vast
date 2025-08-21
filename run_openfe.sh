#!/bin/bash
set -e
# Activate conda environment if used, else inside Docker it's ready
# conda activate openfe_tyk2

python plan_and_run.py
