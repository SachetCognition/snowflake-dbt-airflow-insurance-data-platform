"""
Insurance ELT Pipeline DAG

This DAG orchestrates the complete insurance data pipeline including:
1. Synthetic data generation with fraud patterns
2. Data loading to Snowflake RAW schema
3. dbt transformations (STAGING -> CORE -> MARTS)
4. Fraud detection (rule-based, ML-based, network analysis)
5. Data quality validation
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

# Default arguments for all tasks
default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Python callables for tasks
def generate_synthetic_data():
    """Generate synthetic insurance data with fraud patterns."""
    import sys
    sys.path.insert(0, '/opt/airflow/python')
    from generate_data import main as generate_main
    generate_main()

def run_fraud_rules():
    """Run rule-based fraud detection."""
    import sys
    sys.path.insert(0, '/opt/airflow/python')
    from fraud_rules import run_fraud_detection
    run_fraud_detection(output_path='/opt/airflow/data/fraud_results/rules/')

def run_fraud_ml():
    """Run ML-based fraud detection."""
    import sys
    sys.path.insert(0, '/opt/airflow/python')
    from fraud_ml_model import run_ml_fraud_detection
    run_ml_fraud_detection(output_path='/opt/airflow/data/fraud_results/ml/')

def run_fraud_network():
    """Run network-based fraud detection."""
    import sys
    sys.path.insert(0, '/opt/airflow/python')
    from fraud_network import run_network_analysis
    run_network_analysis(output_path='/opt/airflow/data/fraud_results/network/')

def data_quality_summary():
    """Generate data quality summary report."""
    import snowflake.connector
    import os
    
    conn = snowflake.connector.connect(
        account=os.environ.get('SNOWFLAKE_ACCOUNT'),
        user=os.environ.get('SNOWFLAKE_USER'),
        password=os.environ.get('SNOWFLAKE_PASSWORD'),
        role=os.environ.get('SNOWFLAKE_ROLE'),
        warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE'),
        database='INSURANCE_DB'
    )
    cursor = conn.cursor()
    
    # Check row counts
    tables = [
        ('RAW', 'QUOTES'),
        ('RAW', 'POLICIES'),
        ('RAW', 'CLAIMS'),
        ('RAW_MARTS', 'MART_FRAUD_FEATURES'),
    ]
    
    print("=== Data Quality Summary ===")
    for schema, table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM INSURANCE_DB.{schema}.{table}')
        count = cursor.fetchone()[0]
        print(f"{schema}.{table}: {count} rows")
    
    # Check fraud distribution
    cursor.execute("""
        SELECT fraud_risk_tier, COUNT(*) 
        FROM INSURANCE_DB.RAW_MARTS.MART_FRAUD_FEATURES 
        GROUP BY fraud_risk_tier
    """)
    print("\nFraud Risk Distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} claims")
    
    cursor.close()
    conn.close()


with DAG(
    dag_id="insurance_elt_pipeline",
    default_args=default_args,
    description="Insurance ELT pipeline with fraud detection",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=['insurance', 'elt', 'fraud_detection'],
) as dag:
    
    # Start and end markers
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    
    # Task 1: Generate synthetic data
    generate_data = PythonOperator(
        task_id="generate_synthetic_data",
        python_callable=generate_synthetic_data,
    )
    
    # Task 2: Load data to Snowflake RAW schema
    load_to_snowflake = BashOperator(
        task_id="load_raw_to_snowflake",
        bash_command="""
            cd /opt/airflow && python -c "
import snowflake.connector
import pandas as pd
import os
from snowflake.connector.pandas_tools import write_pandas

conn = snowflake.connector.connect(
    account=os.environ['SNOWFLAKE_ACCOUNT'],
    user=os.environ['SNOWFLAKE_USER'],
    password=os.environ['SNOWFLAKE_PASSWORD'],
    role=os.environ['SNOWFLAKE_ROLE'],
    warehouse=os.environ['SNOWFLAKE_WAREHOUSE'],
    database='INSURANCE_DB',
    schema='RAW'
)

# Load quotes
df_quotes = pd.read_csv('/opt/airflow/data/raw/quotes/quotes.csv')
write_pandas(conn, df_quotes, 'QUOTES', auto_create_table=True, overwrite=True)
print(f'Loaded {len(df_quotes)} quotes')

# Load policies
df_policies = pd.read_csv('/opt/airflow/data/raw/policies/policies.csv')
write_pandas(conn, df_policies, 'POLICIES', auto_create_table=True, overwrite=True)
print(f'Loaded {len(df_policies)} policies')

# Load claims
df_claims = pd.read_csv('/opt/airflow/data/raw/claims/claims.csv')
write_pandas(conn, df_claims, 'CLAIMS', auto_create_table=True, overwrite=True)
print(f'Loaded {len(df_claims)} claims')

conn.close()
print('Data loading complete!')
"
        """,
    )
    
    # Task 3: Run dbt transformations
    run_dbt = BashOperator(
        task_id="run_dbt_transforms",
        bash_command="cd /opt/airflow/dbt && dbt run --profiles-dir /opt/airflow/dbt",
    )
    
    # Task Group: Fraud Detection
    with TaskGroup(group_id="fraud_detection") as fraud_detection_group:
        
        # Rule-based fraud detection
        fraud_rules_task = PythonOperator(
            task_id="run_fraud_rules",
            python_callable=run_fraud_rules,
        )
        
        # ML-based fraud detection
        fraud_ml_task = PythonOperator(
            task_id="run_fraud_ml",
            python_callable=run_fraud_ml,
        )
        
        # Network-based fraud detection
        fraud_network_task = PythonOperator(
            task_id="run_fraud_network",
            python_callable=run_fraud_network,
        )
        
        # These can run in parallel
        [fraud_rules_task, fraud_ml_task, fraud_network_task]
    
    # Task 5: Data quality validation
    quality_check = PythonOperator(
        task_id="data_quality_summary",
        python_callable=data_quality_summary,
    )
    
    # Define task dependencies
    start >> generate_data >> load_to_snowflake >> run_dbt >> fraud_detection_group >> quality_check >> end
