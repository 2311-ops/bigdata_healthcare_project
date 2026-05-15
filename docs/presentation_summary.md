# Presentation Summary

## Problem

Healthcare adverse-event data arrives continuously and is difficult to analyze in its raw form.

## Solution

This project delivers a Dockerized real-time analytics platform that ingests public openFDA adverse-event records, cleans them with Spark, trains machine learning models, stores governed analytics in PostgreSQL, and visualizes results in Metabase.

## Key Capabilities

- Continuous API ingestion into Kafka
- Durable HDFS storage for bronze, silver, and reporting layers
- Spark Structured Streaming for cleaning and deduplication
- Spark MLlib for classification and evaluation
- PostgreSQL data warehouse for reporting
- Metabase dashboards for self-service analytics

## Business Value

- Faster visibility into high-risk adverse events
- Reusable data engineering and ML pipeline
- Production-style orchestration with Docker Compose
- Clear separation of raw, processed, model, and reporting layers
