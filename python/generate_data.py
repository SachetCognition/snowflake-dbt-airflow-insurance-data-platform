import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# -------------------------
# Config
# -------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

N_CUSTOMERS = 2000
N_QUOTES = 5000  # total quotes
CONVERSION_RATE = 0.4  # 40% of quotes become policies
MAX_CLAIMS_PER_POLICY = 3

# Fraud configuration
FRAUD_RATE = 0.05  # 5% of claims are fraudulent
FRAUD_CUSTOMER_RATE = 0.02  # 2% of customers are "fraud-prone"

RNG_SEED = 42


def ensure_dirs():
    for sub in ["quotes", "policies", "claims"]:
        path = os.path.join(RAW_DATA_DIR, sub)
        os.makedirs(path, exist_ok=True)


def random_dates(start_date, end_date, n, rng):
    """Generate n random dates between start_date and end_date."""
    delta = (end_date - start_date).days
    offsets = rng.integers(0, delta + 1, size=n)
    return [start_date + timedelta(days=int(o)) for o in offsets]


def generate_quotes(rng):
    customer_ids = rng.integers(1, N_CUSTOMERS + 1, size=N_QUOTES)
    quote_ids = np.arange(1, N_QUOTES + 1)

    # Date range for quotes
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)
    quote_dates = random_dates(start_date, end_date, N_QUOTES, rng)

    products = rng.choice(["Motor", "Home", "Travel"], size=N_QUOTES, p=[0.6, 0.25, 0.15])
    channels = rng.choice(["Online", "Agent", "Broker"], size=N_QUOTES, p=[0.5, 0.3, 0.2])

    # Risk score between 0 and 1
    risk_scores = rng.beta(a=2, b=5, size=N_QUOTES)  # more low-risk than high-risk

    # Premium quoted depends on product and risk
    base_premium = np.where(
        products == "Motor",
        400,
        np.where(products == "Home", 300, 150)
    )
    premium_quoted = base_premium * (0.6 + 1.2 * risk_scores)  # risk lifts premium

    # Quote status: some bound, some declined, some expired
    quote_status = rng.choice(
        ["BOUND", "DECLINED", "EXPIRED"],
        size=N_QUOTES,
        p=[CONVERSION_RATE, 0.3, 0.3],
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

    return df_quotes


def generate_policies(df_quotes, rng):
    # Keep only quotes that are BOUND
    df_bound = df_quotes[df_quotes["quote_status"] == "BOUND"].copy()
    df_bound = df_bound.reset_index(drop=True)

    n_policies = len(df_bound)
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

    return df_policies


def generate_fraud_prone_customers(rng):
    """Generate a set of customer IDs that are fraud-prone."""
    n_fraud_customers = int(N_CUSTOMERS * FRAUD_CUSTOMER_RATE)
    fraud_customer_ids = set(rng.choice(
        np.arange(1, N_CUSTOMERS + 1), 
        size=n_fraud_customers, 
        replace=False
    ))
    return fraud_customer_ids


def generate_claims(df_policies, rng, fraud_customer_ids=None):
    """Generate claims with fraud indicators.
    
    Fraud patterns implemented:
    1. Velocity fraud: Multiple claims in short time periods
    2. Amount fraud: Unusually high claim amounts
    3. Timing fraud: Claims shortly after policy inception
    4. Pattern fraud: Same claim cause repeatedly
    5. Quick reporting fraud: Same-day loss and report dates
    """
    if fraud_customer_ids is None:
        fraud_customer_ids = set()
    
    claims_rows = []

    claim_causes = ["Collision", "Theft", "Fire", "Weather", "Other"]
    coverage_types = ["Third Party", "Comprehensive"]

    for _, row in df_policies.iterrows():
        policy_id = row["policy_id"]
        customer_id = row["customer_id"]
        inception_date = row["inception_date"]
        expiry_date = row["expiry_date"]
        product = row["product"]
        
        is_fraud_customer = customer_id in fraud_customer_ids

        # Fraud-prone customers have more claims
        if is_fraud_customer:
            n_claims = rng.choice(
                np.arange(1, MAX_CLAIMS_PER_POLICY + 2),  # 1-4 claims
                p=[0.3, 0.3, 0.25, 0.15]
            )
        else:
            n_claims = rng.choice(
                np.arange(0, MAX_CLAIMS_PER_POLICY + 1),
                p=[0.6, 0.25, 0.1, 0.05]  # 60% have no claims, etc.
            )

        if n_claims == 0:
            continue

        # For fraud customers, cluster claims in short time periods (velocity fraud)
        if is_fraud_customer and n_claims > 1:
            # Claims within 60 days of each other
            first_loss = inception_date + timedelta(days=int(rng.integers(0, 60)))
            loss_dates = [first_loss + timedelta(days=int(rng.integers(0, 45))) for _ in range(n_claims)]
        else:
            loss_dates = random_dates(inception_date, expiry_date, n_claims, rng)
        
        # Fraud customers tend to use same claim cause (pattern fraud)
        preferred_cause = rng.choice(claim_causes) if is_fraud_customer else None

        for i in range(n_claims):
            loss_date = loss_dates[i]
            
            # Determine if this specific claim is fraudulent
            is_fraud = False
            fraud_indicators = []
            
            # Fraud-prone customers have higher chance of fraud
            if is_fraud_customer:
                is_fraud = rng.random() < 0.7  # 70% of fraud customer claims are fraudulent
            else:
                is_fraud = rng.random() < FRAUD_RATE  # 5% random fraud
            
            if is_fraud:
                # Quick reporting fraud: same day or next day
                report_date = loss_date + timedelta(days=int(rng.integers(0, 2)))
                fraud_indicators.append("QUICK_REPORT")
                
                # Timing fraud: claim within 30 days of inception
                if (loss_date - inception_date).days <= 30:
                    fraud_indicators.append("EARLY_CLAIM")
            else:
                # Normal reporting: 0-30 days
                report_date = loss_date + timedelta(days=int(rng.integers(0, 31)))

            # Settlement logic
            if rng.random() < 0.7:
                settlement_date = report_date + timedelta(days=int(rng.integers(0, 181)))
                claim_status = "CLOSED"
            else:
                settlement_date = None
                # Fraudulent claims more likely to be rejected
                if is_fraud:
                    claim_status = rng.choice(["OPEN", "REJECTED"], p=[0.5, 0.5])
                else:
                    claim_status = rng.choice(["OPEN", "REJECTED"], p=[0.8, 0.2])

            # Cause selection - fraud customers repeat same cause
            if is_fraud_customer and preferred_cause:
                cause = preferred_cause if rng.random() < 0.7 else rng.choice(claim_causes)
                if cause == preferred_cause:
                    fraud_indicators.append("REPEATED_CAUSE")
            else:
                cause = rng.choice(claim_causes)
            
            coverage = rng.choice(coverage_types)

            # Incurred amount - fraudulent claims tend to be higher
            if product == "Motor":
                base = rng.normal(3000, 1500)
            elif product == "Home":
                base = rng.normal(5000, 3000)
            else:  # Travel
                base = rng.normal(800, 400)

            # Amount fraud: inflate claim amounts
            if is_fraud:
                inflation_factor = rng.uniform(1.5, 3.0)  # 50-200% inflation
                base = base * inflation_factor
                fraud_indicators.append("HIGH_AMOUNT")

            incurred = max(0, base)
            paid = incurred * rng.uniform(0.2, 1.0)
            reserve = max(0, incurred - paid)
            
            # Calculate fraud score (0-100)
            fraud_score = 0
            if is_fraud:
                fraud_score = min(100, len(fraud_indicators) * 25 + rng.integers(10, 30))
            else:
                # Some legitimate claims may have suspicious patterns
                fraud_score = rng.integers(0, 20)

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
                "is_fraud": is_fraud,
                "fraud_score": fraud_score,
                "fraud_indicators": "|".join(fraud_indicators) if fraud_indicators else None,
            })

    if not claims_rows:
        return pd.DataFrame(columns=[
            "claim_id",
            "claim_number",
            "policy_id",
            "customer_id",
            "loss_date",
            "report_date",
            "settlement_date",
            "claim_status",
            "claim_cause",
            "coverage_type",
            "incurred_amount",
            "paid_amount",
            "reserve_amount",
            "is_fraud",
            "fraud_score",
            "fraud_indicators",
        ])

    df_claims = pd.DataFrame(claims_rows)
    df_claims.insert(0, "claim_id", np.arange(1, len(df_claims) + 1))
    df_claims.insert(1, "claim_number", [f"C-{c:06d}" for c in df_claims["claim_id"]])

    return df_claims


def main():
    ensure_dirs()
    rng = np.random.default_rng(RNG_SEED)

    print("Generating quotes...")
    df_quotes = generate_quotes(rng)
    print(f"Quotes generated: {len(df_quotes)}")

    print("Generating policies from bound quotes...")
    df_policies = generate_policies(df_quotes, rng)
    print(f"Policies generated: {len(df_policies)}")

    print("Generating fraud-prone customer profiles...")
    fraud_customer_ids = generate_fraud_prone_customers(rng)
    print(f"Fraud-prone customers: {len(fraud_customer_ids)}")

    print("Generating claims for policies (with fraud patterns)...")
    df_claims = generate_claims(df_policies, rng, fraud_customer_ids)
    print(f"Claims generated: {len(df_claims)}")
    
    # Print fraud statistics
    fraud_count = df_claims["is_fraud"].sum()
    fraud_rate = fraud_count / len(df_claims) * 100 if len(df_claims) > 0 else 0
    print(f"Fraudulent claims: {fraud_count} ({fraud_rate:.1f}%)")

    # Save CSVs
    quotes_path = os.path.join(RAW_DATA_DIR, "quotes", "quotes.csv")
    policies_path = os.path.join(RAW_DATA_DIR, "policies", "policies.csv")
    claims_path = os.path.join(RAW_DATA_DIR, "claims", "claims.csv")

    df_quotes.to_csv(quotes_path, index=False)
    df_policies.to_csv(policies_path, index=False)
    df_claims.to_csv(claims_path, index=False)

    print(f"Saved quotes to   {quotes_path}")
    print(f"Saved policies to {policies_path}")
    print(f"Saved claims to   {claims_path}")
    print("Done!")


if __name__ == "__main__":
    main()
