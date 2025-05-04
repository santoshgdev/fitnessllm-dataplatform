FROM python:3.12.2-slim
# Python configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/var/poetry" \
    POETRY_NO_INTERACTION=1

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}


# Set up application directory
RUN mkdir /app
WORKDIR /app

COPY fitnessllm_dataplatform ./fitnessllm_dataplatform
COPY cloud_functions ./cloud_functions
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.in-project true
RUN poetry lock
RUN poetry install --no-root
RUN poetry export -f requirements.txt -o requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080

# Run the HTTP server
ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
