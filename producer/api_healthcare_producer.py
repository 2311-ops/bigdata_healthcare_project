"""Continuous openFDA -> Kafka ingestion for healthcare adverse-event data."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests
from requests import Response, Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.kafka_utils import (  # noqa: E402
    KafkaSettings,
    create_kafka_producer,
    ensure_topic_exists,
    load_kafka_settings,
    retry_kafka_action,
    send_json_message,
    wait_for_kafka,
)

LOGGER = logging.getLogger("healthcare_producer")
STOP_REQUESTED = False


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def handle_shutdown(signum, frame) -> None:  # pragma: no cover - signal handler
    global STOP_REQUESTED
    STOP_REQUESTED = True
    LOGGER.info("Shutdown requested (%s)", signum)


def build_session() -> Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "healthcare-bigdata-project/1.0"})
    return session


def request_with_retries(
    session: Session,
    url: str,
    params: Dict[str, Any],
    timeout_seconds: int,
    max_retries: int,
) -> Response:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout_seconds)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "10"))
                LOGGER.warning("openFDA rate limited us, sleeping %s seconds", retry_after)
                time.sleep(retry_after)
                continue
            if response.status_code == 404:
                return response
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            wait_seconds = min(2 ** attempt, 60)
            LOGGER.warning("openFDA request failed on attempt %s/%s: %s", attempt, max_retries, exc)
            time.sleep(wait_seconds)
    if last_error:
        raise last_error
    raise RuntimeError("Request failed without an exception")


def fetch_openfda_page(
    session: Session,
    api_url: str,
    search_query: str,
    limit: int,
    skip: int,
    timeout_seconds: int,
    max_retries: int,
) -> List[Dict[str, Any]]:
    params = {
        "search": search_query,
        "limit": limit,
        "skip": skip,
    }
    response = request_with_retries(session, api_url, params, timeout_seconds, max_retries)
    if response.status_code == 404:
        LOGGER.info("openFDA returned no results for skip=%s", skip)
        return []
    payload = response.json()
    return payload.get("results", [])


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_message(record: Dict[str, Any], settings: KafkaSettings, api_url: str, batch_number: int) -> Dict[str, Any]:
    return {
        "source_api": os.getenv("OPENFDA_SOURCE_NAME", "openFDA drug event API"),
        "ingestion_timestamp": current_utc_iso(),
        "batch_number": batch_number,
        "api_endpoint": api_url,
        "raw_data": json.dumps(record, default=str),
    }


def stream_openfda_to_kafka() -> None:
    api_url = os.getenv("OPENFDA_API_URL", "https://api.fda.gov/drug/event.json")
    search_query = os.getenv("OPENFDA_SEARCH_QUERY", "patient.drug.medicinalproduct:*")
    page_size = int(os.getenv("OPENFDA_PAGE_SIZE", "100"))
    max_pages = int(os.getenv("OPENFDA_MAX_PAGES", "20"))
    timeout_seconds = int(os.getenv("OPENFDA_REQUEST_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.getenv("OPENFDA_MAX_RETRIES", "5"))
    sleep_seconds = int(os.getenv("OPENFDA_SLEEP_SECONDS", "3"))
    settings = load_kafka_settings()

    wait_for_kafka(settings.bootstrap_servers)
    ensure_topic_exists(settings)
    producer = create_kafka_producer(settings)
    session = build_session()

    batch_number = 1
    try:
        while not STOP_REQUESTED:
            records_emitted = 0
            for page in range(max_pages):
                if STOP_REQUESTED:
                    break

                skip = page * page_size
                LOGGER.info("Fetching openFDA page=%s skip=%s batch=%s", page + 1, skip, batch_number)
                results = fetch_openfda_page(
                    session=session,
                    api_url=api_url,
                    search_query=search_query,
                    limit=page_size,
                    skip=skip,
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                )
                if not results:
                    LOGGER.info("No more records returned by openFDA for this cycle")
                    break

                for index, record in enumerate(results, start=1):
                    message = build_message(record, settings, api_url, batch_number)

                    def publish_message() -> None:
                        send_json_message(
                            producer=producer,
                            topic=settings.topic,
                            payload=message,
                            key=record.get("safetyreportid") or f"batch-{batch_number}-{skip + index}",
                        )

                    retry_kafka_action(publish_message, retries=5, delay_seconds=2)
                    records_emitted += 1

                LOGGER.info("Published %s records for page %s", len(results), page + 1)

            LOGGER.info("Batch %s completed with %s records", batch_number, records_emitted)
            batch_number += 1
            if STOP_REQUESTED:
                break
            time.sleep(sleep_seconds)
    finally:
        LOGGER.info("Flushing Kafka producer")
        producer.flush()
        producer.close()


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    stream_openfda_to_kafka()


if __name__ == "__main__":
    main()
