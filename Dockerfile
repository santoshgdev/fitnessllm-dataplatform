FROM python:3.12.2-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/var/poetry" \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    dash \
    bash \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

RUN mkdir /app
WORKDIR /app
RUN mkdir fitnessllm-dataplatform

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true \
    && poetry lock \
    && poetry install --no-root \
    && poetry export -f requirements.txt -o requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt

COPY fitnessllm_dataplatform fitnessllm-dataplatform/fitnessllm_dataplatform
COPY cloud_functions fitnessllm-dataplatform/cloud_functions
COPY tests fitnessllm-dataplatform/tests

WORKDIR /app/fitnessllm-dataplatform

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
