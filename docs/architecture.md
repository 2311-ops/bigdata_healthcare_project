# Architecture

## System Overview

The platform follows a **bronze-silver-gold data lakehouse pattern** adapted for healthcare adverse-event analytics. Every layer is containerised and orchestrated via a single `docker-compose.yml`.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Healthcare Analytics Pipeline                     │
│                                                                          │
│  ┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌────────────────┐  │
│  │  openFDA    │───▶│  Kafka   │───▶│   HDFS   │───▶│  Spark Stream  │  │
│  │  REST API   │    │  Topic   │    │  (Bronze)│    │  (Silver)      │  │
│  └─────────────┘    └──────────┘    └──────────┘    └───────┬────────┘  │
│                                                             │            │
│                                                     ┌───────▼────────┐  │
│                                                     │  Spark MLlib   │  │
│                                                     │  (Gold / ML)   │  │
│                                                     └───────┬────────┘  │
│                                                             │            │
│                                          ┌──────────────────▼──────┐   │
│                                          │  PostgreSQL (Reporting)  │   │
│                                          └──────────────┬──────────┘   │
│                                                         │               │
│                                                  ┌──────▼──────┐       │
│                                                  │  Metabase   │       │
│                                                  │  Dashboards │       │
│                                                  └─────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Description

### Layer 1 — Data Ingestion (Producer → Kafka)

The Python producer (`producer/api_healthcare_producer.py`) continuously queries the openFDA Drug Adverse Event REST API. Each raw JSON record is wrapped in a metadata envelope containing:

- `source_api` — identifies the data origin
- `ingestion_timestamp` — ISO-8601 UTC timestamp of fetch
- `batch_number` — monotonically increasing cycle counter
- `api_endpoint` — full URL for auditability
- `raw_data` — original record serialised as a JSON string

The envelope is published to the `healthcare_raw` Kafka topic using gzip compression and `acks=all` for durability.

### Layer 2 — Message Buffer (Kafka)

Kafka decouples ingestion speed from processing speed. The topic is configured with:

- 1 partition (scalable to N by changing `KAFKA_TOPIC_PARTITIONS`)
- Replication factor 1 (suitable for single-broker dev; set to 3 for production)
- `auto.create.topics.enable=false` — topic must be explicitly created via `create_kafka_topic.sh`

### Layer 3 — Bronze Storage + Silver Cleaning (HDFS + Spark Streaming)

Spark Structured Streaming (`spark_jobs/phase2_cleaning_stream.py`) processes Kafka in micro-batches using `foreachBatch`. Each batch:

1. Archives the raw envelope to `hdfs:///healthcare/raw/events` (Bronze layer)
2. Parses nested JSON fields using a typed Spark schema
3. Cleans, normalises, and deduplicates records
4. Writes cleaned Parquet to `hdfs:///healthcare/processed/cleaned_parquet` (Silver layer)
5. Routes bad records to `hdfs:///healthcare/processed/bad_records`

### Layer 4 — Machine Learning (Spark MLlib)

The ML batch job (`spark_jobs/phase3_ml_pipeline.py`) reads the Silver layer and:

1. Imputes missing numeric values (median strategy)
2. Indexes and one-hot encodes categorical columns
3. Trains Logistic Regression and Random Forest classifiers
4. Evaluates on a held-out 20% test split
5. Saves the best model to `hdfs:///healthcare/models/best_model`
6. Writes predictions to `hdfs:///healthcare/models/predictions/latest` and `patient_predictions` table

### Layer 5 — Reporting (PostgreSQL + Metabase)

The reporting job (`spark_jobs/phase4_reporting.py`) aggregates predictions into `risk_summary` by three dimensions: overall, by patient sex, and by medicinal product. Metabase connects directly to PostgreSQL on port 5432 (internal Docker network only).

---

## Data Zones (HDFS)

| HDFS Path | Contents | Layer |
|-----------|----------|-------|
| `/healthcare/raw/events` | Raw Kafka envelopes (Parquet) | Bronze |
| `/healthcare/processed/cleaned_parquet` | Cleaned, deduplicated records | Silver |
| `/healthcare/processed/bad_records` | Unparseable records with error reason | Silver |
| `/healthcare/models/best_model` | Serialised best Spark ML PipelineModel | Gold |
| `/healthcare/models/predictions/latest` | Best-model predictions on test set | Gold |
| `/healthcare/models/predictions/full_latest` | Best-model predictions on full dataset | Gold |
| `/healthcare/reporting/risk_summary` | Aggregated risk summary Parquet | Gold |
| `/healthcare/checkpoints` | Spark Structured Streaming offsets | Internal |

---

## Technology Justification

### Why Apache Kafka (not RabbitMQ or AWS SQS)?

Kafka's **log-based storage model** allows the streaming consumer to replay messages from any offset. This is critical in a data pipeline: if the Spark cleaning job crashes mid-batch, it can resume from the last committed checkpoint offset without any data loss. RabbitMQ deletes messages after acknowledgement, making replay impossible. AWS SQS requires cloud credentials and adds egress cost — incompatible with the self-contained deployment requirement.

### Why Apache Spark (not Apache Flink)?

Spark provides a **unified API** for both Structured Streaming and batch MLlib within the same framework. Flink has excellent streaming capabilities but its ML library is far less mature than Spark MLlib. Using Spark eliminates the need for a second processing engine, reducing operational complexity. Spark's DataFrame API also offers richer data-quality functions (`fillna`, `coalesce`, `dropDuplicates`) than Flink's Table API for ad-hoc cleaning.

### Why HDFS (not AWS S3 or MinIO)?

HDFS keeps the entire stack **self-contained and credential-free**. The `bde2020` Docker images provide a production-equivalent namenode/datanode topology in a single compose file. For a course project running on a local machine, HDFS avoids cloud costs and internet dependencies. A production migration to S3 requires only changing the `fs.defaultFS` configuration.

### Why PostgreSQL (not ClickHouse or Redshift)?

Metabase's native PostgreSQL connector is the most mature and best-supported integration. The reporting data volume (tens of thousands of `risk_summary` rows) does not justify the operational overhead of a dedicated OLAP engine. PostgreSQL handles the required aggregation queries in milliseconds at this scale. A future production deployment could swap PostgreSQL for a managed OLAP store behind the same JDBC interface used by Spark.

---

## Scalability

| Dimension | Current (Dev) | Scale-up Path |
|-----------|--------------|---------------|
| Kafka throughput | 1 partition, 1 broker | Increase `KAFKA_TOPIC_PARTITIONS`; add broker nodes |
| Spark parallelism | 1 worker, 2g executor | Add `spark-worker` services to compose; increase `SPARK_EXECUTOR_MEMORY` |
| HDFS storage | 1 datanode | Duplicate `datanode` service; namenode auto-distributes blocks |
| PostgreSQL | Single node | Replace with managed OLAP (Redshift, BigQuery) behind same JDBC |
| Metabase | Single instance | Horizontal scaling via load balancer (Metabase Enterprise) |

---

## Data Security and Privacy

| Control | Implementation |
|---------|---------------|
| Credential management | All secrets in `.env` file; `.gitignore` must exclude `.env` |
| Network isolation | All services on internal Docker bridge; only Metabase (port 3000) exposed |
| Log sanitisation | Producer does not log raw record content at INFO level |
| HDFS permissions | Disabled for dev (`dfs.permissions.enabled=false`); must be enabled for PHI data |
| Kafka TLS | Not enabled in dev; required for production with identifiable data |
| JDBC encryption | Not enabled in dev; add `ssl=true` to POSTGRES_JDBC_URL for production |
| PHI handling | openFDA data has no direct patient identifiers; HIPAA review required before extending to identifiable datasets |
| Data retention | HDFS volumes persist until `docker compose down -v`; set retention policies for production |

---

## Why this Design Works

- **Kafka absorbs API bursts** — the openFDA API has rate limits; Kafka buffers records so Spark is not tied to API timing.
- **HDFS is the durable landing zone** — raw records are never lost even if downstream jobs fail; replay is always possible.
- **Spark Structured Streaming keeps ingestion near real-time** — micro-batch processing delivers cleaned data within seconds of ingestion.
- **Spark MLlib provides reproducible model training** — the same Pipeline API trains both models without leaving the cluster; no separate ML framework required.
- **PostgreSQL gives Metabase a reliable star-schema-like reporting source** — analysts get self-service dashboards with no SQL knowledge required.
