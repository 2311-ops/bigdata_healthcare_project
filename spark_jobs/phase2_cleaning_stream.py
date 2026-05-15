"""Spark Structured Streaming job that cleans healthcare adverse-event records."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    coalesce,
    current_timestamp,
    from_json,
    lit,
    lower,
    regexp_replace,
    trim,
    when,
    expr,
    to_date,
    to_timestamp,
)
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.spark_utils import build_spark_session  # noqa: E402

LOGGER = logging.getLogger("phase2_cleaning_stream")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def envelope_schema() -> StructType:
    return StructType(
        [
            StructField("source_api", StringType(), True),
            StructField("ingestion_timestamp", StringType(), True),
            StructField("batch_number", IntegerType(), True),
            StructField("api_endpoint", StringType(), True),
            StructField("raw_data", StringType(), True),
        ]
    )


def openfda_record_schema() -> StructType:
    reaction_schema = StructType(
        [
            StructField("reactionmeddrapt", StringType(), True),
            StructField("reactionoutcome", StringType(), True),
        ]
    )
    drug_schema = StructType(
        [
            StructField("medicinalproduct", StringType(), True),
            StructField("drugindication", StringType(), True),
            StructField("drugcharacterization", StringType(), True),
            StructField("drugadministrationroute", StringType(), True),
        ]
    )
    patient_schema = StructType(
        [
            StructField("patientsex", StringType(), True),
            StructField("patientage", StringType(), True),
            StructField("patientweight", StringType(), True),
            StructField("reaction", ArrayType(reaction_schema), True),
            StructField("drug", ArrayType(drug_schema), True),
        ]
    )
    return StructType(
        [
            StructField("safetyreportid", StringType(), True),
            StructField("receivedate", StringType(), True),
            StructField("receiptdate", StringType(), True),
            StructField("serious", StringType(), True),
            StructField("seriousnessdeath", StringType(), True),
            StructField("seriousnesshospitalization", StringType(), True),
            StructField("patient", patient_schema, True),
        ]
    )


def clean_batch(batch_df: DataFrame, batch_id: int, processed_path: str, raw_path: str, bad_path: str) -> None:
    parsed = batch_df.withColumn("payload", from_json(col("value"), envelope_schema()))
    parsed = parsed.select("payload.*")
    records = parsed.withColumn("raw_record", from_json(col("raw_data"), openfda_record_schema()))

    valid_records = (
        records.filter(col("raw_record").isNotNull())
        .withColumn("ingestion_ts", to_timestamp(col("ingestion_timestamp")))
        .withColumn("receipt_date", to_date(coalesce(col("raw_record.receiptdate"), col("raw_record.receivedate")), "yyyyMMdd"))
        .withColumn("patient_age", col("raw_record.patient.patientage").cast(DoubleType()))
        .withColumn("patient_weight", col("raw_record.patient.patientweight").cast(DoubleType()))
        .withColumn("patient_sex", lower(trim(coalesce(col("raw_record.patient.patientsex"), lit("unknown")))))
        .withColumn(
            "medicinal_product",
            lower(
                trim(
                    coalesce(
                        col("raw_record.patient.drug").getItem(0).getField("medicinalproduct"),
                        lit("unknown"),
                    )
                )
            ),
        )
        .withColumn(
            "reaction",
            lower(
                trim(
                    coalesce(
                        col("raw_record.patient.reaction").getItem(0).getField("reactionmeddrapt"),
                        lit("unknown"),
                    )
                )
            ),
        )
        .withColumn("serious", when(lower(col("raw_record.serious")).isin("1", "true", "yes"), lit(True)).otherwise(lit(False)))
        .withColumn(
            "seriousness_death",
            when(lower(col("raw_record.seriousnessdeath")).isin("1", "true", "yes"), lit(True)).otherwise(lit(False)),
        )
        .withColumn(
            "seriousness_hospitalization",
            when(lower(col("raw_record.seriousnesshospitalization")).isin("1", "true", "yes"), lit(True)).otherwise(lit(False)),
        )
        .withColumn(
            "risk_label",
            when(col("serious") | col("seriousness_death") | col("seriousness_hospitalization"), lit(1)).otherwise(lit(0)),
        )
        .withColumn("report_id", coalesce(col("raw_record.safetyreportid"), expr("substring(md5(raw_data), 1, 16)")))
        .dropDuplicates(["report_id"])
    )

    cleaned_df = valid_records.select(
        col("report_id"),
        col("source_api"),
        col("ingestion_ts").alias("ingestion_timestamp"),
        col("batch_number"),
        col("api_endpoint"),
        col("receipt_date"),
        when(col("patient_age") < 0, lit(None)).otherwise(col("patient_age")).alias("patient_age"),
        when(col("patient_weight") < 0, lit(None)).otherwise(col("patient_weight")).alias("patient_weight"),
        coalesce(col("patient_sex"), lit("unknown")).alias("patient_sex"),
        coalesce(col("medicinal_product"), lit("unknown")).alias("medicinal_product"),
        coalesce(col("reaction"), lit("unknown")).alias("reaction"),
        col("serious"),
        col("seriousness_death"),
        col("seriousness_hospitalization"),
        col("risk_label"),
        col("raw_data").alias("raw_record"),
        current_timestamp().alias("created_at"),
    )

    bad_records = records.filter(col("raw_record").isNull()).select(
        col("source_api"),
        col("ingestion_timestamp"),
        col("batch_number"),
        col("api_endpoint"),
        col("raw_data"),
        lit("failed_json_parse").alias("error_reason"),
        current_timestamp().alias("created_at"),
    )

    cleaned_df = cleaned_df.fillna({"patient_sex": "unknown", "medicinal_product": "unknown", "reaction": "unknown"})
    cleaned_df = cleaned_df.dropDuplicates(["report_id"])

    raw_df = parsed.select(
        col("source_api"),
        col("ingestion_timestamp"),
        col("batch_number"),
        col("api_endpoint"),
        col("raw_data"),
        current_timestamp().alias("created_at"),
    )

    raw_df.write.mode("append").partitionBy("batch_number").parquet(raw_path)
    cleaned_df.write.mode("append").partitionBy("batch_number").parquet(processed_path)
    if bad_records.take(1):
        bad_records.write.mode("append").parquet(bad_path)

    LOGGER.info("Batch %s persisted to HDFS", batch_id)


def run_stream() -> None:
    configure_logging()
    spark = build_spark_session(
        os.getenv("SPARK_APP_NAME", "healthcare-phase2-cleaning"),
        extra_conf={
            "spark.sql.streaming.schemaInference": "false",
        },
    )

    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic = os.getenv("KAFKA_TOPIC", "healthcare_raw")
    raw_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_RAW_PATH', '/healthcare/raw')}/events"
    processed_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_PROCESSED_PATH', '/healthcare/processed')}/cleaned_parquet"
    bad_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_PROCESSED_PATH', '/healthcare/processed')}/bad_records"
    checkpoint_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_CHECKPOINT_PATH', '/healthcare/checkpoints')}/phase2_cleaning_stream"

    stream_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", kafka_servers)
        .option("subscribe", kafka_topic)
        .option("startingOffsets", os.getenv("KAFKA_STARTING_OFFSETS", "earliest"))
        .load()
    )

    selected_df = stream_df.selectExpr("CAST(value AS STRING) AS value")

    query = (
        selected_df.writeStream.outputMode("append")
        .option("checkpointLocation", checkpoint_path)
        .foreachBatch(lambda batch_df, batch_id: clean_batch(batch_df, batch_id, processed_path, raw_path, bad_path))
        .start()
    )

    LOGGER.info("Phase 2 cleaning stream started")
    query.awaitTermination()


if __name__ == "__main__":
    run_stream()
