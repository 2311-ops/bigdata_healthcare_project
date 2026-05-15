# Healthcare Big Data Analytics Platform

A comprehensive, fully Dockerized healthcare analytics platform that ingests data from the openFDA API, processes it through Apache Kafka and HDFS, applies machine learning models using Spark, and stores results in PostgreSQL with visualization dashboards.

**Data Pipeline:**
```
Healthcare API → Kafka → HDFS → Spark Streaming → Spark MLlib → PostgreSQL → Dashboards
```

## 🚀 Quick Start with Docker

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 30GB free disk space

### Run Everything in One Command

```bash
docker-compose up -d
```

This starts all services:
- ✅ Zookeeper & Kafka (message streaming)
- ✅ HDFS NameNode & DataNode (data storage)
- ✅ PostgreSQL 15 (data warehouse)
- ✅ Python producer container (data ingestion)

### Monitor Services Health

```bash
docker-compose ps
docker-compose logs -f
```

### Stop All Services

```bash
docker-compose down -v  # -v removes persistent volumes
```

## 📋 What's Included

### Core Components
- **openFDA API Producer** - Continuously ingests healthcare data via REST API
- **Kafka** - Distributed message broker for real-time data streaming
- **HDFS** - Hadoop Distributed File System for scalable data storage
- **Spark** - Distributed processing engine with structured streaming & MLlib
- **PostgreSQL** - Relational data warehouse for analytics queries
- **Metabase** - Business intelligence dashboards (connects to PostgreSQL)

### Project Structure

```
bigdata_healthcare_project/
├── docker-compose.yml          # Multi-container orchestration
├── Dockerfile                  # Python producer image
├── requirements.txt            # Python dependencies
├── producer/                   # openFDA API data ingestion
│   └── api_healthcare_producer.py
├── spark_jobs/                 # Distributed processing jobs
│   ├── phase2_cleaning_stream.py       # Data cleaning
│   ├── phase3_ml_pipeline.py           # ML model training
│   └── phase4_reporting.py             # Analytics aggregation
├── utils/                      # Utility modules
│   ├── kafka_utils.py
│   ├── postgres_utils.py
│   └── spark_utils.py
├── scripts/                    # Execution scripts
│   ├── start_all_services.sh
│   ├── run_full_pipeline.sh
│   └── check_*.sh
├── database/
│   └── init.sql               # PostgreSQL schema initialization
└── docs/                      # Architecture & setup guides
```

## 🔧 Running the Data Pipeline

### Option 1: Start Services Only
```bash
docker-compose up -d
scripts/start_all_services.sh
```

### Option 2: Run Complete Pipeline
```bash
docker-compose up -d
scripts/run_full_pipeline.sh
```

Customize warmup delay (seconds before ML jobs start):
```bash
PIPELINE_WARMUP_SECONDS=300 scripts/run_full_pipeline.sh
```

### Option 3: Run Individual Phases

Start services first:
```bash
docker-compose up -d
```

Then run phases sequentially:
```bash
scripts/run_api_ingestion.sh    # Phase 1: Data ingestion
scripts/run_phase2.sh            # Phase 2: Data cleaning
scripts/run_phase3.sh            # Phase 3: ML training
scripts/run_phase4.sh            # Phase 4: Reporting
```

## 📊 Access Services

Once containers are running:

| Service | URL/Connection | Credentials |
|---------|---|---|
| Kafka | `kafka:9092` (internal) | - |
| HDFS | `http://localhost:50070` | - |
| PostgreSQL | `localhost:5432` | `healthcare` / `healthcare123` |
| Metabase | `http://localhost:3000` | Configure on first visit |

## 💾 Data Locations

### HDFS Paths
- `/healthcare/raw` - Raw API ingestion data
- `/healthcare/processed` - Cleaned & transformed data
- `/healthcare/models` - Serialized ML models
- `/healthcare/reporting` - Aggregated analytics results

### PostgreSQL Tables
- `cleaned_patients` - Cleaned patient data
- `patient_predictions` - ML model predictions
- `model_evaluation` - Model performance metrics
- `risk_summary` - Risk assessment aggregations

## 🔍 Monitoring & Troubleshooting

### Check Service Status
```bash
docker-compose ps
docker-compose logs kafka
docker-compose logs namenode
docker-compose logs postgres
```

### Verify Connectivity
```bash
scripts/check_kafka.sh
scripts/check_hdfs.sh
scripts/check_postgres.sh
```

### View Logs
```bash
# Tail all logs
docker-compose logs -f

# Specific service
docker-compose logs -f spark-master
docker-compose logs -f postgres
```

### Reset Everything
```bash
docker-compose down -v  # Remove all containers and volumes
docker-compose up -d    # Start fresh
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
POSTGRES_USER=healthcare
POSTGRES_PASSWORD=healthcare123
POSTGRES_DB=healthcare_dw
KAFKA_BROKER_PORT=9092
HDFS_NAMENODE_PORT=8020
```

### Database Initialization
- SQL schema auto-loads from `database/init.sql`
- Tables created automatically on first PostgreSQL start
- Credentials: `healthcare` / `healthcare123`

## 📚 Architecture Details

See [technical_documentation.md](docs/technical_documentation.md) for:
- System architecture diagrams
- Data flow explanations
- Component interactions
- Performance considerations

## 🛠️ Development

### Install Dependencies Locally
```bash
pip install -r requirements.txt
```

### Running Producer Locally
```bash
python producer/api_healthcare_producer.py
```

### Build Custom Images
```bash
docker build -t healthcare-producer:latest .
```

## 📝 Notes

- **Producer** runs continuously in the background
- **Spark jobs** execute via `spark-submit` from the Spark master container
- **PostgreSQL** is the single source of truth for data warehouse queries
- **Metabase** dashboards query PostgreSQL directly
- **HDFS** stores raw and intermediate data for fault tolerance

## 🤝 Support

For detailed setup instructions, see [setup_guide.md](docs/setup_guide.md)

For architecture overview, see [architecture.md](docs/architecture.md)

## 📄 License

This project is provided as-is for educational and research purposes.
