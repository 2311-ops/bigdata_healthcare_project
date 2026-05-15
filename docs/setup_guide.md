i need # Setup Guide

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose
- At least 8 GB RAM available for the stack
- Optional: Git Bash or WSL for running the `.sh` helper scripts on Windows

## Start the stack

1. Populate `.env` if you want to change ports, credentials, or API settings.
2. Run:

```bash
scripts/start_all_services.sh
```

3. Confirm the services are healthy:

```bash
scripts/check_kafka.sh
scripts/check_hdfs.sh
scripts/check_postgres.sh
```

## Run the pipeline

1. Start the API producer:

```bash
scripts/run_api_ingestion.sh
```

2. Start the Spark cleaning stream:

```bash
scripts/run_phase2.sh
```

3. Run the ML pipeline:

```bash
scripts/run_phase3.sh
```

4. Run reporting aggregation:

```bash
scripts/run_phase4.sh
```

## Metabase setup

Open Metabase at `http://localhost:3000` and connect it to PostgreSQL using:

- Host: `postgres`
- Port: `5432`
- Database: `healthcare_dw`
- Username: `healthcare`
- Password: `healthcare123`

## Suggested dashboards

- Risk distribution
- High-risk vs low-risk patients
- Model performance
- Prediction analytics
