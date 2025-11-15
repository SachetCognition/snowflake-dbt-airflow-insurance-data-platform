# Real-Time Insurance Risk & Loss Ratio Analytics Platform  
### *End-to-End ELT Pipeline using Snowflake, dbt, Airflow, Python, PySpark & Terraform*

---

## 📌 Project Overview

Insurance companies in 2025 face a critical challenge:  
**their pricing, risk scoring, and loss ratio analysis rely on slow, fragmented, non-governed data pipelines.**

This prevents real-time decision-making, limits AI adoption, and creates major inefficiencies for actuaries, analysts, and data scientists.

This project builds a **modern, cloud-native ELT data platform** that simulates how insurers (like Aviva) unify and transform policy, quotes, and claims data into analytics-ready tables for **pricing adequacy, loss ratio monitoring, fraud insights, and risk segmentation**.

Although designed for AWS, the entire pipeline runs locally using:

- **Snowflake** (cloud data warehouse)
- **dbt Core** (SQL transformations, models, tests, documentation)
- **Airflow** (local orchestration)
- **Python + Pandas + PySpark** (data generation, feature engineering)
- **Terraform** (Snowflake infrastructure as code)
- **GitHub Actions CI/CD** (tests and automation)

The platform is cloud-ready and can be deployed to AWS (S3 + MWAA) with minimal changes.

---

## 🚀 Key Features

### 🔹 End-to-End ELT Pipeline
- **Generate synthetic insurance datasets** (policies, claims, quotes)
- **Ingest into Snowflake RAW** tables via internal stages
- **Transform using dbt** into STAGING → CORE → MARTS layers
- **Compute loss ratios & risk features** using Python/Pandas/PySpark
- **Run the full workflow** with an Airflow DAG

### 🔹 Modern Data Warehouse Architecture
- RAW → STAGING → CORE → MARTS
- dbt tests for:
  - Primary keys
  - Foreign key integrity
  - Business rules (premium ≥ 0, valid dates, loss ratio ≥ 0)
- Auto-generated docs & lineage graph

### 🔹 Risk & Pricing Metrics
- Earned premium (EP)
- Incurred claims (IC)
- Loss ratio = IC / EP
- Policy-level risk scores
- Segment-level profitability

### 🔹 Infrastructure as Code
Terraform manages Snowflake objects:
- Warehouses  
- Databases  
- Schemas  
- Stages  
- Roles & Grants  

### 🔹 CI/CD Automation (GitHub Actions)
- dbt compile + tests  
- Terraform validation  
- Python linting + tests  

---

## 🏗️ Architecture

### **High-Level Flow**

Python Generator → Local Raw Folder → Snowflake RAW →
dbt (STAGING → CORE → MARTS) →
Feature Engineering (Python/PySpark) →
Final Risk & Loss Ratio Data Products →
Consumption (SQL, notebooks, dashboards)


### **Components**

| Layer | Tools | Purpose |
|-------|--------|---------|
| Raw Data Landing | Local filesystem (`./data/raw/`) | Simulates S3 ingestion |
| Data Warehouse | Snowflake | Scalable storage + compute |
| Transformations | dbt Core | SQL models, tests, lineage |
| Orchestration | Airflow | DAG to run full pipeline |
| Engineering | Python, Pandas, PySpark | Risk features, ML-ready tables |
| Infra as Code | Terraform | Snowflake objects as code |
| CI/CD | GitHub Actions | Testing + deployment checks |

---

## 🧱 Data Model (tables)

### 1. **Quotes**
quote_id, customer_id, vehicle_id, quote_datetime,
premium_offered, channel, accepted_flag, risk_band


### 2. **Policies**
policy_id, customer_id, vehicle_id,
inception_date, end_date, status,
written_premium, product_type


### 3. **Claims**
claim_id, policy_id, incident_date, report_date,
paid_amount, reserved_amount, fault_flag, cause,
settlement_status

## 🧩 dbt Models

### **STAGING Layer**
- `stg_quotes.sql`
- `stg_policies.sql`
- `stg_claims.sql`

### **CORE Layer**
- `core_policy_snapshot.sql`
- `core_policy_claims.sql`

### **MARTS Layer**
- `mart_loss_ratio_by_segment.sql`
- `mart_customer_risk.sql`
- `mart_product_performance.sql`

---

## ⚙️ Airflow DAG Pipeline

generate_synthetic_data (PythonOperator)

load_raw_to_snowflake (Snowflake / BashOperator)

run_dbt_transforms (BashOperator)

run_feature_engineering (PythonOperator / PySpark)

data_quality_summary (PythonOperator)



## 📁 Repository Structure

snowflake-dbt-airflow-insurance-data-platform/
│
├── airflow/
│ ├── dags/
│ │ └── insurance_elt_pipeline.py
│ └── docker-compose.yml (if running Airflow with Docker)
│
├── dbt/
│ ├── models/
│ │ ├── staging/
│ │ │ ├── stg_quotes.sql
│ │ │ ├── stg_policies.sql
│ │ │ └── stg_claims.sql
│ │ ├── core/
│ │ │ ├── core_policy_snapshot.sql
│ │ │ └── core_policy_claims.sql
│ │ └── marts/
│ │ ├── mart_loss_ratio_by_segment.sql
│ │ ├── mart_customer_risk.sql
│ │ └── mart_product_performance.sql
│ │
│ ├── seeds/
│ ├── snapshots/
│ ├── tests/
│ ├── macros/
│ └── dbt_project.yml
│
├── python/
│ ├── generate_data.py
│ ├── feature_engineering.py
│ ├── utils/
│ │ ├── snowflake_client.py
│ │ └── transformations.py
│ └── notebooks/
│ └── eda.ipynb
│
├── infra/
│ ├── main.tf
│ ├── variables.tf
│ ├── outputs.tf
│ └── snowflake/
│ ├── warehouse.tf
│ ├── database.tf
│ ├── roles_users.tf
│ └── stages.tf
│
├── data/
│ ├── raw/
│ │ ├── quotes/
│ │ ├── policies/
│ │ └── claims/
│ └── sample/
│
├── .github/
│ └── workflows/
│ └── ci.yml
│
├── requirements.txt
├── .env.example
└── README.md

--- 

## ▶️ How to Run the Project Locally

### 1. Clone the repo
git clone https://github.com/yourname/insurance-risk-lossratio-data-platform.git
cd insurance-risk-lossratio-data-platform

shell
Copy code

### 2. Create a Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

shell
Copy code

### 3. Set up Snowflake credentials  
Use an `.env` file or environment variables.

### 4. Run dbt setup
cd dbt
dbt deps
dbt debug

shell
Copy code

### 5. Start Airflow (Docker recommended)
docker-compose up -d

yaml
Copy code

### 6. Trigger the DAG  
From Airflow UI: `http://localhost:8080`

---

## 📊 Deliverables & Outputs

The pipeline produces:

- Clean, modelled Snowflake tables  
- Loss ratio metrics by segment  
- Risk scores per policy  
- dbt lineage graph  
- Airflow workflow logs  
- Terraform-managed Snowflake infra  
- CI/CD automation  
- Python notebooks for EDA  

All ready to present to employers.

---

## 🏁 Future Enhancements

- Integrate LocalStack to emulate S3  
- Add Snowflake Snowpark ML for model training  
- Add a small Streamlit UI dashboard  
- Deploy Airflow on AWS MWAA (optional)  

---

## 👤 Author

**Thrisha**  
Data Scientist & Data Engineering Enthusiast  
Passionate about building scalable data platforms, ML pipelines, and cloud-native analytics solutions.

---

## ⭐ If you like this project  
Please ⭐ the repo — it helps show support!
