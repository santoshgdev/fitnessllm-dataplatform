FROM python:3.12-slim

WORKDIR /app

# Copy the entire codebase
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install cloud function dependencies
RUN pip install --no-cache-dir functions-framework==3.* \
    requests==2.31.0 \
    firebase-admin>=6.8.0,<7.0.0 \
    google-cloud-firestore>=2.19.0 \
    firebase-functions>=0.1.1 \
    google-cloud-run==0.9.1 \
    beartype>=0.20.2,<0.21.0 \
    google-cloud-functions>=1.13.0

# Install shared library directly from GitHub
RUN pip install --no-cache-dir git+https://github.com/santoshgdev/fitnessllm-shared.git@main#egg=fitnessllm_shared&subdirectory=fitnessllm_shared

# Set environment variables
ENV PYTHONPATH=/app

# The entry point will be specified when running the container
CMD ["functions-framework", "--target=api_router"]
