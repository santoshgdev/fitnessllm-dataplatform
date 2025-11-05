# fitnessllm-dataplatform

[![codecov](https://codecov.io/gh/santoshgdev/fitnessllm-dataplatform/graph/badge.svg?token=7448321QM5)](https://codecov.io/gh/santoshgdev/fitnessllm-dataplatform)

A data platform for ingesting and processing fitness data from Strava, built with Google Cloud Platform, Firebase, and Python. This project serves as the backend for a fitness-related LLM application.

## Features

*   **Strava Data Ingestion**: Ingests activities, streams, and other data from the Strava API.
*   **ETL Pipelines**: Processes raw data through bronze and silver layers into a structured format.
*   **API**: Provides endpoints for interacting with the processed data.
*   **Authentication**: Handles Strava OAuth authentication and token refreshes.
*   **Serverless**: Deployed as serverless functions on Google Cloud Platform.

## Architecture

The platform is built on a serverless architecture using Google Cloud Platform. The data flows through the following stages:

1.  **Authentication**: The `strava_auth_initiate` Cloud Function handles the initial Strava OAuth2 authentication. The `token_refresh` Cloud Function securely stores and refreshes user tokens. Firebase is used for user management and to associate users with their Strava data.

2.  **Data Ingestion**: A scheduled Cloud Function periodically fetches data from the Strava API using `stravalib`. The raw data is then loaded into a "bronze" table in Google BigQuery.

3.  **ETL Processing**: Another Cloud Function triggers an ETL pipeline. This pipeline reads the raw data from the bronze table, cleans and transforms it, and loads it into a "silver" table in BigQuery, ready for analysis.

4.  **API**: The `api_router` Cloud Function provides a Flask-based API for clients to access the processed data from the silver BigQuery table.

5.  **Caching**: Redis is used to cache API responses and frequently accessed data, reducing latency and BigQuery costs.

The entire application is containerized using Docker, ensuring a consistent environment for development, testing, and deployment.

## Getting Started

### Prerequisites

*   [pyenv](https://github.com/pyenv/pyenv)
*   [Poetry](https://python-poetry.org/)
*   [Docker](https://www.docker.com/)

### Installation

1.  **Set up the environment:**
    ```bash
    make setup
    ```

## Usage

### Running the Application

To run a bash session within the application's Docker container:

```bash
make run
```

### Running Tests

To run the test suite:

```bash
make test
```

### Linting

To run the linter and code formatter:

```bash
make lint
```

## Deployment

Deployment is automated via GitHub Actions. The workflow, defined in `.github/workflows/dev-deploy.yaml`, builds and pushes the Docker images to a container registry.