"""Kafka helpers for the healthcare analytics pipeline."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict

from kafka import KafkaAdminClient, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str
    topic: str
    client_id: str = "healthcare-analytics"
    partitions: int = 1
    replication_factor: int = 1


def load_kafka_settings() -> KafkaSettings:
    return KafkaSettings(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        topic=os.getenv("KAFKA_TOPIC", "healthcare_raw"),
        client_id=os.getenv("KAFKA_CLIENT_ID", "healthcare-analytics"),
        partitions=int(os.getenv("KAFKA_TOPIC_PARTITIONS", "1")),
        replication_factor=int(os.getenv("KAFKA_TOPIC_REPLICATION_FACTOR", "1")),
    )


def create_kafka_producer(settings: KafkaSettings | None = None) -> KafkaProducer:
    settings = settings or load_kafka_settings()
    return KafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
        client_id=settings.client_id,
        acks="all",
        retries=5,
        linger_ms=50,
        compression_type="gzip",
        value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if value else None,
    )


def wait_for_kafka(bootstrap_servers: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
            connected = producer.bootstrap_connected()
            producer.close()
            if connected:
                LOGGER.info("Kafka is reachable at %s", bootstrap_servers)
                return
            LOGGER.info("Kafka client created, waiting for broker handshake at %s", bootstrap_servers)
        except Exception as exc:  # pragma: no cover - defensive startup guard
            LOGGER.warning("Waiting for Kafka: %s", exc)
        time.sleep(5)
    raise TimeoutError(f"Kafka was not reachable at {bootstrap_servers} within {timeout_seconds} seconds")


def ensure_topic_exists(settings: KafkaSettings | None = None) -> None:
    settings = settings or load_kafka_settings()
    admin = KafkaAdminClient(bootstrap_servers=settings.bootstrap_servers, client_id=settings.client_id)
    try:
        existing_topics = admin.list_topics()
        if settings.topic in existing_topics:
            LOGGER.info("Kafka topic already exists: %s", settings.topic)
            return

        topic = NewTopic(
            name=settings.topic,
            num_partitions=settings.partitions,
            replication_factor=settings.replication_factor,
        )
        admin.create_topics([topic])
        LOGGER.info("Created Kafka topic: %s", settings.topic)
    except TopicAlreadyExistsError:
        LOGGER.info("Kafka topic already existed: %s", settings.topic)
    finally:
        admin.close()


def send_json_message(producer: KafkaProducer, topic: str, payload: Dict[str, Any], key: str | None = None) -> None:
    future = producer.send(topic, key=key, value=payload)
    future.get(timeout=30)


def retry_kafka_action(action, *, retries: int = 5, delay_seconds: int = 2):
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return action()
        except KafkaError as exc:
            last_error = exc
            LOGGER.warning("Kafka error on attempt %s/%s: %s", attempt, retries, exc)
            time.sleep(delay_seconds * attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Kafka action failed without raising a KafkaError")
