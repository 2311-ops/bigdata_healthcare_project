"""Reporting layer that aggregates risk analytics for PostgreSQL and Metabase."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, current_date, lit, sum as spark_sum, avg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.spark_utils import build_spark_session, write_dataframe_to_postgres  # noqa: E402

LOGGER = logging.getLogger("phase4_reporting")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_summary_tables(spark, predictions_path: str, reporting_path: str) -> None:
    predictions = spark.read.parquet(predictions_path)

    base = predictions.withColumn("summary_date", current_date())

    overall = (
        base.groupBy("summary_date")
        .agg(
            count("*").alias("total_records"),
            spark_sum(col("risk_label")).alias("high_risk_records"),
            (count("*") - spark_sum(col("risk_label"))).alias("low_risk_records"),
            avg("prediction_probability").alias("average_probability"),
        )
        .withColumn("dimension_type", lit("overall"))
        .withColumn("dimension_value", lit("all_records"))
    )

    by_sex = (
        base.groupBy("summary_date", "patient_sex")
        .agg(
            count("*").alias("total_records"),
            spark_sum(col("risk_label")).alias("high_risk_records"),
            (count("*") - spark_sum(col("risk_label"))).alias("low_risk_records"),
            avg("prediction_probability").alias("average_probability"),
        )
        .withColumn("dimension_type", lit("patient_sex"))
        .withColumnRenamed("patient_sex", "dimension_value")
    )

    by_product = (
        base.groupBy("summary_date", "medicinal_product")
        .agg(
            count("*").alias("total_records"),
            spark_sum(col("risk_label")).alias("high_risk_records"),
            (count("*") - spark_sum(col("risk_label"))).alias("low_risk_records"),
            avg("prediction_probability").alias("average_probability"),
        )
        .withColumn("dimension_type", lit("medicinal_product"))
        .withColumnRenamed("medicinal_product", "dimension_value")
    )

    summary = overall.unionByName(by_sex.select(overall.columns)).unionByName(by_product.select(overall.columns))
    summary = summary.select(
        "summary_date",
        "dimension_type",
        "dimension_value",
        "total_records",
        "high_risk_records",
        "low_risk_records",
        "average_probability",
    )

    summary.write.mode("overwrite").parquet(reporting_path)
    write_dataframe_to_postgres(
        summary,
        "risk_summary",
        mode="overwrite",
        extra_options={"truncate": "true"},
    )
    LOGGER.info("Reporting tables stored in HDFS and PostgreSQL")


def main() -> None:
    configure_logging()
    spark = build_spark_session(os.getenv("SPARK_APP_NAME", "healthcare-phase4-reporting"))
    predictions_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_MODELS_PATH', '/healthcare/models')}/predictions/latest"
    reporting_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_REPORTING_PATH', '/healthcare/reporting')}/risk_summary"
    build_summary_tables(spark, predictions_path, reporting_path)
    spark.stop()


if __name__ == "__main__":
    main()
