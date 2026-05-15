"""Spark MLlib pipeline for healthcare adverse-event risk prediction."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence, Tuple

from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import Imputer, OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, struct
from pyspark.sql.types import (
    BooleanType,
    ByteType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    ShortType,
    StringType,
    TimestampType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.spark_utils import build_spark_session, write_dataframe_to_postgres  # noqa: E402

LOGGER = logging.getLogger("phase3_ml_pipeline")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_cleaned_data(spark: SparkSession, cleaned_path: str) -> DataFrame:
    return spark.read.parquet(cleaned_path)


def numeric_columns(df: DataFrame, exclude: Sequence[str]) -> List[str]:
    numeric_types = (ByteType, ShortType, IntegerType, LongType, FloatType, DoubleType, DecimalType)
    return [
        field.name
        for field in df.schema.fields
        if isinstance(field.dataType, numeric_types) and field.name not in exclude
    ]


def categorical_columns(df: DataFrame, exclude: Sequence[str]) -> List[str]:
    categorical_types = (StringType, BooleanType, DateType, TimestampType)
    return [
        field.name
        for field in df.schema.fields
        if isinstance(field.dataType, categorical_types) and field.name not in exclude
    ]


def prepare_base_frame(df: DataFrame) -> DataFrame:
    prepared = (
        df.withColumn("risk_label", col("risk_label").cast("int"))
        .withColumn("patient_age", col("patient_age").cast("double"))
        .withColumn("patient_weight", col("patient_weight").cast("double"))
        .fillna({"patient_sex": "unknown", "medicinal_product": "unknown", "reaction": "unknown"})
    )
    return prepared


def build_feature_stages(df: DataFrame, label_col: str = "risk_label") -> Tuple[List, List[str], List[str]]:
    excluded = {
        "id",
        label_col,
        "report_id",
        "source_api",
        "ingestion_timestamp",
        "batch_number",
        "api_endpoint",
        "raw_record",
        "created_at",
        "scoring_timestamp",
    }
    numeric_cols = numeric_columns(df, excluded)
    categorical_cols = categorical_columns(df, excluded)

    stages = []

    if numeric_cols:
        imputed_numeric_cols = [f"{col_name}_imputed" for col_name in numeric_cols]
        imputer = Imputer(inputCols=numeric_cols, outputCols=imputed_numeric_cols, strategy="median")
        stages.append(imputer)
    else:
        imputed_numeric_cols = []

    encoded_cols = []
    for column_name in categorical_cols:
        index_col = f"{column_name}_index"
        encoded_col = f"{column_name}_encoded"
        indexer = StringIndexer(
            inputCol=column_name,
            outputCol=index_col,
            handleInvalid="keep",
        )
        encoder = OneHotEncoder(inputCols=[index_col], outputCols=[encoded_col], handleInvalid="keep")
        stages.extend([indexer, encoder])
        encoded_cols.append(encoded_col)

    feature_cols = imputed_numeric_cols + encoded_cols
    assembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol="features",
        handleInvalid="keep",
    )
    stages.append(assembler)

    return stages, numeric_cols, categorical_cols


def evaluate_predictions(predictions: DataFrame, label_col: str = "risk_label") -> dict:
    evaluators = {
        "accuracy": MulticlassClassificationEvaluator(labelCol=label_col, predictionCol="prediction", metricName="accuracy"),
        "precision": MulticlassClassificationEvaluator(labelCol=label_col, predictionCol="prediction", metricName="weightedPrecision"),
        "recall": MulticlassClassificationEvaluator(labelCol=label_col, predictionCol="prediction", metricName="weightedRecall"),
        "f1_score": MulticlassClassificationEvaluator(labelCol=label_col, predictionCol="prediction", metricName="f1"),
    }
    return {name: float(evaluator.evaluate(predictions)) for name, evaluator in evaluators.items()}


def model_predictions_frame(predictions: DataFrame, model_name: str, model_version: str) -> DataFrame:
    return predictions.select(
        col("report_id"),
        col("source_api"),
        col("receipt_date"),
        col("patient_sex"),
        col("medicinal_product"),
        lit(model_name).alias("model_name"),
        lit(model_version).alias("model_version"),
        col("risk_label"),
        col("prediction").cast("int").alias("prediction"),
        col("probability").getItem(1).cast("double").alias("prediction_probability"),
        current_timestamp().alias("scoring_timestamp"),
        col("features").cast("string").alias("features"),
        current_timestamp().alias("created_at"),
    )

def train_models(spark: SparkSession, df: DataFrame) -> None:
    cleaned = prepare_base_frame(df)
    feature_stages, numeric_cols, categorical_cols = build_feature_stages(cleaned)

    train_df, test_df = cleaned.randomSplit([0.8, 0.2], seed=42)

    lr = LogisticRegression(featuresCol="features", labelCol="risk_label", maxIter=int(os.getenv("LR_MAX_ITER", "20")))
    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol="risk_label",
        numTrees=int(os.getenv("RF_NUM_TREES", "100")),
        maxDepth=int(os.getenv("RF_MAX_DEPTH", "8")),
        seed=42,
    )

    model_specs = [
        ("logistic_regression", Pipeline(stages=feature_stages + [lr])),
        ("random_forest", Pipeline(stages=feature_stages + [rf])),
    ]

    evaluator = MulticlassClassificationEvaluator(labelCol="risk_label", predictionCol="prediction", metricName="f1")
    best_model_name = None
    best_model_version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    best_model = None
    best_predictions = None
    best_score = -1.0
    metric_rows: List[Tuple[str, str, str, float, str]] = []

    for model_name, pipeline_model in model_specs:
        fitted = pipeline_model.fit(train_df)
        predictions = fitted.transform(test_df).cache()
        metrics = evaluate_predictions(predictions)

        for metric_name, metric_value in metrics.items():
            metric_rows.append((model_name, best_model_version, metric_name, metric_value, "test"))

        score = metrics["f1_score"]
        LOGGER.info("%s F1 score: %s", model_name, score)
        if score > best_score:
            best_score = score
            best_model_name = model_name
            best_model = fitted
            best_predictions = predictions

    if best_model is None or best_predictions is None or best_model_name is None:
        raise RuntimeError("No model was trained successfully")

    model_root = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_MODELS_PATH', '/healthcare/models')}"
    best_model_path = f"{model_root}/best_model"
    best_model.write().overwrite().save(best_model_path)
    LOGGER.info("Saved best model to %s", best_model_path)

    predictions_with_metadata = model_predictions_frame(best_predictions, best_model_name, best_model_version)
    predictions_output_path = f"{model_root}/predictions/latest"
    predictions_with_metadata.write.mode("overwrite").parquet(predictions_output_path)

    cleaned_output = cleaned.select(
        "report_id",
        "source_api",
        "ingestion_timestamp",
        "batch_number",
        "api_endpoint",
        "receipt_date",
        "patient_age",
        "patient_weight",
        "patient_sex",
        "medicinal_product",
        "reaction",
        "serious",
        "seriousness_death",
        "seriousness_hospitalization",
        "risk_label",
        "raw_record",
    )

    write_dataframe_to_postgres(cleaned_output, "cleaned_patients", mode="append")
    write_dataframe_to_postgres(predictions_with_metadata, "patient_predictions", mode="append")
    metrics_df = spark.createDataFrame(
        metric_rows,
        ["model_name", "model_version", "metric_name", "metric_value", "split_name"],
    )
    write_dataframe_to_postgres(metrics_df, "model_evaluation", mode="append")

    full_predictions = best_model.transform(cleaned).select(
        "report_id",
        "source_api",
        "risk_label",
        col("prediction").cast("int").alias("prediction"),
        col("probability").getItem(1).cast("double").alias("prediction_probability"),
    )
    full_predictions.write.mode("overwrite").parquet(f"{model_root}/predictions/full_latest")


def main() -> None:
    configure_logging()
    spark = build_spark_session(
        os.getenv("SPARK_APP_NAME", "healthcare-phase3-ml"),
        extra_conf={
            "spark.jars.packages": os.getenv("SPARK_JARS_PACKAGES", "org.postgresql:postgresql:42.7.3"),
        },
    )
    cleaned_path = f"{os.getenv('HDFS_URI', 'hdfs://namenode:8020')}{os.getenv('HDFS_PROCESSED_PATH', '/healthcare/processed')}/cleaned_parquet"
    df = load_cleaned_data(spark, cleaned_path)
    train_models(spark, df)
    spark.stop()


if __name__ == "__main__":
    main()
