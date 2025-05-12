#!/bin/bash

# Set variables
PROJECT_ID="your-project-id"
REGION="us-west1"
REPOSITORY="fitnessllm-functions"
IMAGE_NAME="fitnessllm-functions"
TAG="latest"

# Build the container
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$TAG .

# Push to Artifact Registry
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$TAG
