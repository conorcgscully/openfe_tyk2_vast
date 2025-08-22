FROM --platform=linux/amd64 mambaorg/micromamba:2.3.0

RUN micromamba create -y -n myenv -c conda-forge -c omnia -c defaults \
    python=3.10 \
    requests \
    openmm \
    openfe \
    openff-toolkit \
    rdkit \
    dask \
    distributed \
    pip && \
    micromamba clean --all --yes

# Activate the environment by default
ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV MAMBA_DOCKERFILE_ACTIVATE=1

WORKDIR /workspace
COPY . /workspace
CMD ["bash"]