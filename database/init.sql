CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS cleaned_patients (
    id BIGSERIAL PRIMARY KEY,
    report_id TEXT,
    source_api TEXT,
    ingestion_timestamp TIMESTAMPTZ,
    batch_number INTEGER,
    api_endpoint TEXT,
    receipt_date DATE,
    patient_age DOUBLE PRECISION,
    patient_weight DOUBLE PRECISION,
    patient_sex TEXT,
    medicinal_product TEXT,
    reaction TEXT,
    serious BOOLEAN,
    seriousness_death BOOLEAN,
    seriousness_hospitalization BOOLEAN,
    risk_label INTEGER,
    raw_record TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patient_predictions (
    id BIGSERIAL PRIMARY KEY,
    report_id TEXT,
    source_api TEXT,
    model_name TEXT,
    model_version TEXT,
    receipt_date DATE,
    patient_sex TEXT,
    medicinal_product TEXT,
    prediction INTEGER,
    prediction_probability DOUBLE PRECISION,
    risk_label INTEGER,
    scoring_timestamp TIMESTAMPTZ,
    features TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_evaluation (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT,
    model_version TEXT,
    metric_name TEXT,
    metric_value DOUBLE PRECISION,
    split_name TEXT,
    trained_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_summary (
    id BIGSERIAL PRIMARY KEY,
    summary_date DATE,
    dimension_type TEXT,
    dimension_value TEXT,
    total_records BIGINT,
    high_risk_records BIGINT,
    low_risk_records BIGINT,
    average_probability DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cleaned_patients_report_id ON cleaned_patients(report_id);
CREATE INDEX IF NOT EXISTS idx_patient_predictions_report_id ON patient_predictions(report_id);
CREATE INDEX IF NOT EXISTS idx_risk_summary_summary_date ON risk_summary(summary_date);
