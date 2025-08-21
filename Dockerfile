FROM condaforge/miniforge3

RUN conda install -y -c conda-forge \
    python=3.10 \
    requests \
    openmm \
    openfe \
    openff-toolkit \
    rdkit \
    dask \
    distributed \
    pip && \
    conda clean --all --yes

WORKDIR /workspace
COPY . /workspace
CMD ["bash"]
