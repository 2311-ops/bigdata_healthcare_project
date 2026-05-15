# Technical Documentation

## Producer

The producer continuously queries the openFDA `drug/event` endpoint using pagination. Every raw record is wrapped with:

- `source_api`
- `ingestion_timestamp`
- `batch_number`
- `api_endpoint`
- `raw_data`

The producer uses retries, exponential backoff, and rate-limit-aware sleeping to reduce API pressure.

## Streaming cleaning

Spark Structured Streaming reads Kafka JSON envelopes and:

- parses the raw JSON string
- extracts nested `patient`, `reaction`, and `drug` fields
- converts serious flags into booleans
- derives `risk_label`
- deduplicates on `report_id`
- writes raw, processed, and bad records to HDFS

## ML layer

The ML job automatically detects numeric and categorical columns, then:

- imputes numeric values
- indexes and one-hot encodes categorical values
- assembles features
- trains Logistic Regression and Random Forest models
- evaluates accuracy, precision, recall, and F1
- saves the best model and predictions

## Reporting layer

The reporting job joins model outputs into aggregated analytics tables that Metabase can query directly:

- overall risk counts
- risk by sex
- risk by medicinal product

## Storage model

PostgreSQL tables:

- `cleaned_patients`
- `patient_predictions`
- `model_evaluation`
- `risk_summary`
