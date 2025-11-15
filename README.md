# Real-Time Insurance Risk & Loss Ratio Analytics Platform  
### *End-to-End ELT Pipeline using Snowflake, dbt, Airflow, Python, PySpark & Terraform*

![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-CB3D3D?style=for-the-badge&logo=dbt&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![PySpark](https://img.shields.io/badge/PySpark-E25A1C?style=for-the-badge&logo=apache-spark&logoColor=white)

---

## 📌 Project Overview

Insurance companies in 2025 face a major challenge:  
**their pricing, risk scoring, and loss ratio analysis rely on slow, fragmented, non-governed data pipelines.**

This prevents real-time decision-making and creates inefficiencies for actuaries, analysts, and underwriting teams.

This project builds a **modern, cloud-native ELT data platform** that simulates how insurers (like Aviva, AXA, Zurich) unify and transform **policy, quotes, and claims data** into analytics-ready tables for:

- Pricing adequacy  
- Loss ratio monitoring  
- Risk segmentation  
- Claims behaviour insights  
- Fraud detection  

Although designed for the cloud, the entire pipeline runs **locally** using Snowflake, dbt, Airflow, Python, and Terraform.

---

## 🏗️ Architecture Diagram

```mermaid
flowchart TD
    A[Python Synthetic Data Generator] --> B[Local Raw Data Zone]
    B --> C[Snowflake RAW Layer]

    C --> D[dbt STAGING Models]
    D --> E[dbt CORE Models]
    E --> F[dbt MARTS Models]

    F --> G[Feature Engineering in Python/PySpark]
    G --> H[Final Risk & Loss Ratio Data Products]

    H --> I[BI Dashboards / Analytics / ML Models]

    subgraph Orchestration
        J[Airflow DAG]
    end
    J --> A
    J --> C
    J --> D
    J --> G

## 🚀 Key Features

### 🔹 End-to-End ELT Pipeline
- Synthetic insurance dataset generation using Python
- Batch ingestion into **Snowflake RAW** layer
- dbt transformations across **STAGING → CORE → MARTS**
- Feature engineering using Pandas & PySpark
- Full workflow orchestration with Airflow

### 🔹 Modern Data Warehouse Architecture
- Fully modular dbt project structure
- Dimensional and entity modeling for policies, quotes & claims
- Source freshness checks & built-in data quality tests
- Auto-generated dbt lineage and documentation

### 🔹 Insurance Risk & Pricing Analytics
- Earned Premium (EP) calculations  
- Incurred Claims (IC) roll-ups  
- Loss Ratio (IC / EP) metrics  
- Customer segmentation (risk bands, channels, behaviour)
- Product performance analytics across time periods

### 🔹 Terraform Infrastructure as Code
Defines and manages:
- Warehouses
- Databases
- Schemas
- Stages
- Storage integrations
- Role-based access controls (RBAC)

### 🔹 CI/CD with GitHub Actions
- dbt compile & dbt tests on every commit
- Python linting & unit tests
- Terraform `fmt` + `validate`
- Branch protection workflow for PRs

### 🔹 Full Local Simulation of a Cloud Data Platform
- No AWS access required  
- Local execution with Docker + Snowflake  
- Cloud-ready architecture that can be deployed to AWS later  

## ⚙️ Airflow DAG Workflow
generate_synthetic_data      (PythonOperator)
load_raw_to_snowflake        (BashOperator)
run_dbt_transforms           (BashOperator)
run_feature_engineering      (PythonOperator / PySpark)
data_quality_summary         (PythonOperator)

## Repository Structure
snowflake-dbt-airflow-insurance-data-platform/
│
├── airflow/
│   ├── dags/
│   │   └── insurance_elt_pipeline.py
│   └── docker-compose.yml
│
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_quotes.sql
│   │   │   ├── stg_policies.sql
│   │   │   └── stg_claims.sql
│   │   ├── core/
│   │   │   ├── core_policy_snapshot.sql
│   │   │   └── core_policy_claims.sql
│   │   └── marts/
│   │       ├── mart_loss_ratio_by_segment.sql
│   │       ├── mart_customer_risk.sql
│   │       └── mart_product_performance.sql
│   ├── seeds/
│   ├── snapshots/
│   ├── tests/
│   ├── macros/
│   └── dbt_project.yml
│
├── python/
│   ├── generate_data.py
│   ├── feature_engineering.py
│   ├── utils/
│   │   ├── snowflake_client.py
│   │   └── transformations.py
│   └── notebooks/
│       └── eda.ipynb
│
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── snowflake/
│       ├── warehouse.tf
│       ├── database.tf
│       ├── roles_users.tf
│       └── stages.tf
│
├── data/
│   ├── raw/
│   │   ├── quotes/
│   │   ├── policies/
│   │   └── claims/
│   └── sample/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── requirements.txt
├── .env.example
└── README.md

## 📊 Outputs

- Modeled Snowflake warehouse tables
- Integrated policy-claims datasets
- Loss ratio metrics by product/segment
- dbt lineage & documentation
- Airflow workflow logs
- Terraform-managed Snowflake infra
- Feature engineering outputs

## EDA notebooks

🏁 Future Enhancements

- Add LocalStack (simulate S3 ingestion)
- Add Streamlit BI dashboard
- Add Snowflake Snowpark ML
- Deploy Airflow on AWS MWAA
- Add Kafka/Snowpipe streaming ingestion

👤 Author

Thrisha Rajkumat
Data Scientist & Cloud Data Engineering Enthusiast
Building scalable, cloud-native ELT pipelines for real-world business problems.

⭐ Support

If this project inspires you, please give the repo a ⭐!
