FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

USER $MAMBA_USER
RUN micromamba install -y -c conda-forge \
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
COPY --chown=$MAMBA_USER:$MAMBA_USER . /workspace

# Activate the base environment and run bash
CMD ["/usr/local/bin/_entrypoint.sh", "bash"]