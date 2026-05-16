# Project Plan — Healthcare Big Data Analytics Platform

## Project Overview

**Project Title:** Real-Time Healthcare Adverse-Event Analytics Platform  
**Course:** CSCI461 — Introduction to Big Data, Spring 2026  
**Dataset:** openFDA Drug Adverse Event API  
**Stack:** Kafka · HDFS · Spark Streaming · Spark MLlib · PostgreSQL · Metabase  

---

## Project Timeline (Gantt Overview)

| Phase | Milestone | Duration | Deliverable |
|-------|-----------|----------|-------------|
| **Phase 1** | Project idea, dataset selection, objective definition | Week 1–2 | Phase 1 submission + paper Introduction |
| **Phase 2** | System design, Docker compose, data lifecycle design | Week 3–5 | Architecture docs + paper Methodology outline |
| **Phase 2** | Infrastructure setup (Kafka, HDFS, Spark, PostgreSQL) | Week 4–5 | `docker-compose.yml` fully operational |
| **Phase 2** | Producer service (openFDA → Kafka ingestion) | Week 5 | `producer/api_healthcare_producer.py` |
| **Phase 3** | Spark Structured Streaming cleaner (Phase 2 job) | Week 6–7 | `spark_jobs/phase2_cleaning_stream.py` |
| **Phase 3** | ML pipeline — feature engineering + model training | Week 7–8 | `spark_jobs/phase3_ml_pipeline.py` |
| **Phase 3** | Reporting layer + Metabase dashboards | Week 8–9 | `spark_jobs/phase4_reporting.py` |
| **Phase 3** | Full pipeline integration test | Week 9 | `scripts/run_full_pipeline.sh` validated |
| **Phase 3** | Final paper (Results + Discussion) | Week 9–10 | IEEE paper complete |

---

## Resource Allocation

### Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU cores | 4 | 8 |
| Disk space | 20 GB free | 30 GB free |
| OS | Linux / macOS / Windows (WSL2) | Linux / macOS |

All compute runs locally via Docker Desktop or Docker Engine — no cloud infrastructure or budget is required.

### Software (all open-source / free)

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Engine | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-service orchestration |
| Apache Kafka | 7.7.8 (Confluent) | Message streaming |
| Apache Hadoop (HDFS) | 3.2.1 | Distributed storage |
| Apache Spark | 3.3.0 | Batch + streaming processing |
| PostgreSQL | 15 | Data warehouse |
| Metabase | 0.50.19 | Dashboard / BI layer |
| Python | 3.11 | Producer + utility scripts |
| PySpark | 3.3.0 | Spark Python API |

### Personnel

| Role | Effort |
|------|--------|
| Data Engineer | Pipeline design, Kafka producer, Spark jobs |
| ML Engineer | Feature engineering, model training, evaluation |
| DevOps | Docker Compose orchestration, startup scripts |
| Analyst | Metabase dashboard setup, result interpretation |

> For a student project, all roles are fulfilled by the project team.

---

## Risk Assessment and Mitigation

| # | Risk | Likelihood | Impact | Mitigation Strategy |
|---|------|-----------|--------|---------------------|
| 1 | **openFDA API rate limiting** — API returns HTTP 429 | High | Medium | Producer respects Retry-After headers; configurable sleep between pages (`OPENFDA_SLEEP_SECONDS`); exponential backoff on failures |
| 2 | **Docker memory exhaustion** — Spark OOM on machines with < 8 GB RAM | Medium | High | Spark driver/executor memory configurable via env vars; `SPARK_SHUFFLE_PARTITIONS=4` limits shuffle memory; Metabase runs on separate heap |
| 3 | **HDFS namenode startup delay** — namenode takes > 60 s on first boot | Medium | Low | `start_all_services.sh` polls `hdfs dfs -ls /` with 300-second timeout before proceeding |
| 4 | **Kafka topic not created** — auto-create disabled in compose | Low | High | `create_kafka_topic.sh` runs idempotently on every startup; `--if-not-exists` flag prevents errors |
| 5 | **openFDA API structural changes** — nested field paths change | Low | High | Schema defined in `openfda_record_schema()` in `phase2_cleaning_stream.py`; bad-records partition captures failures for review |
| 6 | **Model training fails — no data** — ML job runs before enough records are cleaned | Medium | Medium | `run_full_pipeline.sh` waits `PIPELINE_WARMUP_SECONDS` (default 180) before triggering Phase 3 |
| 7 | **PostgreSQL connection refused** — Spark JDBC write fails | Low | Medium | `wait_for_postgres()` in `postgres_utils.py` retries for up to 120 seconds; compose health check gate |
| 8 | **Data privacy breach** — sensitive data in logs | Low | High | Producer does not log raw record content at INFO level; `.env` excluded from version control via `.gitignore` |
| 9 | **Port conflicts on host** — port 3000 (Metabase) already in use | Low | Low | Metabase port configurable in `.env` (`METABASE_PORT`); only port exposed to host |
| 10 | **ML class imbalance** — most records may be serious | Medium | Medium | Weighted F1 metric used (not accuracy); Random Forest uses bootstrap sampling; risk_label distribution checked in exploration |
