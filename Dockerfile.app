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
RUN cd /tmp/fitnessllm-shared && \
    echo "Setting commit hash to: $(git rev-parse HEAD | cut -c1-5)" && \
    echo "$(git rev-parse HEAD | cut -c1-5)" > /app/commit_hash.txt

# Create entrypoint script
RUN echo '#!/bin/bash\n\
export FITNESSLLM_SHARED_COMMIT_HASH=$(cat /app/commit_hash.txt)\n\
exec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
