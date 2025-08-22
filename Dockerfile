FROM --platform=linux/amd64 mambaorg/micromamba:2.3.0

# Keep micromamba auto-activation
ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# Ensure we’re root for installs and FS setup
USER root

# Create a writable workspace owned by UID 1000 (mambauser)
RUN mkdir -p /workspace && chown -R 1000:1000 /workspace

# Create your env
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

WORKDIR /workspace

# This is the key change
COPY --chown=1000:1000 . /workspace

# Drop privileges so writes happen as mambauser
USER 1000:1000

CMD ["bash"]
