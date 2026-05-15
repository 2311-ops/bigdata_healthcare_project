#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

WARMUP_SECONDS="${PIPELINE_WARMUP_SECONDS:-180}"

echo "Starting the full healthcare analytics pipeline..."
"${SCRIPT_DIR}/start_all_services.sh"

echo "Starting the Spark Structured Streaming cleaner..."
docker compose exec -d spark-master bash -lc 'spark-submit \
  --master spark://spark-master:7077 \
  --packages org.postgresql:postgresql:42.7.3 \
  /workspace/spark_jobs/phase2_cleaning_stream.py'

echo "Starting the API producer..."
docker compose up -d producer

echo "Waiting ${WARMUP_SECONDS}s for cleaned data to accumulate..."
sleep "${WARMUP_SECONDS}"

echo "Running the Spark MLlib pipeline..."
"${SCRIPT_DIR}/run_phase3.sh"

echo "Running the reporting pipeline..."
"${SCRIPT_DIR}/run_phase4.sh"

echo "Full pipeline has been launched successfully."
echo "The producer and streaming cleaner will keep running in the background."
