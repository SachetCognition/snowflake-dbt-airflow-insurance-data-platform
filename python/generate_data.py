import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

def ensure_dirs():
    for sub in ["quotes", "policies", "claims"]:
        path = os.path.join(RAW_DATA_DIR, sub)
        os.makedirs(path, exist_ok=True)

def main():
    ensure_dirs()
    # Temporary stub: create tiny example CSVs
    quotes_path = os.path.join(RAW_DATA_DIR, "quotes", "quotes_sample.csv")
    policies_path = os.path.join(RAW_DATA_DIR, "policies", "policies_sample.csv")
    claims_path = os.path.join(RAW_DATA_DIR, "claims", "claims_sample.csv")

    pd.DataFrame({"quote_id": [1], "customer_id": [100], "premium": [500.0]}).to_csv(quotes_path, index=False)
    pd.DataFrame({"policy_id": [10], "customer_id": [100], "product": ["Motor"]}).to_csv(policies_path, index=False)
    pd.DataFrame({"claim_id": [1000], "policy_id": [10], "claim_amount": [2000.0]}).to_csv(claims_path, index=False)

    print("Sample raw data generated in data/raw/*")

if __name__ == "__main__":
    main()
