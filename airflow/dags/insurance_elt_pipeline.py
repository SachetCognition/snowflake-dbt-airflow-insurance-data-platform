"""
Insurance ELT Pipeline DAG

This DAG orchestrates the complete ELT pipeline for insurance data:
1. Generate synthetic data (quotes, policies, claims)
2. Load raw data to Snowflake
3. Run dbt transformations (staging -> core -> marts)
4. Run feature engineering
5. Data quality validation
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

sys.path.insert(0, "/opt/airflow/python")

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def generate_synthetic_data():
    """Generate synthetic insurance data (quotes, policies, claims)."""
    from generate_data import main as generate_main
    generate_main()


def load_raw_to_snowflake():
    """Load CSV files from data/raw to Snowflake RAW schema."""
    import snowflake.connector
    import pandas as pd
    
    conn = snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "INSURANCE_DB"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "RAW"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "WH_INSURANCE"),
        role=os.environ.get("SNOWFLAKE_ROLE", "DATA_ENGINEER"),
    )
    
    cursor = conn.cursor()
    
    data_dir = "/opt/airflow/data/raw"
    
    tables = {
        "quotes": "RAW_QUOTES",
        "policies": "RAW_POLICIES",
        "claims": "RAW_CLAIMS",
    }
    
    for subdir, table_name in tables.items():
        csv_path = os.path.join(data_dir, subdir, f"{subdir}.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            
            columns = ", ".join(df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([f'{col} VARCHAR' for col in df.columns])})")
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            
            for _, row in df.iterrows():
                cursor.execute(
                    f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                    tuple(row.values)
                )
            
            print(f"Loaded {len(df)} rows into {table_name}")
    
    cursor.close()
    conn.close()


def run_feature_engineering():
    """Run feature engineering on mart tables."""
    from feature_engineering import main as feature_main
    feature_main()


def data_quality_summary():
    """Generate data quality summary report."""
    import snowflake.connector
    
    conn = snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "INSURANCE_DB"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "WH_INSURANCE"),
        role=os.environ.get("SNOWFLAKE_ROLE", "DATA_ENGINEER"),
    )
    
    cursor = conn.cursor()
    
    schemas = ["RAW", "STAGING", "CORE", "MARTS"]
    
    for schema in schemas:
        cursor.execute(f"SHOW TABLES IN SCHEMA {schema}")
        tables = cursor.fetchall()
        print(f"\n=== Schema: {schema} ===")
        for table in tables:
            table_name = table[1]
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count} rows")
    
    cursor.close()
    conn.close()


with DAG(
    dag_id="insurance_elt_pipeline",
    default_args=default_args,
    description="Insurance ELT Pipeline: Generate -> Load -> Transform -> Feature Engineering",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["insurance", "elt", "dbt"],
) as dag:
    
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    
    generate_data_task = PythonOperator(
        task_id="generate_synthetic_data",
        python_callable=generate_synthetic_data,
    )
    
    load_raw_task = PythonOperator(
        task_id="load_raw_to_snowflake",
        python_callable=load_raw_to_snowflake,
    )
    
    with TaskGroup(group_id="dbt_transforms") as dbt_transforms:
        dbt_deps = BashOperator(
            task_id="dbt_deps",
            bash_command="cd /opt/airflow/dbt && dbt deps",
        )
        
        dbt_staging = BashOperator(
            task_id="dbt_run_staging",
            bash_command="cd /opt/airflow/dbt && dbt run --select staging.*",
        )
        
        dbt_core = BashOperator(
            task_id="dbt_run_core",
            bash_command="cd /opt/airflow/dbt && dbt run --select core.*",
        )
        
        dbt_marts = BashOperator(
            task_id="dbt_run_marts",
            bash_command="cd /opt/airflow/dbt && dbt run --select marts.*",
        )
        
        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command="cd /opt/airflow/dbt && dbt test",
        )
        
        dbt_deps >> dbt_staging >> dbt_core >> dbt_marts >> dbt_test
    
    feature_eng_task = PythonOperator(
        task_id="run_feature_engineering",
        python_callable=run_feature_engineering,
    )
    
    data_quality_task = PythonOperator(
        task_id="data_quality_summary",
        python_callable=data_quality_summary,
    )
    
    start >> generate_data_task >> load_raw_task >> dbt_transforms >> feature_eng_task >> data_quality_task >> end
