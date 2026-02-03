"""
Synthetic Insurance Data Generator

This module generates synthetic insurance data for quotes, policies, and claims.
It reads configuration from config.yaml and outputs CSV files to the data/raw directory.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yaml


# Set up module-level logger
logger = logging.getLogger(__name__)


def setup_logging(config: dict) -> None:
    """Configure logging based on config settings."""
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Create logs directory if it doesn't exist
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_file = log_config.get("file", "logs/insurance_platform.log")
    log_path = os.path.join(base_dir, log_file)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path)
        ]
    )
    logger.info("Logging configured successfully")


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default location.
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config.yaml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse configuration file: {e}")
        raise


def ensure_dirs(config: dict) -> str:
    """
    Create necessary directories for data output.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Path to raw data directory
        
    Raises:
        OSError: If directory creation fails
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    paths_config = config.get("paths", {})
    raw_data_dir = os.path.join(base_dir, paths_config.get("raw_data_dir", "data/raw"))
    
    subdirs = [
        paths_config.get("quotes_subdir", "quotes"),
        paths_config.get("policies_subdir", "policies"),
        paths_config.get("claims_subdir", "claims")
    ]
    
    try:
        for sub in subdirs:
            path = os.path.join(raw_data_dir, sub)
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Directory ensured: {path}")
        return raw_data_dir
    except OSError as e:
        logger.error(f"Failed to create directories: {e}")
        raise


def random_dates(start_date: datetime, end_date: datetime, n: int, rng: np.random.Generator) -> list:
    """
    Generate n random dates between start_date and end_date.
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        n: Number of dates to generate
        rng: NumPy random generator
        
    Returns:
        List of datetime objects
    """
    delta = (end_date - start_date).days
    offsets = rng.integers(0, delta + 1, size=n)
    return [start_date + timedelta(days=int(o)) for o in offsets]


def generate_quotes(config: dict, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate synthetic quotes data.
    
    Args:
        config: Configuration dictionary
        rng: NumPy random generator
        
    Returns:
        DataFrame containing quotes data
        
    Raises:
        ValueError: If generated data is invalid
    """
    gen_config = config.get("data_generation", {})
    n_customers = gen_config.get("n_customers", 2000)
    n_quotes = gen_config.get("n_quotes", 5000)
    conversion_rate = gen_config.get("conversion_rate", 0.4)
    
    logger.info(f"Generating {n_quotes} quotes for {n_customers} customers")
    
    customer_ids = rng.integers(1, n_customers + 1, size=n_quotes)
    quote_ids = np.arange(1, n_quotes + 1)

    # Date range for quotes
    start_date_str = gen_config.get("quote_start_date", "2022-01-01")
    end_date_str = gen_config.get("quote_end_date", "2024-12-31")
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    quote_dates = random_dates(start_date, end_date, n_quotes, rng)

    # Product distribution
    product_dist = gen_config.get("product_distribution", {"Motor": 0.6, "Home": 0.25, "Travel": 0.15})
    products_list = list(product_dist.keys())
    products_probs = list(product_dist.values())
    products = rng.choice(products_list, size=n_quotes, p=products_probs)
    
    # Channel distribution
    channel_dist = gen_config.get("channel_distribution", {"Online": 0.5, "Agent": 0.3, "Broker": 0.2})
    channels_list = list(channel_dist.keys())
    channels_probs = list(channel_dist.values())
    channels = rng.choice(channels_list, size=n_quotes, p=channels_probs)

    # Risk score between 0 and 1 using beta distribution (more low-risk than high-risk)
    risk_scores = rng.beta(a=2, b=5, size=n_quotes)

    # Premium quoted depends on product and risk
    base_premium = np.where(
        products == "Motor",
        400,
        np.where(products == "Home", 300, 150)
    )
    premium_quoted = base_premium * (0.6 + 1.2 * risk_scores)

    # Quote status: some bound, some declined, some expired
    # Adjust probabilities to ensure they sum to 1
    decline_rate = (1 - conversion_rate) / 2
    expire_rate = (1 - conversion_rate) / 2
    quote_status = rng.choice(
        ["BOUND", "DECLINED", "EXPIRED"],
        size=n_quotes,
        p=[conversion_rate, decline_rate, expire_rate],
    )

    df_quotes = pd.DataFrame({
        "quote_id": quote_ids,
        "quote_number": [f"Q-{q:06d}" for q in quote_ids],
        "customer_id": customer_ids,
        "quote_date": quote_dates,
        "product": products,
        "channel": channels,
        "risk_score": risk_scores.round(4),
        "premium_quoted": premium_quoted.round(2),
        "quote_status": quote_status,
    })

    # Validate generated data
    if df_quotes.empty:
        raise ValueError("Generated quotes DataFrame is empty")
    
    if df_quotes["quote_id"].isna().any():
        raise ValueError("Generated quotes contain null quote_ids")
    
    logger.info(f"Generated {len(df_quotes)} quotes successfully")
    return df_quotes


def generate_policies(df_quotes: pd.DataFrame, config: dict, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate synthetic policies data from bound quotes.
    
    Args:
        df_quotes: DataFrame containing quotes data
        config: Configuration dictionary
        rng: NumPy random generator
        
    Returns:
        DataFrame containing policies data
        
    Raises:
        ValueError: If generated data is invalid
    """
    # Keep only quotes that are BOUND
    df_bound = df_quotes[df_quotes["quote_status"] == "BOUND"].copy()
    df_bound = df_bound.reset_index(drop=True)

    n_policies = len(df_bound)
    logger.info(f"Generating {n_policies} policies from bound quotes")
    
    if n_policies == 0:
        logger.warning("No bound quotes found - returning empty policies DataFrame")
        return pd.DataFrame(columns=[
            "policy_id", "policy_number", "quote_id", "customer_id", "product",
            "inception_date", "expiry_date", "premium_written", "payment_frequency", "policy_status"
        ])
    
    policy_ids = np.arange(1, n_policies + 1)

    # Inception is on or shortly after quote_date
    inception_offsets = rng.integers(0, 30, size=n_policies)
    inception_dates = [
        qd + timedelta(days=int(offset))
        for qd, offset in zip(df_bound["quote_date"], inception_offsets)
    ]

    # 1-year policies
    expiry_dates = [inc + timedelta(days=365) for inc in inception_dates]

    payment_frequency = rng.choice(["ANNUAL", "MONTHLY"], size=n_policies, p=[0.7, 0.3])

    # Premium written = premium quoted +/- small adjustment
    adjustments = rng.normal(loc=1.0, scale=0.1, size=n_policies)
    premium_written = df_bound["premium_quoted"].values * adjustments

    # Policy status
    policy_status = rng.choice(
        ["ACTIVE", "LAPSED", "CANCELLED"],
        size=n_policies,
        p=[0.8, 0.1, 0.1],
    )

    df_policies = pd.DataFrame({
        "policy_id": policy_ids,
        "policy_number": [f"P-{p:06d}" for p in policy_ids],
        "quote_id": df_bound["quote_id"].values,
        "customer_id": df_bound["customer_id"].values,
        "product": df_bound["product"].values,
        "inception_date": inception_dates,
        "expiry_date": expiry_dates,
        "premium_written": premium_written.round(2),
        "payment_frequency": payment_frequency,
        "policy_status": policy_status,
    })

    # Validate generated data
    if df_policies.empty:
        raise ValueError("Generated policies DataFrame is empty")
    
    if df_policies["policy_id"].isna().any():
        raise ValueError("Generated policies contain null policy_ids")
    
    logger.info(f"Generated {len(df_policies)} policies successfully")
    return df_policies


def generate_claims(df_policies: pd.DataFrame, config: dict, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate synthetic claims data for policies.
    
    Args:
        df_policies: DataFrame containing policies data
        config: Configuration dictionary
        rng: NumPy random generator
        
    Returns:
        DataFrame containing claims data
    """
    gen_config = config.get("data_generation", {})
    max_claims = gen_config.get("max_claims_per_policy", 3)
    claims_dist = gen_config.get("claims_distribution", [0.6, 0.25, 0.1, 0.05])
    
    logger.info(f"Generating claims for {len(df_policies)} policies")
    
    claims_rows = []
    claim_causes = ["Collision", "Theft", "Fire", "Weather", "Other"]
    coverage_types = ["Third Party", "Comprehensive"]

    for _, row in df_policies.iterrows():
        policy_id = row["policy_id"]
        customer_id = row["customer_id"]
        inception_date = row["inception_date"]
        expiry_date = row["expiry_date"]
        product = row["product"]

        # Decide how many claims for this policy
        n_claims = rng.choice(
            np.arange(0, max_claims + 1),
            p=claims_dist
        )

        if n_claims == 0:
            continue

        loss_dates = random_dates(inception_date, expiry_date, n_claims, rng)

        for i in range(n_claims):
            loss_date = loss_dates[i]
            # report within 0-30 days
            report_date = loss_date + timedelta(days=int(rng.integers(0, 31)))

            # some claims settle within 0-180 days, some stay open
            if rng.random() < 0.7:
                settlement_date = report_date + timedelta(days=int(rng.integers(0, 181)))
                claim_status = "CLOSED"
            else:
                settlement_date = None
                claim_status = rng.choice(["OPEN", "REJECTED"], p=[0.8, 0.2])

            cause = rng.choice(claim_causes)
            coverage = rng.choice(coverage_types)

            # Incurred amount depends on product
            if product == "Motor":
                base = rng.normal(3000, 1500)
            elif product == "Home":
                base = rng.normal(5000, 3000)
            else:  # Travel
                base = rng.normal(800, 400)

            incurred = max(0, base)
            # Paid is up to incurred
            paid = incurred * rng.uniform(0.2, 1.0)
            reserve = max(0, incurred - paid)

            claims_rows.append({
                "policy_id": policy_id,
                "customer_id": customer_id,
                "loss_date": loss_date,
                "report_date": report_date,
                "settlement_date": settlement_date,
                "claim_status": claim_status,
                "claim_cause": cause,
                "coverage_type": coverage,
                "incurred_amount": round(incurred, 2),
                "paid_amount": round(paid, 2),
                "reserve_amount": round(reserve, 2),
            })

    if not claims_rows:
        logger.warning("No claims generated - all policies have zero claims")
        return pd.DataFrame(columns=[
            "claim_id", "policy_id", "customer_id", "claim_number",
            "loss_date", "report_date", "settlement_date", "claim_status",
            "claim_cause", "coverage_type", "incurred_amount", "paid_amount", "reserve_amount",
        ])

    df_claims = pd.DataFrame(claims_rows)
    df_claims.insert(0, "claim_id", np.arange(1, len(df_claims) + 1))
    df_claims.insert(1, "claim_number", [f"C-{c:06d}" for c in df_claims["claim_id"]])

    logger.info(f"Generated {len(df_claims)} claims successfully")
    return df_claims


def save_dataframe(df: pd.DataFrame, file_path: str, entity_name: str) -> None:
    """
    Save DataFrame to CSV file with error handling.
    
    Args:
        df: DataFrame to save
        file_path: Path to output file
        entity_name: Name of entity for logging
        
    Raises:
        IOError: If file writing fails
        ValueError: If DataFrame is empty
    """
    if df.empty:
        logger.warning(f"{entity_name} DataFrame is empty - saving empty file")
    
    try:
        df.to_csv(file_path, index=False)
        logger.info(f"Saved {len(df)} {entity_name} records to {file_path}")
    except IOError as e:
        logger.error(f"Failed to save {entity_name} to {file_path}: {e}")
        raise


def main(config_path: Optional[str] = None) -> dict:
    """
    Main entry point for data generation.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Dictionary with paths to generated files
        
    Raises:
        Exception: If data generation fails
    """
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Setup logging
        setup_logging(config)
        
        logger.info("Starting synthetic data generation")
        
        # Ensure directories exist
        raw_data_dir = ensure_dirs(config)
        
        # Initialize random generator with seed
        gen_config = config.get("data_generation", {})
        rng_seed = gen_config.get("rng_seed", 42)
        rng = np.random.default_rng(rng_seed)
        logger.info(f"Random generator initialized with seed {rng_seed}")

        # Generate data
        df_quotes = generate_quotes(config, rng)
        df_policies = generate_policies(df_quotes, config, rng)
        df_claims = generate_claims(df_policies, config, rng)

        # Get paths from config
        paths_config = config.get("paths", {})
        quotes_subdir = paths_config.get("quotes_subdir", "quotes")
        policies_subdir = paths_config.get("policies_subdir", "policies")
        claims_subdir = paths_config.get("claims_subdir", "claims")
        
        # Save CSVs
        quotes_path = os.path.join(raw_data_dir, quotes_subdir, "quotes.csv")
        policies_path = os.path.join(raw_data_dir, policies_subdir, "policies.csv")
        claims_path = os.path.join(raw_data_dir, claims_subdir, "claims.csv")

        save_dataframe(df_quotes, quotes_path, "quotes")
        save_dataframe(df_policies, policies_path, "policies")
        save_dataframe(df_claims, claims_path, "claims")

        logger.info("Data generation completed successfully")
        
        return {
            "quotes_path": quotes_path,
            "policies_path": policies_path,
            "claims_path": claims_path,
            "quotes_count": len(df_quotes),
            "policies_count": len(df_policies),
            "claims_count": len(df_claims),
        }
        
    except Exception as e:
        logger.error(f"Data generation failed: {e}")
        raise


if __name__ == "__main__":
    result = main()
    print(f"Data generation complete:")
    print(f"  Quotes: {result['quotes_count']} records -> {result['quotes_path']}")
    print(f"  Policies: {result['policies_count']} records -> {result['policies_path']}")
    print(f"  Claims: {result['claims_count']} records -> {result['claims_path']}")
