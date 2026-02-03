"""
Insurance ELT Pipeline DAG

This DAG orchestrates the complete ELT pipeline for insurance data:
1. Generate synthetic data (quotes, policies, claims)
2. Load raw data to Snowflake
3. Run dbt transformations (staging -> core -> marts)
4. Run feature engineering
5. Data quality summary
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


# Default arguments for all tasks
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
DBT_DIR = os.path.join(PROJECT_ROOT, "dbt")


def generate_synthetic_data_callable():
    """Generate synthetic insurance data."""
    sys.path.insert(0, PROJECT_ROOT)
    from python.generate_data import main as generate_main
    
    result = generate_main()
    print(f"Generated {result['quotes_count']} quotes, {result['policies_count']} policies, {result['claims_count']} claims")
    return result


def load_raw_to_snowflake_callable():
    """Load raw CSV data to Snowflake."""
    sys.path.insert(0, PROJECT_ROOT)
    from python.load_to_snowflake import main as load_main
    
    result = load_main(truncate=True)
    print(f"Loaded {result['quotes_loaded']} quotes, {result['policies_loaded']} policies, {result['claims_loaded']} claims")
    return result


def run_feature_engineering_callable():
    """Run feature engineering on mart data."""
    sys.path.insert(0, PROJECT_ROOT)
    from python.feature_engineering import main as feature_main
    
    feature_main()
    print("Feature engineering completed")


def data_quality_summary_callable(**context):
    """Generate data quality summary."""
    ti = context["ti"]
    
    # Get results from previous tasks
    generate_result = ti.xcom_pull(task_ids="generate_synthetic_data")
    load_result = ti.xcom_pull(task_ids="load_raw_to_snowflake")
    
    print("=" * 60)
    print("DATA QUALITY SUMMARY")
    print("=" * 60)
    
    if generate_result:
        print(f"\nData Generation:")
        print(f"  - Quotes generated: {generate_result.get('quotes_count', 'N/A')}")
        print(f"  - Policies generated: {generate_result.get('policies_count', 'N/A')}")
        print(f"  - Claims generated: {generate_result.get('claims_count', 'N/A')}")
    
    if load_result:
        print(f"\nData Loading:")
        print(f"  - Quotes loaded: {load_result.get('quotes_loaded', 'N/A')}")
        print(f"  - Policies loaded: {load_result.get('policies_loaded', 'N/A')}")
        print(f"  - Claims loaded: {load_result.get('claims_loaded', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)


with DAG(
    dag_id="insurance_elt_pipeline",
    description="End-to-end ELT pipeline for insurance data analytics",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    tags=["insurance", "elt", "dbt", "snowflake"],
) as dag:
    
    # Start marker
    start = EmptyOperator(task_id="start")
    
    # Task 1: Generate synthetic data
    generate_synthetic_data = PythonOperator(
        task_id="generate_synthetic_data",
        python_callable=generate_synthetic_data_callable,
    )
    
    # Task 2: Load raw data to Snowflake
    load_raw_to_snowflake = PythonOperator(
        task_id="load_raw_to_snowflake",
        python_callable=load_raw_to_snowflake_callable,
    )
    
    # Task 3: Run dbt transformations
    run_dbt_transforms = BashOperator(
        task_id="run_dbt_transforms",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir {DBT_DIR}",
        env={
            **os.environ,
            "DBT_PROFILES_DIR": DBT_DIR,
        },
    )
    
    # Task 4: Run dbt tests
    run_dbt_tests = BashOperator(
        task_id="run_dbt_tests",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir {DBT_DIR}",
        env={
            **os.environ,
            "DBT_PROFILES_DIR": DBT_DIR,
        },
    )
    
    # Task 5: Run feature engineering
    run_feature_engineering = PythonOperator(
        task_id="run_feature_engineering",
        python_callable=run_feature_engineering_callable,
    )
    
    # Task 6: Data quality summary
    data_quality_summary = PythonOperator(
        task_id="data_quality_summary",
        python_callable=data_quality_summary_callable,
        provide_context=True,
    )
    
    # End marker
    end = EmptyOperator(task_id="end")
    
    # Define task dependencies
    start >> generate_synthetic_data >> load_raw_to_snowflake >> run_dbt_transforms
    run_dbt_transforms >> run_dbt_tests >> run_feature_engineering >> data_quality_summary >> endc.
