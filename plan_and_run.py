import subprocess
import os
import sys

# Expect config path (JSON) as input
if len(sys.argv) < 2:
    print("Usage: python plan_and_run.py CONFIG.json")
    sys.exit(1)

config = sys.argv[1]
job_id = os.path.basename(config).replace(".json", "")
workdir = f"work_{job_id}"
os.makedirs(workdir, exist_ok=True)

# Run quickrun on the given config
subprocess.run([
    "openfe", "quickrun",
    config,
    "-o", f"results_{job_id}.json",
    "-d", workdir
], check=True)

print(f"Finished job {job_id}")
