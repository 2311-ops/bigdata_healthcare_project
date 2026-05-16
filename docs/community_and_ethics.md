# Community Contribution and Ethical Considerations

## Open-Source Contribution

This project is released as open-source software for educational and research purposes. The full codebase — including the Docker Compose orchestration, Python producer, Spark Structured Streaming cleaner, Spark MLlib pipeline, and Metabase setup — is available on GitHub under an open educational licence.

### What Others Can Build On

The project is designed as a **reusable big-data pipeline template** for healthcare and life-sciences data engineering:

1. **Adapter for other openFDA datasets** — The producer and schema files can be adapted to ingest openFDA Device Adverse Events, Drug Labeling, or Drug Recall Enforcement datasets with minimal changes to the schema definition in `phase2_cleaning_stream.py`.

2. **Reference implementation** — The combination of Kafka + HDFS + Spark Structured Streaming + MLlib in a single `docker-compose.yml` is a reference implementation that students and researchers can use to learn production-style big-data engineering without cloud infrastructure.

3. **Pipeline template for other domains** — The bronze-silver-gold data lakehouse pattern, foreachBatch micro-batch processing, and MLlib Pipeline API are domain-agnostic. Teams working on financial, IoT, or social media analytics can fork the repository and replace only the producer and schema files.

### Documentation Contributions

All architecture decisions, technology justifications, data lifecycle steps, and ML methodology are documented in the `docs/` directory in Markdown format. This lowers the barrier to understanding and extending the platform.

---

## Ethical Considerations

### 1. Patient Privacy

The openFDA adverse-event data does not contain direct patient identifiers (no names, dates of birth, or addresses). However, the combination of age, sex, weight, specific drug, and reaction could in rare cases enable re-identification of individuals in small communities or with unusual drug combinations. The platform is designed exclusively for **aggregate, population-level analytics**. Any deployment against identifiable health data must:

- Obtain Institutional Review Board (IRB) approval
- Apply appropriate de-identification under the HIPAA Safe Harbor or Expert Determination method
- Restrict data access to authorised personnel via HDFS role-based access control and PostgreSQL row-level security

### 2. Clinical Decision-Support Disclaimer

The risk labels and ML predictions produced by this platform are derived from **spontaneous self-reported adverse-event data**, not from validated clinical outcomes. The `risk_label` field is a proxy variable (1 = the reporter marked the event as serious) and is subject to reporting bias, under-reporting, and duplicate submissions. The model's prediction should **not** be used for:

- Individual patient risk scoring in a clinical setting
- Regulatory pharmacovigilance signal detection without expert pharmacoepidemiology review
- Any decision that could affect patient care without IRB approval and clinical validation

### 3. Algorithmic Fairness

The training data may reflect systemic reporting biases in the MedWatch system (e.g., certain demographics may be over- or under-represented in spontaneous reports). The `risk_summary` reporting layer breaks down predictions by patient sex and medicinal product, enabling analysts to detect disparate prediction rates across demographic groups. Future work should include a formal fairness audit using metrics such as equalised odds across demographic subgroups.

### 4. Data Retention and Right to Erasure

The platform stores records indefinitely in HDFS and PostgreSQL until the Docker volumes are deleted. A production deployment handling any personally identifiable information must implement:

- Configurable data retention policies (e.g., HDFS TTL via quotas)
- A deletion audit trail for GDPR Article 17 (right to erasure) compliance
- Encrypted volumes for data at rest

### 5. Environmental Impact

Running Apache Spark, Kafka, Hadoop, and PostgreSQL simultaneously on a local machine consumes significant CPU and memory resources. For long-running deployments, consider setting Spark executor memory limits and running on energy-efficient hardware or renewable-powered cloud infrastructure.

---

## Suggested Community Activities

- **Share the repository** on academic platforms (ResearchGate, Zenodo) with a DOI for citability.
- **Write a tutorial post** walking through the setup and pipeline execution for students who are new to big-data engineering.
- **Submit a pull request** to the Apache Spark documentation linking to this project as a healthcare use-case example.
- **Collaborate with public health researchers** who need a ready-made pipeline for openFDA signal detection, offering the platform as a starting point for their analysis.
