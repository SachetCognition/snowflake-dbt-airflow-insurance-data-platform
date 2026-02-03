"""
Snowflake Connection Utility

This module provides a robust Snowflake connection with error handling and retry logic.
"""

import os
import logging
import time
from typing import Optional
from contextlib import contextmanager

import snowflake.connector
from snowflake.connector.errors import (
    DatabaseError,
    OperationalError,
    ProgrammingError,
    InterfaceError,
)


logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5  # seconds


class SnowflakeConnectionError(Exception):
    """Custom exception for Snowflake connection failures."""
    pass


def get_connection_params() -> dict:
    """
    Get Snowflake connection parameters from environment variables.
    
    Returns:
        Dictionary of connection parameters
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return {
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }


def get_snowflake_connection(
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
) -> snowflake.connector.SnowflakeConnection:
    """
    Create a Snowflake connection with retry logic.
    
    Args:
        max_retries: Maximum number of connection attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 5)
        
    Returns:
        Snowflake connection object
        
    Raises:
        SnowflakeConnectionError: If connection fails after all retries
        ValueError: If required environment variables are missing
    """
    max_retries = max_retries or DEFAULT_MAX_RETRIES
    retry_delay = retry_delay or DEFAULT_RETRY_DELAY
    
    # Get connection parameters
    try:
        params = get_connection_params()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting Snowflake connection (attempt {attempt}/{max_retries})")
            
            conn = snowflake.connector.connect(**params)
            
            # Verify connection is working
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            
            logger.info(f"Successfully connected to Snowflake (version: {version})")
            return conn
            
        except (DatabaseError, OperationalError, InterfaceError) as e:
            last_exception = e
            logger.warning(f"Connection attempt {attempt} failed: {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} connection attempts failed")
                
        except ProgrammingError as e:
            # Programming errors are usually not transient, don't retry
            logger.error(f"Snowflake programming error: {e}")
            raise SnowflakeConnectionError(f"Snowflake configuration error: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            raise SnowflakeConnectionError(f"Unexpected connection error: {e}") from e
    
    raise SnowflakeConnectionError(
        f"Failed to connect to Snowflake after {max_retries} attempts. "
        f"Last error: {last_exception}"
    )


@contextmanager
def snowflake_connection(
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
):
    """
    Context manager for Snowflake connections.
    
    Automatically handles connection cleanup.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Yields:
        Snowflake connection object
        
    Example:
        with snowflake_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM my_table")
    """
    conn = None
    try:
        conn = get_snowflake_connection(max_retries, retry_delay)
        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    fetch: bool = True,
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
) -> Optional[list]:
    """
    Execute a query with automatic connection management.
    
    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        fetch: Whether to fetch and return results (default: True)
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Query results if fetch=True, None otherwise
        
    Raises:
        SnowflakeConnectionError: If connection fails
        ProgrammingError: If query execution fails
    """
    with snowflake_connection(max_retries, retry_delay) as conn:
        cursor = conn.cursor()
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                results = cursor.fetchall()
                logger.debug(f"Query returned {len(results)} rows")
                return results
            else:
                logger.debug("Query executed successfully")
                return None
                
        finally:
            cursor.close()


def test_connection() -> bool:
    """
    Test Snowflake connection.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with snowflake_connection(max_retries=1) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
