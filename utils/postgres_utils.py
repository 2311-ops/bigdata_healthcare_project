"""PostgreSQL helpers used by the supporting scripts and producer."""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as PGConnection
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

LOGGER = logging.getLogger(__name__)


def get_postgres_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "healthcare_dw")
    user = os.getenv("POSTGRES_USER", "healthcare")
    password = os.getenv("POSTGRES_PASSWORD", "healthcare123")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def create_engine_from_env() -> Engine:
    return create_engine(get_postgres_dsn(), pool_pre_ping=True, future=True)


def wait_for_postgres(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                dbname=os.getenv("POSTGRES_DB", "healthcare_dw"),
                user=os.getenv("POSTGRES_USER", "healthcare"),
                password=os.getenv("POSTGRES_PASSWORD", "healthcare123"),
            ):
                LOGGER.info("PostgreSQL is ready")
                return
        except Exception as exc:  # pragma: no cover - defensive startup guard
            LOGGER.warning("Waiting for PostgreSQL: %s", exc)
            time.sleep(5)
    raise TimeoutError("PostgreSQL did not become ready in time")


@contextmanager
def get_connection() -> Iterator[PGConnection]:
    connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "healthcare_dw"),
        user=os.getenv("POSTGRES_USER", "healthcare"),
        password=os.getenv("POSTGRES_PASSWORD", "healthcare123"),
    )
    try:
        yield connection
    finally:
        connection.close()


def run_sql_file(sql_file: str | Path) -> None:
    path = Path(sql_file)
    sql_text = path.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_text)
        conn.commit()


def execute_scalar(query: str):
    with create_engine_from_env().connect() as connection:
        return connection.execute(text(query)).scalar_one_or_none()
