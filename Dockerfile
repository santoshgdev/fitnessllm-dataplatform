FROM python:3.12.2-slim

RUN ["apt-get", "update"]
RUN ["apt-get", "install", "-y", "zsh"]
RUN wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh || true


# Python configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/opt/poetry" \
    #POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

#RUN mkdir /app/fitnessllm-dataplatform -p
#WORKDIR /app/fitnessllm-dataplatform
#COPY poetry.lock .
WORKDIR /app
COPY pyproject.toml .
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-root

CMD ["tail", "-f", "/dev/null"]
