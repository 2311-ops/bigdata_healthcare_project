# Rubric Gap Analysis

Source rubric: `ProjectRubricBigDataSpring 2026.pdf`

This checklist compares the rubric requirements against the current healthcare big data project.

## Overall Status

The project satisfies most of the required big data pipeline work:

- Clear healthcare analytics idea
- Public dataset from openFDA
- Dockerized big data architecture
- Kafka ingestion
- HDFS storage
- Spark preprocessing
- PostgreSQL reporting layer
- Metabase visualizations
- CSV outputs
- Documentation and ethical discussion

The main items still needing attention before submission are:

- Make the final paper fully IEEE-style.
- Add screenshots of charts and system output.
- Make documentation consistent with the actual Phase 3 implementation.
- Add a clear timeline/Gantt figure.
- Add a stronger "methodology" explanation for the rule-based scorer.

---

## Phase 1: Project Idea, Objective, and Dataset

### What We Did Correctly

- Project idea is clear: a healthcare adverse-event analytics platform.
- The project has real-world relevance because adverse-event monitoring is important for public health and pharmacovigilance.
- The project uses big data tools instead of only simple scripts.
- Dataset is relevant and legally accessible: openFDA Drug Event API.
- The project scope is clear: ingest, process, score, store, visualize, and export healthcare records.

### Evidence in the Project

- `README.md`
- `docs/project_plan.md`
- `docs/architecture.md`
- `producer/api_healthcare_producer.py`
- `.env`

### What Still Needs Work

- In the paper introduction, state SMART objectives more explicitly.
- Add measurable success criteria, for example:
  - Successfully ingest thousands of openFDA records.
  - Store raw and cleaned data in HDFS.
  - Generate PostgreSQL tables for visualization.
  - Export final CSV outputs.

---

## Phase 2: Project Planning, Design, Data Lifecycle, and Paper Part 1

### What We Did Correctly

- Project planning exists in `docs/project_plan.md`.
- Architecture is documented in `docs/architecture.md`.
- Docker Compose design includes Kafka, HDFS, Spark, PostgreSQL, and Metabase.
- The data lifecycle is implemented end-to-end:
  - openFDA API acquisition
  - Kafka streaming
  - HDFS raw storage
  - Spark cleaning
  - PostgreSQL storage
  - Metabase visualization
  - CSV export
- Risk assessment exists in the project plan.
- Resource allocation is documented.

### Evidence in the Project

- `docker-compose.yml`
- `docs/project_plan.md`
- `docs/architecture.md`
- `docs/setup_guide.md`
- `scripts/start_all_services.sh`
- `scripts/run_full_pipeline.sh`

### What Still Needs Work

- Add an actual diagram or screenshot of the architecture to the PowerPoint.
- Add a Gantt chart image or table to the paper/slides.
- In the paper, clearly justify why each technology was chosen:
  - Kafka for buffering and replay
  - HDFS for distributed storage
  - Spark for scalable processing
  - PostgreSQL for analytical queries
  - Metabase for dashboards
- Mention data security more clearly:
  - openFDA is public data
  - no direct patient identifiers
  - production systems would require access control, encryption, and HIPAA review

---

## Phase 3: Data Preprocessing, Methodology, Community Contribution, and Paper Part 2

### What We Did Correctly

- Spark preprocessing is implemented.
- Missing text fields are handled using `"unknown"`.
- Negative age and weight values are nullified.
- Raw nested JSON is parsed into structured columns.
- Records are deduplicated by `report_id`.
- A risk label is derived from seriousness indicators.
- Prediction output is generated and stored.
- Model evaluation table is generated.
- Community and ethical considerations are documented.
- Visualizations were created in Metabase.
- CSV files were exported to `outputs/`.

### Evidence in the Project

- `spark_jobs/phase2_cleaning_stream.py`
- `spark_jobs/phase3_ml_pipeline.py`
- `spark_jobs/phase4_reporting.py`
- `docs/community_and_ethics.md`
- `outputs/cleaned_patients.csv`
- `outputs/patient_predictions.csv`
- `outputs/model_evaluation.csv`
- `outputs/risk_summary.csv`

### What Still Needs Work

- Important: update any paper or slide text that says the final working model is Logistic Regression or Random Forest.
- The current working Phase 3 implementation is a rule-based risk scorer, not a trained MLlib model.
- In the methodology section, explain that:
  - `risk_label` is derived from serious/death/hospitalization flags.
  - `prediction` follows the derived risk label.
  - `prediction_probability` is set to 0.95 for high risk and 0.05 for low risk.
  - This approach was used because the Spark container lacked the `numpy` dependency needed by Spark MLlib.
- Add screenshots of:
  - Metabase dashboard
  - PostgreSQL query output
  - HDFS folder output
  - CSV files in the `outputs` folder
- Add a short results interpretation for each major chart.

---

## Paper Requirements

### What We Did Correctly

- There is already documentation for:
  - Introduction
  - Architecture
  - Methodology
  - Data lifecycle
  - Ethics and community impact
  - Visualization queries
- There is a Word document:
  - `docs/IEEE_Paper_Healthcare_Analytics.docx`

### What Still Needs Work

- Verify that the Word paper is in IEEE format.
- Add final screenshots and chart images.
- Replace any outdated MLlib claims with the actual working scorer.
- Add a clear "Results and Discussion" section.
- Add references:
  - openFDA API documentation
  - Apache Kafka
  - Apache Hadoop/HDFS
  - Apache Spark
  - PostgreSQL
  - Metabase
- Add a limitations section.

---

## PowerPoint Requirements

### What We Did Correctly

- You have working charts in Metabase.
- You have final PostgreSQL tables.
- You have CSV outputs.
- You have architecture and methodology documentation.

### What Still Needs Work

- Export or screenshot charts as PNG.
- Add architecture diagram.
- Add pipeline phase diagram.
- Add result screenshots.
- Add short explanation of each visualization.
- Add a final slide for limitations and future work.

Suggested slide order:

1. Title
2. Problem statement
3. Objectives
4. Dataset
5. Architecture
6. Data lifecycle
7. Preprocessing
8. Risk scoring methodology
9. Database outputs
10. Dashboard visualizations
11. Results and insights
12. Community and ethics
13. Limitations
14. Future work
15. Conclusion

---

## Final To-Do List Before Submission

1. Take PNG screenshots of all charts.
2. Put screenshots into the PowerPoint.
3. Add architecture and data lifecycle diagrams.
4. Update paper methodology to match the working Phase 3 scorer.
5. Add CSV output evidence from the `outputs` folder.
6. Add PostgreSQL query output screenshots.
7. Add HDFS output screenshot.
8. Add references.
9. Add limitations and future work.
10. Review all documents for outdated "Random Forest / Logistic Regression" statements.

