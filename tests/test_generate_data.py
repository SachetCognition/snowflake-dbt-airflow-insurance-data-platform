"""
Unit tests for the data generation module.

Tests cover:
- Quote generation with expected record counts
- Policy generation respecting conversion rate
- Claims generation with valid data
- Configuration loading
"""

import os
import sys
import tempfile
import pytest
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from python.generate_data import (
    generate_quotes,
    generate_policies,
    generate_claims,
    load_config,
    random_dates,
)


@pytest.fixture
def test_config():
    """Provide a test configuration."""
    return {
        "data_generation": {
            "n_customers": 100,
            "n_quotes": 250,
            "conversion_rate": 0.4,
            "max_claims_per_policy": 3,
            "rng_seed": 42,
            "quote_start_date": "2022-01-01",
            "quote_end_date": "2024-12-31",
            "product_distribution": {"Motor": 0.6, "Home": 0.25, "Travel": 0.15},
            "channel_distribution": {"Online": 0.5, "Agent": 0.3, "Broker": 0.2},
            "claims_distribution": [0.6, 0.25, 0.1, 0.05],
        },
        "paths": {
            "raw_data_dir": "data/raw",
            "quotes_subdir": "quotes",
            "policies_subdir": "policies",
            "claims_subdir": "claims",
        },
        "logging": {
            "level": "INFO",
            "file": "logs/test.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }


@pytest.fixture
def rng():
    """Provide a seeded random number generator."""
    return np.random.default_rng(42)


class TestGenerateQuotes:
    """Tests for the generate_quotes function."""

    def test_generates_expected_number_of_quotes(self, test_config, rng):
        """Test that generate_quotes produces the expected number of records."""
        df_quotes = generate_quotes(test_config, rng)
        
        expected_count = test_config["data_generation"]["n_quotes"]
        assert len(df_quotes) == expected_count, (
            f"Expected {expected_count} quotes, got {len(df_quotes)}"
        )

    def test_quote_ids_are_unique(self, test_config, rng):
        """Test that all quote IDs are unique."""
        df_quotes = generate_quotes(test_config, rng)
        
        assert df_quotes["quote_id"].is_unique, "Quote IDs should be unique"

    def test_quote_ids_are_sequential(self, test_config, rng):
        """Test that quote IDs are sequential starting from 1."""
        df_quotes = generate_quotes(test_config, rng)
        
        expected_ids = list(range(1, len(df_quotes) + 1))
        actual_ids = df_quotes["quote_id"].tolist()
        assert actual_ids == expected_ids, "Quote IDs should be sequential from 1"

    def test_customer_ids_are_within_range(self, test_config, rng):
        """Test that customer IDs are within the expected range."""
        df_quotes = generate_quotes(test_config, rng)
        
        n_customers = test_config["data_generation"]["n_customers"]
        assert df_quotes["customer_id"].min() >= 1, "Customer IDs should be >= 1"
        assert df_quotes["customer_id"].max() <= n_customers, (
            f"Customer IDs should be <= {n_customers}"
        )

    def test_products_are_valid(self, test_config, rng):
        """Test that all products are from the expected set."""
        df_quotes = generate_quotes(test_config, rng)
        
        valid_products = set(test_config["data_generation"]["product_distribution"].keys())
        actual_products = set(df_quotes["product"].unique())
        assert actual_products.issubset(valid_products), (
            f"Invalid products found: {actual_products - valid_products}"
        )

    def test_channels_are_valid(self, test_config, rng):
        """Test that all channels are from the expected set."""
        df_quotes = generate_quotes(test_config, rng)
        
        valid_channels = set(test_config["data_generation"]["channel_distribution"].keys())
        actual_channels = set(df_quotes["channel"].unique())
        assert actual_channels.issubset(valid_channels), (
            f"Invalid channels found: {actual_channels - valid_channels}"
        )

    def test_quote_status_values_are_valid(self, test_config, rng):
        """Test that quote status values are valid."""
        df_quotes = generate_quotes(test_config, rng)
        
        valid_statuses = {"BOUND", "DECLINED", "EXPIRED"}
        actual_statuses = set(df_quotes["quote_status"].unique())
        assert actual_statuses.issubset(valid_statuses), (
            f"Invalid statuses found: {actual_statuses - valid_statuses}"
        )

    def test_risk_scores_are_in_valid_range(self, test_config, rng):
        """Test that risk scores are between 0 and 1."""
        df_quotes = generate_quotes(test_config, rng)
        
        assert df_quotes["risk_score"].min() >= 0, "Risk scores should be >= 0"
        assert df_quotes["risk_score"].max() <= 1, "Risk scores should be <= 1"

    def test_premium_quoted_is_positive(self, test_config, rng):
        """Test that all quoted premiums are positive."""
        df_quotes = generate_quotes(test_config, rng)
        
        assert (df_quotes["premium_quoted"] > 0).all(), "All premiums should be positive"

    def test_conversion_rate_approximately_correct(self, test_config, rng):
        """Test that the conversion rate is approximately as configured."""
        df_quotes = generate_quotes(test_config, rng)
        
        expected_rate = test_config["data_generation"]["conversion_rate"]
        actual_rate = (df_quotes["quote_status"] == "BOUND").mean()
        
        # Allow 10% tolerance due to randomness
        tolerance = 0.1
        assert abs(actual_rate - expected_rate) < tolerance, (
            f"Conversion rate {actual_rate:.2f} differs from expected {expected_rate:.2f}"
        )


class TestGeneratePolicies:
    """Tests for the generate_policies function."""

    def test_policies_only_from_bound_quotes(self, test_config, rng):
        """Test that policies are only created from BOUND quotes."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        bound_quote_ids = set(df_quotes[df_quotes["quote_status"] == "BOUND"]["quote_id"])
        policy_quote_ids = set(df_policies["quote_id"])
        
        assert policy_quote_ids.issubset(bound_quote_ids), (
            "All policy quote_ids should be from BOUND quotes"
        )

    def test_policy_count_matches_bound_quotes(self, test_config, rng):
        """Test that the number of policies matches the number of BOUND quotes."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        bound_count = (df_quotes["quote_status"] == "BOUND").sum()
        assert len(df_policies) == bound_count, (
            f"Expected {bound_count} policies, got {len(df_policies)}"
        )

    def test_policy_ids_are_unique(self, test_config, rng):
        """Test that all policy IDs are unique."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        assert df_policies["policy_id"].is_unique, "Policy IDs should be unique"

    def test_inception_date_after_quote_date(self, test_config, rng):
        """Test that inception dates are on or after quote dates."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        # Merge to get quote dates
        merged = df_policies.merge(
            df_quotes[["quote_id", "quote_date"]], 
            on="quote_id", 
            suffixes=("", "_quote")
        )
        
        assert (merged["inception_date"] >= merged["quote_date"]).all(), (
            "Inception dates should be >= quote dates"
        )

    def test_expiry_date_after_inception_date(self, test_config, rng):
        """Test that expiry dates are after inception dates."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        assert (df_policies["expiry_date"] > df_policies["inception_date"]).all(), (
            "Expiry dates should be > inception dates"
        )

    def test_policy_status_values_are_valid(self, test_config, rng):
        """Test that policy status values are valid."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        valid_statuses = {"ACTIVE", "LAPSED", "CANCELLED"}
        actual_statuses = set(df_policies["policy_status"].unique())
        assert actual_statuses.issubset(valid_statuses), (
            f"Invalid statuses found: {actual_statuses - valid_statuses}"
        )

    def test_premium_written_is_positive(self, test_config, rng):
        """Test that all written premiums are positive."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        
        assert (df_policies["premium_written"] > 0).all(), "All premiums should be positive"


class TestGenerateClaims:
    """Tests for the generate_claims function."""

    def test_claims_reference_valid_policies(self, test_config, rng):
        """Test that all claims reference valid policy IDs."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            valid_policy_ids = set(df_policies["policy_id"])
            claim_policy_ids = set(df_claims["policy_id"])
            assert claim_policy_ids.issubset(valid_policy_ids), (
                "All claim policy_ids should reference valid policies"
            )

    def test_claim_ids_are_unique(self, test_config, rng):
        """Test that all claim IDs are unique."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            assert df_claims["claim_id"].is_unique, "Claim IDs should be unique"

    def test_loss_date_within_policy_period(self, test_config, rng):
        """Test that loss dates are within the policy period."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            merged = df_claims.merge(
                df_policies[["policy_id", "inception_date", "expiry_date"]], 
                on="policy_id"
            )
            
            assert (merged["loss_date"] >= merged["inception_date"]).all(), (
                "Loss dates should be >= inception dates"
            )
            assert (merged["loss_date"] <= merged["expiry_date"]).all(), (
                "Loss dates should be <= expiry dates"
            )

    def test_report_date_after_loss_date(self, test_config, rng):
        """Test that report dates are on or after loss dates."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            assert (df_claims["report_date"] >= df_claims["loss_date"]).all(), (
                "Report dates should be >= loss dates"
            )

    def test_claim_amounts_are_non_negative(self, test_config, rng):
        """Test that all claim amounts are non-negative."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            assert (df_claims["incurred_amount"] >= 0).all(), "Incurred amounts should be >= 0"
            assert (df_claims["paid_amount"] >= 0).all(), "Paid amounts should be >= 0"
            assert (df_claims["reserve_amount"] >= 0).all(), "Reserve amounts should be >= 0"

    def test_claim_status_values_are_valid(self, test_config, rng):
        """Test that claim status values are valid."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        if len(df_claims) > 0:
            valid_statuses = {"OPEN", "CLOSED", "REJECTED"}
            actual_statuses = set(df_claims["claim_status"].unique())
            assert actual_statuses.issubset(valid_statuses), (
                f"Invalid statuses found: {actual_statuses - valid_statuses}"
            )

    def test_approximately_60_percent_policies_have_no_claims(self, test_config, rng):
        """Test that approximately 60% of policies have no claims."""
        df_quotes = generate_quotes(test_config, rng)
        df_policies = generate_policies(df_quotes, test_config, rng)
        df_claims = generate_claims(df_policies, test_config, rng)
        
        policies_with_claims = df_claims["policy_id"].nunique() if len(df_claims) > 0 else 0
        total_policies = len(df_policies)
        
        if total_policies > 0:
            no_claims_rate = 1 - (policies_with_claims / total_policies)
            expected_rate = test_config["data_generation"]["claims_distribution"][0]
            
            # Allow 15% tolerance due to randomness
            tolerance = 0.15
            assert abs(no_claims_rate - expected_rate) < tolerance, (
                f"No-claims rate {no_claims_rate:.2f} differs from expected {expected_rate:.2f}"
            )


class TestRandomDates:
    """Tests for the random_dates helper function."""

    def test_generates_correct_number_of_dates(self, rng):
        """Test that random_dates generates the correct number of dates."""
        from datetime import datetime
        
        start = datetime(2022, 1, 1)
        end = datetime(2022, 12, 31)
        n = 100
        
        dates = random_dates(start, end, n, rng)
        assert len(dates) == n, f"Expected {n} dates, got {len(dates)}"

    def test_dates_are_within_range(self, rng):
        """Test that all generated dates are within the specified range."""
        from datetime import datetime
        
        start = datetime(2022, 1, 1)
        end = datetime(2022, 12, 31)
        n = 100
        
        dates = random_dates(start, end, n, rng)
        
        for date in dates:
            assert start <= date <= end, f"Date {date} is outside range [{start}, {end}]"


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_config_raises_on_missing_file(self):
        """Test that load_config raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_config_returns_dict(self):
        """Test that load_config returns a dictionary."""
        # Create a temporary config file
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"test": "value"}, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            assert isinstance(config, dict), "Config should be a dictionary"
            assert config.get("test") == "value", "Config should contain expected values"
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
