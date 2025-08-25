# OpenFE TYK2 Dask Cluster (NFS-Free)

## Build & Push Docker
```bash
docker build -t yourdocker/openfe-dask:latest .
docker push yourdocker/openfe-dask:latest




git clone https://github.com/conorcgscully/openfe_tyk2_vast.git
cd openfe_tyk2_vast

docker build -t openfe_tyk2_image:latest .

###### debugging docker write permission issues
docker build -f dockerfile_permissions -t write-test .
docker run --rm write-test
######

docker run --gpus all -v "$(pwd)":/workspace -w /workspace -it openfe_tyk2_image:latest bash
docker run -v "$(pwd)":/workspace -w /workspace -it openfe_tyk2_image:latest bash

micromamba activate myenv
python -m openmm.testInstallation

# Install jax with cuda 12 support
pip install --upgrade "jax[cuda12_local]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

openfe quickrun tyk2_json/lig_ejm_31_lig_ejm_47_solvent.json -o /tmp/test.json -d /tmp/wd
openfe quickrun tyk2_json/lig_ejm_31_lig_ejm_47_complex.json -o /tmp/test_complex.json -d /tmp/wd
openfe quickrun tyk2_json/lig_ejm_31_lig_ejm_47_solvent.json -o test.json -d /tmp/wd

# ssh -p 40776 root@207.167.211.138 -L 8080:localhost:8080
