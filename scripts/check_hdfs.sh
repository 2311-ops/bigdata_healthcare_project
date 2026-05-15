#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

docker compose exec -T namenode bash -lc 'hdfs dfs -ls /healthcare && hdfs dfs -ls /healthcare/raw && hdfs dfs -ls /healthcare/processed && hdfs dfs -ls /healthcare/models && hdfs dfs -ls /healthcare/reporting'
