# Architecture

The platform follows a bronze-silver-gold style flow tailored for healthcare adverse-event analytics:

1. The producer service fetches records from the openFDA drug event API.
2. Each record is wrapped with ingestion metadata and pushed into Kafka topic `healthcare_raw`.
3. Spark Structured Streaming consumes Kafka, archives the raw stream into HDFS, cleans nested JSON payloads, and writes curated parquet data to HDFS.
4. Spark MLlib reads the cleaned parquet data, engineers features, trains Logistic Regression and Random Forest models, and writes predictions and metrics.
5. Spark writes analytical tables into PostgreSQL `healthcare_dw`.
6. Metabase connects directly to PostgreSQL for dashboards and business exploration.

## Data Zones

- `hdfs:///healthcare/raw` stores raw envelopes from Kafka.
- `hdfs:///healthcare/processed` stores cleaned parquet and bad records.
- `hdfs:///healthcare/models` stores trained model artifacts and predictions.
- `hdfs:///healthcare/reporting` stores aggregated reporting outputs.

## Why this design works

- Kafka absorbs bursts from the public API.
- HDFS acts as the low-cost durable landing zone.
- Spark Structured Streaming keeps ingestion near real time.
- Spark MLlib provides reproducible model training without leaving the cluster.
- PostgreSQL gives Metabase a reliable star-schema-like reporting source.
