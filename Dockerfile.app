ARG BASE_IMAGE=base:latest
FROM ${BASE_IMAGE}

RUN mkdir /app
WORKDIR /app
RUN mkdir fitnessllm-dataplatform

# Clone and install fitnessllm-shared
RUN git clone https://github.com/santoshgdev/fitnessllm-shared.git /tmp/fitnessllm-shared \
    && cd /tmp/fitnessllm-shared \
    && pip install -e . \
    && cd /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true \
    && poetry lock \
    && poetry install --no-root \
    && poetry run pip install -e /tmp/fitnessllm-shared \
    && poetry lock \
    && poetry export -f requirements.txt -o requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt

COPY fitnessllm_dataplatform fitnessllm-dataplatform/fitnessllm_dataplatform
COPY cloud_functions fitnessllm-dataplatform/cloud_functions
COPY tests fitnessllm-dataplatform/tests

WORKDIR /app/fitnessllm-dataplatform

# Get and set the commit hash as an environment variable
ARG FITNESSLLM_SHARED_COMMIT_HASH
RUN FITNESSLLM_SHARED_COMMIT_HASH=$(cd /tmp/fitnessllm-shared && git rev-parse HEAD | cut -c1-5)
ENV FITNESSLLM_SHARED_COMMIT_HASH=${FITNESSLLM_SHARED_COMMIT_HASH}

# Verify the shared package is installed and accessible
RUN poetry run python -c "import fitnessllm_shared; print(fitnessllm_shared.__file__)"

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
