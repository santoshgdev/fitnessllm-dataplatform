ARG BASE_IMAGE=base:latest
FROM ${BASE_IMAGE}

RUN mkdir /app
WORKDIR /app
RUN mkdir fitnessllm-dataplatform

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true \
    && poetry lock \
    && poetry install --no-root \
    && poetry lock \
    && poetry export -f requirements.txt -o requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt

COPY fitnessllm_dataplatform fitnessllm-dataplatform/fitnessllm_dataplatform
COPY cloud_functions fitnessllm-dataplatform/cloud_functions
COPY tests fitnessllm-dataplatform/tests

WORKDIR /app/fitnessllm-dataplatform

# Verify the shared package is installed and accessible
RUN poetry run python -c "import fitnessllm_shared; print(fitnessllm_shared.__file__)"

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
