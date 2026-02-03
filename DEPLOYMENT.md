# Deployment Guide

This guide provides step-by-step instructions for setting up and running the Insurance Data Platform locally.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9 or higher
- pip (Python package manager)
- Git
- A Snowflake account with appropriate permissions
- Docker and Docker Compose (optional, for Airflow)

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SachetCognition/snowflake-dbt-airflow-insurance-data-platform.git
cd snowflake-dbt-airflow-insurance-data-platform
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update it with your Snowflake credentials:

```bash
cp .env.example .env
```

Edit the `.env` file with your Snowflake connection details:

```bash
# Snowflake Connection
export SNOWFLAKE_ACCOUNT=your_account_identifier
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_ROLE=ACCOUNTADMIN  # or your designated role
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export SNOWFLAKE_DATABASE=INSURANCE_DB
export SNOWFLAKE_SCHEMA=RAW

# dbt Configuration
export DBT_TARGET=dev

# Environment
export ENVIRONMENT=local
```

Load the environment variables:

```bash
source .env
```

### 5. Create Snowflake Database and Schemas

Connect to Snowflake and run the following SQL commands:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS INSURANCE_DB;

-- Create schemas for each layer
USE DATABASE INSURANCE_DB;
CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS CORE;
CREATE SCHEMA IF NOT EXISTS MARTS;

-- Grant permissions (adjust role as needed)
GRANT ALL ON DATABASE INSURANCE_DB TO ROLE ACCOUNTADMIN;
GRANT ALL ON ALL SCHEMAS IN DATABASE INSURANCE_DB TO ROLE ACCOUNTADMIN;
```

### 6. Configure dbt Profile

Create or update your dbt profiles file at `~/.dbt/profiles.yml`:

```yaml
insurance_snowflake:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      schema: RAW
      threads: 4
```

## Running the Pipeline

### Step 1: Generate Synthetic Data

Run the data generation script to create CSV files:

```bash
cd /path/to/project
python python/generate_data.py
```

This will create the following files in `data/raw/`:
- `quotes/quotes.csv` - 5000 quote records
- `policies/policies.csv` - ~2000 policy records (40% conversion rate)
- `claims/claims.csv` - Variable number of claims

Expected output:
```
Data generation complete:
  Quotes: 5000 records -> data/raw/quotes/quotes.csv
  Policies: 2000 records -> data/raw/policies/policies.csv
  Claims: 1200 records -> data/raw/claims/claims.csv
```

### Step 2: Load Data to Snowflake

Load the generated CSV data into Snowflake RAW tables:

```bash
python python/load_to_snowflake.py
```

This script will:
1. Create RAW_QUOTES, RAW_POLICIES, and RAW_CLAIMS tables if they don't exist
2. Truncate existing data (optional, controlled by `truncate` parameter)
3. Load CSV data into the tables

Expected output:
```
Data load complete:
  Quotes loaded: 5000
  Policies loaded: 2000
  Claims loaded: 1200
```

### Step 3: Run dbt Transformations

Navigate to the dbt directory and run the transformations:

```bash
cd dbt

# Test the connection
dbt debug

# Compile models (validates SQL without running)
dbt compile

# Run all models
dbt run

# Run tests
dbt test
```

The dbt run will create views in the following schemas:
- **STAGING**: `stg_quotes`, `stg_policies`, `stg_claims`
- **CORE**: `core_policy_claims`, `core_policy_snapshot`
- **MARTS**: `mart_loss_ratio_by_segment`, `mart_customer_risk`, `mart_product_performance`

### Step 4: Verify Data in Snowflake

Connect to Snowflake and verify data exists in all layers:

```sql
-- Check RAW layer
SELECT COUNT(*) FROM INSURANCE_DB.RAW.RAW_QUOTES;
SELECT COUNT(*) FROM INSURANCE_DB.RAW.RAW_POLICIES;
SELECT COUNT(*) FROM INSURANCE_DB.RAW.RAW_CLAIMS;

-- Check STAGING layer
SELECT COUNT(*) FROM INSURANCE_DB.STAGING.STG_QUOTES;
SELECT COUNT(*) FROM INSURANCE_DB.STAGING.STG_POLICIES;
SELECT COUNT(*) FROM INSURANCE_DB.STAGING.STG_CLAIMS;

-- Check CORE layer
SELECT COUNT(*) FROM INSURANCE_DB.CORE.CORE_POLICY_CLAIMS;
SELECT COUNT(*) FROM INSURANCE_DB.CORE.CORE_POLICY_SNAPSHOT;

-- Check MARTS layer
SELECT * FROM INSURANCE_DB.MARTS.MART_LOSS_RATIO_BY_SEGMENT;
SELECT * FROM INSURANCE_DB.MARTS.MART_CUSTOMER_RISK LIMIT 10;
SELECT * FROM INSURANCE_DB.MARTS.MART_PRODUCT_PERFORMANCE;
```

## Running with Airflow (Optional)

### Start Airflow

```bash
cd airflow
docker-compose up -d
```

Access the Airflow UI at http://localhost:8080 (default credentials: airflow/airflow).

### Trigger the Pipeline

1. Navigate to the Airflow UI
2. Find the `insurance_elt_pipeline` DAG
3. Enable the DAG
4. Click "Trigger DAG" to run manually

The DAG will execute the following tasks in order:
1. `generate_synthetic_data` - Generate CSV files
2. `load_raw_to_snowflake` - Load data to Snowflake
3. `run_dbt_transforms` - Execute dbt models
4. `run_dbt_tests` - Run dbt tests
5. `run_feature_engineering` - Run feature engineering (placeholder)
6. `data_quality_summary` - Generate summary report

## Running Tests

### Python Unit Tests

```bash
# From project root
pytest tests/ -v
```

### dbt Tests

```bash
cd dbt
dbt test
```

## Configuration

### Data Generation Configuration

The `config.yaml` file controls data generation parameters:

```yaml
data_generation:
  n_customers: 2000      # Number of unique customers
  n_quotes: 5000         # Total quotes to generate
  conversion_rate: 0.4   # 40% of quotes become policies
  max_claims_per_policy: 3
  rng_seed: 42           # For reproducibility
```

### Logging Configuration

Logs are written to `logs/insurance_platform.log`. Configure logging in `config.yaml`:

```yaml
logging:
  level: "INFO"          # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/insurance_platform.log"
```

## Troubleshooting

### Common Issues

**1. Snowflake Connection Errors**

If you see connection errors, verify:
- Environment variables are set correctly
- Snowflake account identifier format (e.g., `abc12345.us-east-1`)
- Network connectivity to Snowflake
- Role has appropriate permissions

**2. dbt Compilation Errors**

If dbt compile fails:
- Verify `~/.dbt/profiles.yml` exists and is configured correctly
- Run `dbt debug` to test the connection
- Check that source tables exist in RAW schema

**3. Missing Data Files**

If load_to_snowflake.py fails with "file not found":
- Ensure you ran `python/generate_data.py` first
- Check that `data/raw/` directory contains CSV files

**4. Permission Errors**

If you see permission errors in Snowflake:
- Verify your role has CREATE TABLE, INSERT, SELECT permissions
- Check schema ownership

### Getting Help

For additional support:
- Check the project README.md
- Review the business logic analysis document
- Open an issue on GitHub

## Architecture Overview

```
CSV Files (data/raw/)
        |
        v
[RAW Schema] - Raw tables loaded from CSV
        |
        v
[STAGING Schema] - Cleaned and standardized data
        |
        v
[CORE Schema] - Business logic and entity resolution
        |
        v
[MARTS Schema] - Analytics-ready aggregations
```

## Next Steps

After successful deployment:

1. **Explore the Data**: Query the mart tables to understand the analytics available
2. **Customize Configuration**: Adjust `config.yaml` to generate different data volumes
3. **Extend Models**: Add new dbt models for additional analytics
4. **Set Up Scheduling**: Configure Airflow to run on a schedule
5. **Add Monitoring**: Implement data quality monitoring and alerting
