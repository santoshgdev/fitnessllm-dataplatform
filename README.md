# fitnessllm-dataplatform

[![codecov](https://codecov.io/gh/santoshgdev/fitnessllm-dataplatform/graph/badge.svg?token=7448321QM5)](https://codecov.io/gh/santoshgdev/fitnessllm-dataplatform)

A comprehensive data platform for ingesting and processing fitness data from Strava, built with Google Cloud Platform, Firebase, and Python. This project serves as the backend for a fitness-related LLM application, implementing a robust ETL pipeline with bronze and silver data layers.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Data Models](#data-models)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Features

- **Strava Data Ingestion**: Comprehensive ingestion of activities, streams (heartrate, cadence, power, GPS, etc.), and athlete data from the Strava API using `stravalib`
- **Multi-Layer ETL Pipeline**: Processes raw data through bronze and silver layers into structured formats optimized for analytics
- **RESTful API**: Provides secure endpoints for interacting with processed data
- **OAuth2 Authentication**: Handles Strava OAuth authentication flow with secure token encryption and refresh mechanisms
- **Serverless Architecture**: Fully serverless deployment on Google Cloud Platform using Cloud Functions and Cloud Run Jobs
- **Batch Processing**: Efficient batch processing capabilities for multiple users
- **Type Safety**: Full type checking with `beartype` for runtime type validation
- **Comprehensive Logging**: Structured logging throughout the platform for observability

## Architecture

The platform follows a serverless architecture on Google Cloud Platform with a bronze-silver data lakehouse pattern. The data flows through the following stages:

```
???????????????????????????????????????????????????????????????????
?                         Client Application                       ?
???????????????????????????????????????????????????????????????????
                         ?
                         ?
???????????????????????????????????????????????????????????????????
?                    API Router (Cloud Function)                   ?
?  - Routes requests to appropriate services                        ?
?  - Handles authentication and authorization                      ?
???????????????????????????????????????????????????????????????????
       ?                      ?                      ?
       ?                      ?                      ?
????????????????    ????????????????????    ????????????????????
? Strava Auth  ?    ?  Token Refresh   ?    ?   Data Run       ?
?  Initiate    ?    ?  (Cloud Func)    ?    ? (Cloud Run Job)  ?
????????????????    ????????????????????    ????????????????????
       ?                      ?                      ?
       ???????????????????????????????????????????????
                         ?
                         ?
???????????????????????????????????????????????????????????????????
?                    Data Ingestion Layer                           ?
?  - StravaAPIInterface: Fetches activities and streams           ?
?  - Stores raw JSON files in Google Cloud Storage (Bronze)        ?
????????????????????????????????????????????????????????????????????
                             ?
                             ?
???????????????????????????????????????????????????????????????????
?                    Bronze ETL Layer                               ?
?  - BronzeStravaETLInterface: Transforms JSON ? DataFrames        ?
?  - Loads into BigQuery bronze tables                             ?
?  - Tracks metrics and status in metrics table                    ?
????????????????????????????????????????????????????????????????????
                             ?
                             ?
???????????????????????????????????????????????????????????????????
?                    Silver ETL Layer                               ?
?  - SilverStravaETLInterface: Transforms bronze ? silver         ?
?  - Executes SQL transformations                                 ?
?  - Creates aggregated stream tables ready for analysis           ?
????????????????????????????????????????????????????????????????????
                             ?
                             ?
???????????????????????????????????????????????????????????????????
?                    Analytics & Query Layer                        ?
?  - BigQuery tables accessible via API                            ?
?  - Optimized for fast queries and aggregations                   ?
???????????????????????????????????????????????????????????????????
```

### Data Flow Details

1. **Authentication Flow**:
   - User initiates OAuth via `strava_auth_initiate` Cloud Function
   - Authorization code exchanged for access/refresh tokens
   - Tokens encrypted using AES encryption and stored in Firestore
   - User document structure: `users/{uid}/stream/strava/`

2. **Data Ingestion**:
   - `StravaAPIInterface` fetches new activities since last sync
   - Retrieves activity summaries and detailed streams (heartrate, cadence, GPS, etc.)
   - Stores raw JSON files in GCS: `gs://{bronze_bucket}/strava/athlete_id={id}/{stream}/activity_id={id}.json`

3. **Bronze ETL**:
   - Processes JSON files from GCS into Pandas DataFrames
   - Applies stream-specific transformations (e.g., lat/lng extraction)
   - Filters out already-processed activities using metrics table
   - Loads into BigQuery bronze tables: `{env}_bronze_strava.{stream}`
   - Tracks processing metrics in `{env}_metrics.metrics`

4. **Silver ETL**:
   - Executes SQL transformations from bronze to silver layer
   - Joins multiple stream tables into aggregated views
   - Creates optimized tables: `{env}_silver_strava.{table}`
   - Implements delete-and-insert pattern for idempotency

## Project Structure

```
fitnessllm-dataplatform/
??? cloud_functions/              # Google Cloud Functions
?   ??? api_router/               # Main API router
?   ?   ??? main.py              # Routes requests to other services
?   ?   ??? utils/                # Cloud utilities
?   ??? strava_auth_initiate/     # OAuth initiation handler
?   ?   ??? main.py
?   ??? token_refresh/            # Token refresh handler
?       ??? main.py
?       ??? streams/              # Stream-specific refresh logic
?
??? fitnessllm_dataplatform/      # Main package
?   ??? batch_handler.py         # Batch processing for all users
?   ??? task_handler.py          # Main ETL orchestration
?   ??? entities/                 # Data models and enums
?   ?   ??? dataclasses.py       # Metrics dataclass
?   ?   ??? enums.py             # Platform enums
?   ?   ??? mapping.py           # OAuth refresh mappings
?   ??? infrastructure/           # Infrastructure connections
?   ?   ??? FirebaseConnect.py   # Firebase wrapper
?   ??? services/                 # Base service interfaces
?   ?   ??? api_interface.py     # Base API interface
?   ?   ??? etl_interface.py     # Base ETL interface
?   ??? stream/                   # Data source implementations
?   ?   ??? strava/               # Strava-specific code
?   ?       ??? services/         # Strava service implementations
?   ?       ?   ??? api_interface.py
?   ?       ?   ??? bronze_etl_interface.py
?   ?       ?   ??? silver_etl_interface.py
?   ?       ??? entities/         # Strava-specific enums and queries
?   ?       ??? schemas/          # BigQuery schemas
?   ?       ?   ??? bronze/json/  # JSON schemas for bronze tables
?   ?       ?   ??? silver/sql/   # SQL transformations
?   ?       ??? cloud_utils.py    # Storage path utilities
?   ?       ??? etl_utils.py      # Stream-specific transformations
?   ?       ??? qc_utils.py       # Quality checks
?   ??? utils/                    # Shared utilities
?   ?   ??? cloud_utils.py        # GCP utilities
?   ?   ??? query_utils.py        # SQL query builders
?   ?   ??? request_utils.py      # HTTP request handlers
?   ?   ??? task_utils.py         # Task utilities
?   ??? schemas/                  # Platform schemas
?       ??? metrics.json           # Metrics table schema
?
??? tests/                        # Test suite
?   ??? cloud_functions/          # Cloud function tests
?   ??? fitnessllm_dataplatform/  # Package tests
?
??? Dockerfile.base              # Base Docker image
??? Dockerfile.app               # Application Docker image
??? Makefile                     # Build and test commands
??? pyproject.toml               # Poetry dependencies
??? pytest.ini                   # Pytest configuration
??? mypy.ini                     # Type checking configuration
```

## Prerequisites

### Required Software

- **Python 3.12.2**: Managed via pyenv
- **Poetry**: Python dependency management
- **Docker**: Container runtime
- **Google Cloud SDK**: For GCP operations
- **Firebase CLI**: For Firebase operations

### Required Services

- **Google Cloud Project** with:
  - BigQuery API enabled
  - Cloud Functions API enabled
  - Cloud Run API enabled
  - Cloud Storage API enabled
  - Secret Manager API enabled
  - Cloud Build API enabled (for CI/CD)
- **Firebase Project** with:
  - Authentication enabled
  - Firestore database created
- **Strava API Application**:
  - Client ID and Client Secret
  - OAuth redirect URI configured

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/santoshgdev/fitnessllm-dataplatform.git
cd fitnessllm-dataplatform
```

### 2. Set Up Development Environment

The `make setup` command will:
- Install pre-commit hooks
- Set up pyenv
- Install Python 3.12.2
- Install all dependencies via Poetry

```bash
make setup
```

### 3. Build Docker Images

Build the base and application Docker images:

```bash
make build
```

Or clean and rebuild:

```bash
make clean-build
```

## Configuration

### Environment Variables

The platform requires several environment variables to be set:

#### Required for All Components

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ID` | Google Cloud Project ID | `my-project-id` |
| `ENV` | Environment name (dev/staging/prod) | `dev` |
| `STAGE` | Stage name (matches ENV) | `dev` |

#### Required for Cloud Functions

| Variable | Description | Example |
|----------|-------------|---------|
| `REGION` | GCP region | `us-west1` |
| `ENVIRONMENT` | Environment prefix for resources | `dev` |
| `STRAVA_SECRET` | Secret Manager secret name for Strava credentials | `strava-credentials` |
| `ENCRYPTION_SECRET` | Secret Manager secret name for encryption key | `encryption-key` |
| `INFRASTRUCTURE_SECRET` | Secret Manager secret name for infrastructure config | `infrastructure-config` |

#### Optional for ETL Processing

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKER` | Number of parallel workers for processing | `1` (or CPU count) |
| `SAMPLE` | Limit number of files to process (for testing) | `None` |

#### Cloud Run Job Variables (Auto-set)

| Variable | Description |
|----------|-------------|
| `CLOUD_RUN_JOB` | Cloud Run Job name |
| `CLOUD_RUN_EXECUTION` | Execution ID |
| `CLOUD_RUN_TASK_INDEX` | Task index |
| `CLOUD_RUN_TASK_ATTEMPT` | Task attempt number |
| `CLOUD_RUN_TASK_COUNT` | Total task count |

### Secret Manager Configuration

Secrets must be stored in Google Secret Manager with the following structure:

#### `STRAVA_SECRET`
```json
{
  "client_id": "your-strava-client-id",
  "client_secret": "your-strava-client-secret"
}
```

#### `ENCRYPTION_SECRET`
```json
{
  "token": "your-32-byte-encryption-key"
}
```

#### `INFRASTRUCTURE_SECRET`
```json
{
  "dev": {
    "bronze_bucket": "gs://your-bronze-bucket",
    "silver_bucket": "gs://your-silver-bucket"
  },
  "prod": {
    "bronze_bucket": "gs://your-prod-bronze-bucket",
    "silver_bucket": "gs://your-prod-silver-bucket"
  }
}
```

### Firebase Configuration

The Firestore database structure should be:

```
users/
  {uid}/
    uid: string
    ...
    stream/
      strava/
        uid: string
        type: "strava"
        accessToken: string (encrypted)
        refreshToken: string (encrypted)
        expiresAt: timestamp
        scope: string
        athlete: {
          id: integer
          firstname: string
          lastname: string
          profile: string
        }
        firstConnected: timestamp
        lastUpdated: timestamp
        lastTokenRefresh: timestamp
        connected: boolean
        version: string
```

### BigQuery Schema Setup

The platform expects the following BigQuery datasets:

- `{env}_bronze_strava`: Bronze layer tables
  - `activity`: Activity summaries
  - `athlete_summary`: Athlete information
  - `time`, `heartrate`, `cadence`, `watts`, `distance`, `altitude`, `latlng`, `velocity_smooth`, `temp`, `moving`, `grade_smooth`, `power`: Stream tables
  
- `{env}_silver_strava`: Silver layer tables
  - `aggregate_stream`: Aggregated stream data

- `{env}_metrics`: Metrics tracking
  - `metrics`: ETL operation metrics

## Usage

### Running the Application

Start a bash session in the Docker container:

```bash
make run
```

### Running Individual ETL Tasks

#### Using the Task Handler

The `task_handler.py` module provides a command-line interface using Google's `fire` library:

```bash
# Full ETL pipeline (ingest ? bronze ? silver)
python -m fitnessllm_dataplatform.task_handler \
  --uid=user123 \
  --data_source=STRAVA \
  full_etl

# Individual steps
python -m fitnessllm_dataplatform.task_handler \
  --uid=user123 \
  --data_source=STRAVA \
  ingest

python -m fitnessllm_dataplatform.task_handler \
  --uid=user123 \
  --data_source=STRAVA \
  bronze_etl

python -m fitnessllm_dataplatform.task_handler \
  --uid=user123 \
  --data_source=STRAVA \
  silver_etl

# Bronze ETL with specific streams
python -m fitnessllm_dataplatform.task_handler \
  --uid=user123 \
  --data_source=STRAVA \
  bronze_etl \
  --data_streams=["heartrate","cadence"]
```

#### Using Batch Handler

Process all users in the database:

```bash
python -m fitnessllm_dataplatform.batch_handler
```

### Running Tests

Run the full test suite with coverage:

```bash
make test
```

Run tests for a specific module:

```bash
docker run -it \
  -v "$PWD:/app/fitnessllm-dataplatform" \
  fitnessllm-dp:latest \
  bash -c "cd /app/fitnessllm-dataplatform && /app/.venv/bin/pytest tests/fitnessllm_dataplatform/utils/ -v"
```

### Linting

Run pre-commit hooks and linters:

```bash
make lint
```

## API Documentation

### API Router Endpoints

All API requests go through the `api_router` Cloud Function with the following structure:

#### Base URL
```
https://{region}-{project-id}.cloudfunctions.net/{environment}-api-router
```

#### Authentication

All requests require a Firebase ID token in the Authorization header:

```
Authorization: Bearer {firebase-id-token}
```

#### Request Format

```json
{
  "target_api": "api_name",
  "payload": {
    // API-specific payload
  }
}
```

### Available APIs

#### 1. Strava Auth Initiate

**Target API**: `strava_auth_initiate`

**Payload**:
```json
{
  "code": "strava-authorization-code"
}
```

**Response**:
```json
{
  "message": "Strava connection successful",
  "athlete": 12345678
}
```

**Description**: Initiates Strava OAuth flow, exchanges authorization code for tokens, encrypts and stores them in Firestore.

#### 2. Token Refresh

**Target API**: `token_refresh`

**Query Parameter**: `data_source=strava`

**Payload**: Empty object `{}`

**Response**:
```json
{
  "message": "Token refreshed successfully for Strava."
}
```

**Description**: Refreshes OAuth tokens for a specified data source.

#### 3. Data Run

**Target API**: `data_run`

**Payload**:
```json
{
  // uid is automatically added from the authenticated user
}
```

**Response**: Cloud Run Job execution response

**Description**: Triggers a Cloud Run Job to execute the full ETL pipeline for the authenticated user.

### Error Responses

All APIs return consistent error responses:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "diagnostics": {
    // Additional debugging information
  }
}
```

**Status Codes**:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error
- `900-906`: Custom error codes for API router

## Development

### Code Style

The project uses:
- **Black**: Code formatting (88 character line length)
- **beartype**: Runtime type checking
- **pre-commit**: Git hooks for code quality

### Type Checking

The project uses `beartype` for runtime type validation. Type hints are required for all function parameters and return types.

### Adding a New Data Source

1. **Create Stream Module**: Add a new directory under `fitnessllm_dataplatform/stream/{data_source}/`

2. **Implement Services**:
   - `api_interface.py`: Extends `APIInterface`
   - `bronze_etl_interface.py`: Extends `ETLInterface`
   - `silver_etl_interface.py`: Extends `ETLInterface`

3. **Add Enums**: Create enums in `entities/enums.py` for the new data source

4. **Update Mappings**: Add refresh function mapping in `entities/mapping.py`

5. **Add Schemas**: Create BigQuery schemas in `schemas/bronze/json/` and `schemas/silver/sql/`

6. **Update Task Handler**: Add data source handling in `task_handler.py`

### Project Dependencies

Key dependencies:
- `stravalib`: Strava API client
- `pandas`: Data manipulation
- `google-cloud-bigquery`: BigQuery operations
- `firebase-admin`: Firebase SDK
- `cloudpathlib`: Cloud storage paths
- `beartype`: Runtime type checking
- `flask`: Web framework (for Cloud Functions)
- `joblib`: Parallel processing

See `pyproject.toml` for the complete list.

## Testing

### Test Structure

Tests mirror the main codebase structure:

```
tests/
??? cloud_functions/
?   ??? api_router/
?   ??? token_refresh/
?   ??? conftest.py
??? fitnessllm_dataplatform/
    ??? utils/
    ??? data/
```

### Running Tests

```bash
# All tests
make test

# Specific test file
pytest tests/fitnessllm_dataplatform/utils/test_task_utils.py -v

# With coverage report
pytest tests/ --cov --cov-report=html
```

### Writing Tests

- Use `pytest` fixtures from `conftest.py`
- Mock external services (Firebase, BigQuery, Strava API)
- Use `freezegun` for time-based testing
- Follow naming convention: `test_*.py` files with `test_*` functions

## Deployment

### Pre-Deployment Checklist

1. ? All tests passing
2. ? Environment variables configured
3. ? Secrets created in Secret Manager
4. ? BigQuery datasets and tables created
5. ? Firebase project configured
6. ? Docker images built and tested locally

### Deployment Process

Deployment is automated via GitHub Actions (`.github/workflows/dev-deploy.yaml`). The workflow:

1. Builds Docker images
2. Pushes to Google Container Registry
3. Deploys Cloud Functions
4. Updates Cloud Run Jobs

### Manual Deployment

#### Build and Push Docker Images

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-west1"
export REPOSITORY="fitnessllm-functions"
export IMAGE_NAME="fitnessllm-functions"
export TAG="latest"

# Build and push
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$TAG .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$TAG
```

#### Deploy Cloud Functions

```bash
# Deploy API router
gcloud functions deploy ${ENVIRONMENT}-api-router \
  --gen2 \
  --runtime=python312 \
  --region=${REGION} \
  --source=cloud_functions/api_router \
  --entry-point=api_router \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=PROJECT_ID=${PROJECT_ID},REGION=${REGION},ENVIRONMENT=${ENVIRONMENT}

# Deploy Strava auth initiate
gcloud functions deploy ${ENVIRONMENT}-strava-auth-initiate \
  --gen2 \
  --runtime=python312 \
  --region=${REGION} \
  --source=cloud_functions/strava_auth_initiate \
  --entry-point=strava_auth_initiate \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=STRAVA_SECRET=${STRAVA_SECRET},ENCRYPTION_SECRET=${ENCRYPTION_SECRET}

# Deploy token refresh
gcloud functions deploy ${ENVIRONMENT}-token-refresh \
  --gen2 \
  --runtime=python312 \
  --region=${REGION} \
  --source=cloud_functions/token_refresh \
  --entry-point=token_refresh \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=STRAVA_SECRET=${STRAVA_SECRET},ENCRYPTION_SECRET=${ENCRYPTION_SECRET}
```

#### Deploy Cloud Run Job

```bash
gcloud run jobs deploy ${ENVIRONMENT}-fitnessllm-dp \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG} \
  --region=${REGION} \
  --set-env-vars=PROJECT_ID=${PROJECT_ID},ENV=${ENV},STAGE=${STAGE}
```

## Data Models

### Metrics Dataclass

Tracks ETL operation metrics:

```python
@dataclass
class Metrics:
    athlete_id: str
    activity_id: str
    data_source: FitnessLLMDataSource
    data_stream: FitnessLLMDataStream
    record_count: int
    status: Optional[str] = None
    bq_insert_timestamp: Optional[datetime] = None
```

### Strava Streams

Supported Strava data streams:

- `ACTIVITY`: Activity summaries
- `ATHLETE_SUMMARY`: Athlete profile
- `TIME`: Time series
- `HEARTRATE`: Heart rate data
- `CADENCE`: Cadence data
- `WATTS`: Power data
- `DISTANCE`: Distance data
- `ALTITUDE`: Altitude data
- `LATLNG`: GPS coordinates
- `VELOCITY_SMOOTH`: Smoothed velocity
- `TEMP`: Temperature data
- `MOVING`: Moving indicator
- `GRADE_SMOOTH`: Smoothed grade
- `POWER`: Power measurements

## Troubleshooting

### Common Issues

#### 1. Secret Manager Access Errors

**Error**: `Failed to retrieve or decode secret`

**Solution**: 
- Verify service account has `roles/secretmanager.secretAccessor`
- Check secret name matches exactly
- Verify secret exists: `gcloud secrets list`

#### 2. BigQuery Permission Errors

**Error**: `Access Denied: BigQuery`

**Solution**:
- Verify service account has `roles/bigquery.dataEditor` and `roles/bigquery.jobUser`
- Check dataset exists and is accessible

#### 3. Firebase Authentication Errors

**Error**: `Invalid Firebase ID Token`

**Solution**:
- Verify Firebase Admin SDK is initialized
- Check Firebase project credentials
- Ensure token is not expired

#### 4. Strava API Rate Limits

**Error**: `Rate limit exceeded`

**Solution**:
- Implement exponential backoff
- Reduce request frequency
- Check Strava API limits (600 requests per 15 minutes per application)

#### 5. GCS Access Errors

**Error**: `Access Denied: Cloud Storage`

**Solution**:
- Verify service account has `roles/storage.objectAdmin`
- Check bucket exists and is accessible
- Verify bucket path format matches expected structure

### Debugging

Enable detailed logging by setting log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs in Cloud Console:
- Cloud Functions: Cloud Functions ? Logs
- Cloud Run: Cloud Run ? Logs
- Application logs: Cloud Logging ? Logs Explorer

### Performance Optimization

1. **Parallel Processing**: Set `WORKER` environment variable to utilize multiple cores
2. **Batch Size**: Adjust batch sizes in BigQuery load jobs
3. **Incremental Processing**: Use metrics table to skip already-processed activities
4. **Caching**: Implement Redis caching for frequently accessed data

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests
5. Run tests and linting (`make test && make lint`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Review Guidelines

- All code must pass tests and linting
- Type hints required for all functions
- Documentation strings required for public APIs
- Follow existing code style and patterns

## License

[Add your license information here]

## Support

For issues and questions:
- GitHub Issues: [repository issues URL]
- Documentation: [documentation URL]

## Acknowledgments

- Built with [stravalib](https://github.com/hozn/stravalib) for Strava API integration
- Uses [beartype](https://github.com/beartype/beartype) for runtime type checking
- Powered by Google Cloud Platform
