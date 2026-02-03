"""
Data Loader for Snowflake

This module loads CSV data from the data/raw directory into Snowflake RAW schema tables.
It creates the necessary tables and uses COPY INTO for efficient bulk loading.
"""

import os
import sys
import logging
from typing import Optional

import pandas as pd
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from python.utils.snowflake_client import (
    snowflake_connection,
    SnowflakeConnectionError,
)


logger = logging.getLogger(__name__)


def setup_logging(config: dict) -> None:
    """Configure logging based on config settings."""
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_file = log_config.get("file", "logs/insurance_platform.log")
    log_path = os.path.join(base_dir, log_file)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path)
        ]
    )


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config.yaml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# Table definitions for RAW schema
TABLE_DEFINITIONS = {
    "RAW_QUOTES": """
        CREATE TABLE IF NOT EXISTS RAW_QUOTES (
            quote_id INTEGER,
            quote_number VARCHAR(20),
            customer_id INTEGER,
            quote_date DATE,
            product VARCHAR(50),
            channel VARCHAR(50),
            risk_score FLOAT,
            premium_quoted FLOAT,
            quote_status VARCHAR(20),
            loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """,
    "RAW_POLICIES": """
        CREATE TABLE IF NOT EXISTS RAW_POLICIES (
            policy_id INTEGER,
            policy_number VARCHAR(20),
            quote_id INTEGER,
            customer_id INTEGER,
            product VARCHAR(50),
            inception_date DATE,
            expiry_date DATE,
            premium_written FLOAT,
            payment_frequency VARCHAR(20),
            policy_status VARCHAR(20),
            loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """,
    "RAW_CLAIMS": """
        CREATE TABLE IF NOT EXISTS RAW_CLAIMS (
            claim_id INTEGER,
            claim_number VARCHAR(20),
            policy_id INTEGER,
            customer_id INTEGER,
            loss_date DATE,
            report_date DATE,
            settlement_date DATE,
            claim_status VARCHAR(20),
            claim_cause VARCHAR(50),
            coverage_type VARCHAR(50),
            incurred_amount FLOAT,
            paid_amount FLOAT,
            reserve_amount FLOAT,
            loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """,
}


def create_tables(conn) -> None:
    """
    Create RAW tables in Snowflake if they don't exist.
    
    Args:
        conn: Snowflake connection object
    """
    cursor = conn.cursor()
    try:
        for table_name, create_sql in TABLE_DEFINITIONS.items():
            logger.info(f"Creating table {table_name} if not exists...")
            cursor.execute(create_sql)
            logger.info(f"Table {table_name} ready")
    finally:
        cursor.close()


def truncate_table(conn, table_name: str) -> None:
    """
    Truncate a table before loading new data.
    
    Args:
        conn: Snowflake connection object
        table_name: Name of table to truncate
    """
    cursor = conn.cursor()
    try:
        logger.info(f"Truncating table {table_name}...")
        cursor.execute(f"TRUNCATE TABLE IF EXISTS {table_name}")
        logger.info(f"Table {table_name} truncated")
    finally:
        cursor.close()


def load_csv_to_table(conn, csv_path: str, table_name: str, columns: list) -> int:
    """
    Load CSV data into a Snowflake table using pandas and executemany.
    
    Args:
        conn: Snowflake connection object
        csv_path: Path to CSV file
        table_name: Target table name
        columns: List of column names to load
        
    Returns:
        Number of rows loaded
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        Exception: If loading fails
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Loading {csv_path} into {table_name}...")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    if df.empty:
        logger.warning(f"CSV file {csv_path} is empty")
        return 0
    
    # Prepare data for insertion
    cursor = conn.cursor()
    try:
        # Build INSERT statement
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)
        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        # Convert DataFrame to list of tuples
        # Handle NaN values by converting to None
        df_subset = df[columns].copy()
        df_subset = df_subset.where(pd.notnull(df_subset), None)
        data = [tuple(row) for row in df_subset.values]
        
        # Execute batch insert
        cursor.executemany(insert_sql, data)
        
        row_count = len(data)
        logger.info(f"Loaded {row_count} rows into {table_name}")
        return row_count
        
    except Exception as e:
        logger.error(f"Failed to load data into {table_name}: {e}")
        raise
    finally:
        cursor.close()


def load_quotes(conn, config: dict) -> int:
    """Load quotes data to Snowflake."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    paths_config = config.get("paths", {})
    raw_data_dir = os.path.join(base_dir, paths_config.get("raw_data_dir", "data/raw"))
    quotes_subdir = paths_config.get("quotes_subdir", "quotes")
    csv_path = os.path.join(raw_data_dir, quotes_subdir, "quotes.csv")
    
    columns = [
        "quote_id", "quote_number", "customer_id", "quote_date",
        "product", "channel", "risk_score", "premium_quoted", "quote_status"
    ]
    
    return load_csv_to_table(conn, csv_path, "RAW_QUOTES", columns)


def load_policies(conn, config: dict) -> int:
    """Load policies data to Snowflake."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    paths_config = config.get("paths", {})
    raw_data_dir = os.path.join(base_dir, paths_config.get("raw_data_dir", "data/raw"))
    policies_subdir = paths_config.get("policies_subdir", "policies")
    csv_path = os.path.join(raw_data_dir, policies_subdir, "policies.csv")
    
    columns = [
        "policy_id", "policy_number", "quote_id", "customer_id", "product",
        "inception_date", "expiry_date", "premium_written", "payment_frequency", "policy_status"
    ]
    
    return load_csv_to_table(conn, csv_path, "RAW_POLICIES", columns)


def load_claims(conn, config: dict) -> int:
    """Load claims data to Snowflake."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    paths_config = config.get("paths", {})
    raw_data_dir = os.path.join(base_dir, paths_config.get("raw_data_dir", "data/raw"))
    claims_subdir = paths_config.get("claims_subdir", "claims")
    csv_path = os.path.join(raw_data_dir, claims_subdir, "claims.csv")
    
    columns = [
        "claim_id", "claim_number", "policy_id", "customer_id",
        "loss_date", "report_date", "settlement_date", "claim_status",
        "claim_cause", "coverage_type", "incurred_amount", "paid_amount", "reserve_amount"
    ]
    
    return load_csv_to_table(conn, csv_path, "RAW_CLAIMS", columns)


def main(config_path: Optional[str] = None, truncate: bool = True) -> dict:
    """
    Main entry point for data loading.
    
    Args:
        config_path: Optional path to configuration file
        truncate: Whether to truncate tables before loading (default: True)
        
    Returns:
        Dictionary with load statistics
        
    Raises:
        Exception: If loading fails
    """
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Setup logging
        setup_logging(config)
        
        logger.info("Starting data load to Snowflake")
        
        # Get retry settings from config
        snowflake_config = config.get("snowflake", {})
        max_retries = snowflake_config.get("max_retries", 3)
        retry_delay = snowflake_config.get("retry_delay_seconds", 5)
        
        with snowflake_connection(max_retries=max_retries, retry_delay=retry_delay) as conn:
            # Create tables
            create_tables(conn)
            
            # Optionally truncate tables
            if truncate:
                for table_name in TABLE_DEFINITIONS.keys():
                    truncate_table(conn, table_name)
            
            # Load data
            quotes_count = load_quotes(conn, config)
            policies_count = load_policies(conn, config)
            claims_count = load_claims(conn, config)
            
            logger.info("Data load completed successfully")
            
            return {
                "quotes_loaded": quotes_count,
                "policies_loaded": policies_count,
                "claims_loaded": claims_count,
            }
            
    except SnowflakeConnectionError as e:
        logger.error(f"Snowflake connection failed: {e}")
        raise
    except FileNotFoundError as e:
        logger.error(f"Data file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Data load failed: {e}")
        raise


if __name__ == "__main__":
    result = main()
    print(f"Data load complete:")
    print(f"  Quotes loaded: {result['quotes_loaded']}")
    print(f"  Policies loaded: {result['policies_loaded']}")
    print(f"  Claims loaded: {result['claims_loaded']}")
