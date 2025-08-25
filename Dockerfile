FROM --platform=linux/amd64 mambaorg/micromamba:2.3.0

# Keep micromamba auto-activation
ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# # Ensure we’re root for installs and FS setup
# USER root

# Create a non-root user that matches common UID/GID ranges used by container platforms
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

# Create directories with proper ownership
RUN mkdir -p /workspace && \
    chown -R appuser:appgroup /workspace && \
    chmod -R 755 /workspace


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
COPY . /workspace

# Drop privileges so writes happen as mambauser
USER appuser

CMD ["bash"]
