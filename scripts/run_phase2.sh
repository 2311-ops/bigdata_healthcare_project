#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

KAFKA_DEADLINE=$((SECONDS + 300))
until docker compose exec -T kafka bash -lc 'echo >/dev/tcp/localhost/9092' >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$KAFKA_DEADLINE" ]; then
    echo "Kafka did not become ready within 300 seconds." >&2
    echo "Try: docker compose logs kafka --tail 200" >&2
    exit 1
  fi
  sleep 5
done

docker compose exec spark-master bash -lc 'spark-submit \
  --master spark://spark-master:7077 \
  --packages org.postgresql:postgresql:42.7.3 \
  /workspace/spark_jobs/phase2_cleaning_stream.py'
