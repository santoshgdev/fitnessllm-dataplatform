ARG BASE_IMAGE=base:latest
FROM ${BASE_IMAGE}

ARG CACHEBUST=1
RUN echo $CACHEBUST

# Install git for the build process
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone and install the shared package
RUN git clone https://github.com/santoshgdev/fitnessllm-shared.git /tmp/fitnessllm-shared && \
    cd /tmp/fitnessllm-shared && \
    git checkout main && \
    poetry add /tmp/fitnessllm-shared && \
    rm -rf /tmp/fitnessllm-shared

RUN poetry install --no-interaction --no-root
RUN poetry run python -c "import fitnessllm_shared; print(fitnessllm_shared.__file__)"

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
