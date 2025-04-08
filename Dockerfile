FROM python:3.12.2-slim

# Python configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY . .

# Install dependencies directly from poetry.lock
RUN pip install --no-cache-dir poetry==2.0.1 && \
    poetry export -f requirements.txt --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

ENV PORT=8080

# Run with system Python
CMD ["python", "-m", "fitnessllm_dataplatform.http_handler"]
