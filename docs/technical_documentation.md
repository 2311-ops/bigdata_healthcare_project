# Technical Documentation

## Producer

The producer (`producer/api_healthcare_producer.py`) continuously queries the openFDA `drug/event` endpoint using pagination. Every raw record is wrapped with:

- `source_api` — string identifying the openFDA API
- `ingestion_timestamp` — ISO-8601 UTC timestamp
- `batch_number` — monotonically increasing cycle counter
- `api_endpoint` — full URL for auditability
- `raw_data` — original record as a JSON string

The producer uses retries with exponential backoff (up to 5 attempts), respects HTTP 429 `Retry-After` headers, and configurable sleep between pages (`OPENFDA_SLEEP_SECONDS`) to reduce API pressure.

---

## Phase 2 — Streaming Cleaning

Spark Structured Streaming (`spark_jobs/phase2_cleaning_stream.py`) reads Kafka JSON envelopes and applies the following pipeline in each micro-batch:

### Parsing
- The outer envelope is parsed with `from_json` using the `envelope_schema()` typed struct.
- The nested `raw_data` string is parsed with `from_json` using `openfda_record_schema()`, which defines typed structs for `patient`, `reaction[]`, and `drug[]` arrays.

### Field Extraction
- `patient_age` and `patient_weight` cast to `DoubleType`
- `patient_sex` from `patient.patientsex`, lowercased and trimmed
- `medicinal_product` from `patient.drug[0].medicinalproduct`, lowercased and trimmed
- `reaction` from `patient.reaction[0].reactionmeddrapt`, lowercased and trimmed
- `receipt_date` from `receiptdate` or `receivedate` (fallback), parsed from `yyyyMMdd` format

### Cleaning
- Negative `patient_age` and `patient_weight` values are nullified (physiologically impossible)
- Null string fields are replaced with `"unknown"` via `coalesce` and `fillna`
- `serious`, `seriousness_death`, `seriousness_hospitalization` flags accept `"1"`, `"true"`, `"yes"` (case-insensitive) → `BooleanType`

### Risk Label Derivation
```
risk_label = 1  if (serious OR seriousness_death OR seriousness_hospitalization)
risk_label = 0  otherwise
```

### Deduplication
- `dropDuplicates(["report_id"])` on `safetyreportid`; falls back to `substring(md5(raw_data), 1, 16)` when absent

### Outputs
| Location | Content |
|----------|---------|
| `hdfs:///healthcare/raw/events` | Raw envelopes (Bronze) |
| `hdfs:///healthcare/processed/cleaned_parquet` | Cleaned records (Silver) |
| `hdfs:///healthcare/processed/bad_records` | Records failing JSON parse |

---

## Phase 3 — Machine Learning Pipeline

### Why These Algorithms?

**Logistic Regression** was chosen as the baseline model because:
- It produces **calibrated probability estimates** useful for risk ranking
- It is **interpretable** via feature coefficients — important for healthcare applications
- It converges quickly on **sparse one-hot feature vectors** typical of categorical drug/reaction data
- It serves as a strong baseline to measure the added value of more complex models

**Random Forest** was chosen as the challenger model because:
- It captures **non-linear interactions** between features (e.g., specific drug–reaction–age combinations)
- It is **robust to outliers** in numeric features through bootstrap averaging
- It naturally handles **mild class imbalance** via bootstrap sampling
- It does not require feature scaling, unlike Logistic Regression

### Feature Engineering

| Feature Type | Input Columns | Transformation |
|-------------|--------------|----------------|
| Numeric | `patient_age`, `patient_weight`, `batch_number` | Median imputation → VectorAssembler |
| Categorical | `patient_sex`, `medicinal_product`, `reaction`, `receipt_date` | StringIndexer (handleInvalid=keep) → OneHotEncoder → VectorAssembler |

`handleInvalid='keep'` in StringIndexer assigns a dedicated index to unseen labels at inference time, preventing pipeline failures on new drug names or reaction terms not seen during training.

### Hyperparameters

| Model | Parameter | Value | Rationale |
|-------|-----------|-------|-----------|
| Logistic Regression | `maxIter` | 20 | Sufficient for convergence on sparse OHE features |
| Logistic Regression | `labelCol` | `risk_label` | Binary target |
| Random Forest | `numTrees` | 100 | Reduces variance sufficiently; beyond 100 offers diminishing returns |
| Random Forest | `maxDepth` | 8 | Limits overfitting on a small dataset; captures 2–3 feature interactions |
| Random Forest | `seed` | 42 | Reproducibility |
| Train/test split | `seed` | 42 | Reproducibility |
| Train fraction | — | 0.80 | Standard 80/20 split |

### Evaluation Metrics

All four metrics are computed using `MulticlassClassificationEvaluator` with weighted averaging:

| Metric | Formula | Why Used |
|--------|---------|----------|
| Accuracy | (TP + TN) / N | Overall correctness |
| Weighted Precision | Σ(precision_i × support_i) / N | Penalises false positives |
| Weighted Recall | Σ(recall_i × support_i) / N | Penalises false negatives (missed serious events) |
| **Weighted F1** | Harmonic mean of precision & recall | **Primary selection metric** — balances both |

F1 is the primary selection criterion because in a healthcare risk-detection context, both false positives (unnecessary alerts) and false negatives (missed serious events) carry real costs.

### Model Results

| Metric | Logistic Regression | Random Forest |
|--------|-------------------|---------------|
| Accuracy | ~0.84 | ~0.87 |
| Weighted Precision | ~0.83 | ~0.86 |
| Weighted Recall | ~0.84 | ~0.87 |
| Weighted F1 | ~0.83 | **~0.86** |

Random Forest is selected as the best model and saved to `hdfs:///healthcare/models/best_model`.

> Note: Exact values vary by ingestion run due to API data variation. Values above are representative of a 2,000-record test run.

---

## Phase 4 — Reporting Layer

The reporting job reads model predictions and produces `risk_summary` aggregations:

| Dimension | Description |
|-----------|-------------|
| `overall` | Total, high-risk, low-risk counts + avg probability across all records |
| `patient_sex` | Same metrics broken down by patient sex |
| `medicinal_product` | Same metrics broken down by medicinal product name |

Results are written to both `hdfs:///healthcare/reporting/risk_summary` (Parquet) and the `risk_summary` PostgreSQL table for Metabase.

---

## Storage Model

### HDFS Data Zones

| Zone | Path | Contents |
|------|------|---------|
| Bronze | `/healthcare/raw` | Raw API envelopes |
| Silver | `/healthcare/processed` | Cleaned Parquet + bad records |
| Gold (ML) | `/healthcare/models` | Trained model artifacts + predictions |
| Gold (Reporting) | `/healthcare/reporting` | Aggregated analytics tables |
| Internal | `/healthcare/checkpoints` | Spark Structured Streaming offsets |

### PostgreSQL Tables

| Table | Contents |
|-------|---------|
| `cleaned_patients` | Cleaned patient records from Spark streaming |
| `patient_predictions` | Per-record ML model predictions |
| `model_evaluation` | Accuracy, precision, recall, F1 per model per run |
| `risk_summary` | Aggregated risk counts by date, sex, and medicinal product |

---

## Data Quality

- **Bad record rate:** ~3–5% of raw records fail JSON parsing (routed to `bad_records`)
- **Null patient age:** ~12% of valid records
- **Null patient weight:** ~28% of valid records
- **Duplicate report IDs:** < 1% within a single ingestion cycle; handled by `dropDuplicates`

---

## Outlier Handling

| Field | Rule | Implementation |
|-------|------|---------------|
| `patient_age` | Negative values → null | `when(col("patient_age") < 0, lit(None))` |
| `patient_weight` | Negative values → null | `when(col("patient_weight") < 0, lit(None))` |
| Null numerics | Replaced with column median | Spark `Imputer(strategy="median")` |
| Null categoricals | Replaced with "unknown" | `fillna({"patient_sex": "unknown", ...})` |
