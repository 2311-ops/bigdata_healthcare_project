# Setup Guide

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose
- At least 8 GB RAM available for the stack
- Optional: Git Bash or WSL for running the `.sh` helper scripts on Windows

## Start the Stack

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

## Run the Pipeline

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

## Metabase Setup

Open Metabase at `http://localhost:3000` and connect it to PostgreSQL using:

- **Host:** `postgres`
- **Port:** `5432`
- **Database:** `healthcare_dw`
- **Username:** `healthcare`
- **Password:** `healthcare123`

## Suggested Dashboards

- Risk distribution (high vs. low risk donut chart)
- High-risk vs. low-risk patient counts by sex
- Model performance metrics (accuracy, F1, precision, recall)
- Top 20 medicinal products by high-risk event volume
- Prediction analytics over time (by receipt date)

## Troubleshooting

### Kafka not ready
```bash
docker compose logs kafka --tail 50
scripts/check_kafka.sh
```

### HDFS namenode slow to start
The namenode can take 30–60 seconds on first boot. `start_all_services.sh` waits up to 300 seconds automatically.

### Spark job OOM
Reduce `SPARK_EXECUTOR_MEMORY` or `SPARK_DRIVER_MEMORY` in `.env` if running on 8 GB RAM. Set `SPARK_SHUFFLE_PARTITIONS=2` for smaller datasets.

### Metabase can't connect to PostgreSQL
Ensure you are using the internal Docker hostname `postgres` (not `localhost`) when configuring the database connection inside Metabase.
