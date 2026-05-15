#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

docker compose exec -T kafka bash -lc 'unset JMX_PORT; kafka-topics --bootstrap-server localhost:9092 --describe --topic healthcare_raw'
