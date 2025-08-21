import subprocess
import os
import sys
import requests
from pathlib import Path

test_config_loc = "https://raw.githubusercontent.com/conorcgscully/openfe_tyk2_vast/refs/heads/main/tyk2_json/lig_ejm_31_lig_ejm_47_solvent.json"
test_config_str = requests.get(test_config_loc).text
test_config_fname = "test_config.json"
Path(test_config_fname).write_text(test_config_str)


job_id = Path(test_config_fname).stem
workdir = f"work_{job_id}"
os.makedirs(workdir, exist_ok=True)

# Run quickrun on the given config
subprocess.run([
    "openfe", "quickrun",
    test_config_fname,
    "-o", f"results_{job_id}.json",
    "-d", workdir
], check=True)

print(f"Finished job {job_id}")
