#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

export DOCKER_CONFIG="${ROOT_DIR}/.docker-config"
mkdir -p "$DOCKER_CONFIG"

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop is not ready. Start or repair Docker Desktop, then try again." >&2
  exit 1
fi

docker compose up -d --build zookeeper kafka namenode datanode postgres spark-master spark-worker metabase

echo "Waiting for ZooKeeper, HDFS, and PostgreSQL to become ready..."

ZOOKEEPER_DEADLINE=$((SECONDS + 300))
until docker compose exec -T zookeeper bash -lc 'echo >/dev/tcp/localhost/2181' >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$ZOOKEEPER_DEADLINE" ]; then
    echo "ZooKeeper did not become ready within 300 seconds." >&2
    echo "Try: docker compose logs zookeeper --tail 200" >&2
    exit 1
  fi
  sleep 5
done

POSTGRES_DEADLINE=$((SECONDS + 300))
until docker compose exec -T postgres pg_isready -U healthcare -d healthcare_dw >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$POSTGRES_DEADLINE" ]; then
    echo "PostgreSQL did not become ready within 300 seconds." >&2
    echo "Try: docker compose logs postgres --tail 200" >&2
    exit 1
  fi
  sleep 5
done

HDFS_DEADLINE=$((SECONDS + 300))
until docker compose exec -T namenode bash -lc 'curl -fsS http://localhost:9870 >/dev/null' >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$HDFS_DEADLINE" ]; then
    echo "HDFS did not become ready within 300 seconds." >&2
    echo "Try: docker compose logs namenode --tail 200" >&2
    exit 1
  fi
  sleep 5
done

"${SCRIPT_DIR}/create_kafka_topic.sh"
docker compose exec -T namenode bash -lc 'hdfs dfs -mkdir -p /healthcare/raw /healthcare/processed /healthcare/models /healthcare/reporting /healthcare/checkpoints'

echo "Infrastructure services are up and the Kafka topic plus HDFS directories are ready."
