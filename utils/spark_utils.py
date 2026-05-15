"""Spark helpers for the healthcare analytics pipeline."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from pyspark.sql import DataFrame, SparkSession


def build_spark_session(app_name: str, extra_conf: Dict[str, str] | None = None) -> SparkSession:
    builder = SparkSession.builder.appName(app_name)
    builder = builder.config("spark.sql.session.timeZone", os.getenv("TZ", "Africa/Cairo"))
    builder = builder.config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "4"))
    builder = builder.config("spark.hadoop.fs.defaultFS", os.getenv("HDFS_URI", "hdfs://namenode:8020"))
    builder = builder.config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
    builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    builder = builder.config("spark.sql.sources.partitionOverwriteMode", "dynamic")
    if extra_conf:
        for key, value in extra_conf.items():
            builder = builder.config(key, value)
    return builder.getOrCreate()


def postgres_jdbc_url() -> str:
    return os.getenv("POSTGRES_JDBC_URL", "jdbc:postgresql://postgres:5432/healthcare_dw")


def postgres_jdbc_properties() -> Dict[str, str]:
    return {
        "user": os.getenv("POSTGRES_USER", "healthcare"),
        "password": os.getenv("POSTGRES_PASSWORD", "healthcare123"),
        "driver": "org.postgresql.Driver",
    }


def write_dataframe_to_postgres(
    df: DataFrame,
    table_name: str,
    mode: str = "append",
    extra_options: Dict[str, str] | None = None,
) -> None:
    writer = df.write.format("jdbc").option("url", postgres_jdbc_url()).option("dbtable", table_name).options(
        **postgres_jdbc_properties()
    )
    if extra_options:
        writer = writer.options(**extra_options)
    writer.mode(mode).save()


def read_parquet_paths(spark: SparkSession, paths: Iterable[str]) -> DataFrame:
    existing_paths: List[str] = [path for path in paths if path]
    if not existing_paths:
        raise ValueError("No parquet paths provided")
    return spark.read.parquet(*existing_paths)
