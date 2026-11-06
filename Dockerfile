FROM condaforge/miniforge3:latest
WORKDIR /app
COPY environment.yml .
RUN conda env create -q -f environment.yml -y && conda clean -afy
COPY . .
ENV PATH=/opt/conda/envs/knn-paralelo/bin:$PATH \
    EN_DOCKER=1 \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 \
    PRTE_ALLOW_RUN_AS_ROOT=1 \
    PRTE_ALLOW_RUN_AS_ROOT_CONFIRM=1
ENTRYPOINT ["./replicar.sh"]
