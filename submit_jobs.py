from dask.distributed import Client
import subprocess
import os

HEAD_IP = "HEAD_PRIVATE_IP"  # replace with private IP of head node
client = Client(f"tcp://{HEAD_IP}:8786")

# Function that runs on worker
def run_transform(config_url):
    import subprocess, os, requests

    # Download config
    local_config = os.path.basename(config_url)
    r = requests.get(config_url)
    with open(local_config, "wb") as f:
        f.write(r.content)

    # Run transform
    subprocess.run([
        "python", "/workspace/plan_and_run.py", local_config
    ], check=True)

    # (Optional) Upload results to remote storage
    # Example: scp to head node, or use boto3 for S3

    return f"Completed {local_config}"

# List of config JSONs hosted on GitHub
configs = [
    "https://raw.githubusercontent.com/YOUR_GITHUB/openfe_tyk2_dask/main/configs/job1.json",
    "https://raw.githubusercontent.com/YOUR_GITHUB/openfe_tyk2_dask/main/configs/job2.json",
    # ...
]

futures = client.map(run_transform, configs)
results = client.gather(futures)
print("All jobs finished:", results)
