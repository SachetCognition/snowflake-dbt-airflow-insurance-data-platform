#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "Insurance Data Platform - Master Deployment"
echo "=============================================="

check_env_vars() {
    local required_vars=(
        "SNOWFLAKE_ACCOUNT"
        "SNOWFLAKE_USER"
        "SNOWFLAKE_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "ERROR: Required environment variable $var is not set"
            echo "Please set it in your .env file or export it"
            exit 1
        fi
    done
    echo "Environment variables validated"
}

load_env() {
    if [ -f "$BASE_DIR/.env" ]; then
        echo "Loading environment from .env file..."
        set -a
        source "$BASE_DIR/.env"
        set +a
    else
        echo "WARNING: No .env file found. Using environment variables."
    fi
}

step_1_generate_data() {
    echo ""
    echo "Step 1: Generating synthetic insurance data..."
    echo "----------------------------------------------"
    
    cd "$BASE_DIR"
    
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -q -r requirements.txt
    
    echo "Running data generator..."
    python python/generate_data.py
    
    deactivate
    echo "Data generation complete!"
}

step_2_setup_snowflake() {
    echo ""
    echo "Step 2: Setting up Snowflake infrastructure..."
    echo "-----------------------------------------------"
    
    SNOWSQL_CMD="snowsql"
    
    if ! command -v $SNOWSQL_CMD &> /dev/null; then
        echo "WARNING: snowsql not found. Please run the setup SQL manually."
        echo "SQL file location: ../SN_sfguide-getting-started-with-predicting-insurance-claims-regression-model/scripts/setup.sql"
        return 0
    fi
    
    SETUP_SQL_PATH="$BASE_DIR/../SN_sfguide-getting-started-with-predicting-insurance-claims-regression-model/scripts/setup.sql"
    
    if [ -f "$SETUP_SQL_PATH" ]; then
        echo "Executing Snowflake setup script..."
        $SNOWSQL_CMD -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" -f "$SETUP_SQL_PATH"
    else
        echo "WARNING: Setup SQL not found at $SETUP_SQL_PATH"
    fi
    
    echo "Snowflake infrastructure setup complete!"
}

step_3_load_raw_data() {
    echo ""
    echo "Step 3: Loading raw data to Snowflake..."
    echo "-----------------------------------------"
    
    cd "$BASE_DIR"
    source venv/bin/activate
    
    python3 << 'EOF'
import os
import snowflake.connector
import pandas as pd

conn = snowflake.connector.connect(
    account=os.environ.get("SNOWFLAKE_ACCOUNT"),
    user=os.environ.get("SNOWFLAKE_USER"),
    password=os.environ.get("SNOWFLAKE_PASSWORD"),
    database=os.environ.get("SNOWFLAKE_DATABASE", "INSURANCE_DB"),
    schema="RAW",
    warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "WH_INSURANCE"),
    role=os.environ.get("SNOWFLAKE_ROLE", "DATA_ENGINEER"),
)

cursor = conn.cursor()

cursor.execute("CREATE SCHEMA IF NOT EXISTS RAW")
cursor.execute("CREATE SCHEMA IF NOT EXISTS STAGING")
cursor.execute("CREATE SCHEMA IF NOT EXISTS CORE")
cursor.execute("CREATE SCHEMA IF NOT EXISTS MARTS")

data_dir = "data/raw"
tables = {
    "quotes": "RAW_QUOTES",
    "policies": "RAW_POLICIES",
    "claims": "RAW_CLAIMS",
}

for subdir, table_name in tables.items():
    csv_path = os.path.join(data_dir, subdir, f"{subdir}.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"Loading {len(df)} rows into {table_name}...")
        
        col_defs = ", ".join([f'"{col}" VARCHAR' for col in df.columns])
        cursor.execute(f'CREATE OR REPLACE TABLE RAW.{table_name} ({col_defs})')
        
        for _, row in df.iterrows():
            cols = ", ".join([f'"{c}"' for c in df.columns])
            vals = ", ".join([f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" if pd.notna(v) else "NULL" for v in row.values])
            cursor.execute(f"INSERT INTO RAW.{table_name} ({cols}) VALUES ({vals})")
        
        print(f"  Loaded {table_name} successfully")

cursor.close()
conn.close()
print("Raw data loading complete!")
EOF
    
    deactivate
}

step_4_run_dbt() {
    echo ""
    echo "Step 4: Running dbt transformations..."
    echo "---------------------------------------"
    
    cd "$BASE_DIR/dbt"
    source ../venv/bin/activate
    
    export DBT_PROFILES_DIR="$BASE_DIR/dbt"
    
    echo "Installing dbt dependencies..."
    dbt deps || true
    
    echo "Running dbt models..."
    dbt run --profiles-dir . || {
        echo "WARNING: dbt run failed. Check your Snowflake connection."
    }
    
    echo "Running dbt tests..."
    dbt test --profiles-dir . || {
        echo "WARNING: Some dbt tests failed."
    }
    
    deactivate
    echo "dbt transformations complete!"
}

step_5_validate() {
    echo ""
    echo "Step 5: Validating deployment..."
    echo "---------------------------------"
    
    cd "$BASE_DIR"
    source venv/bin/activate
    
    python3 << 'EOF'
import os
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

print("\nData Quality Summary:")
print("=" * 50)

for schema in schemas:
    try:
        cursor.execute(f"SHOW TABLES IN SCHEMA {schema}")
        tables = cursor.fetchall()
        print(f"\nSchema: {schema}")
        for table in tables:
            table_name = table[1]
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count:,} rows")
    except Exception as e:
        print(f"\nSchema: {schema} - Error: {e}")

cursor.close()
conn.close()
EOF
    
    deactivate
}

main() {
    echo "Starting deployment at $(date)"
    echo ""
    
    load_env
    check_env_vars
    
    step_1_generate_data
    step_2_setup_snowflake
    step_3_load_raw_data
    step_4_run_dbt
    step_5_validate
    
    echo ""
    echo "=============================================="
    echo "Deployment Complete!"
    echo "=============================================="
    echo "Finished at $(date)"
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: $0 [step]"
    echo ""
    echo "Steps:"
    echo "  1 - Generate synthetic data"
    echo "  2 - Setup Snowflake infrastructure"
    echo "  3 - Load raw data to Snowflake"
    echo "  4 - Run dbt transformations"
    echo "  5 - Validate deployment"
    echo ""
    echo "Run without arguments to execute all steps."
    exit 0
fi

if [ -n "${1:-}" ]; then
    load_env
    check_env_vars
    case "$1" in
        1) step_1_generate_data ;;
        2) step_2_setup_snowflake ;;
        3) step_3_load_raw_data ;;
        4) step_4_run_dbt ;;
        5) step_5_validate ;;
        *) echo "Unknown step: $1"; exit 1 ;;
    esac
else
    main
fi
