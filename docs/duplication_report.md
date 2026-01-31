# Insurance Data Platform - Duplication Report

## Overview

This report analyzes code duplication and logic overlap across the four insurance repositories, identifying similar implementations and highlighting differences in approach.

## 1. Data Generation Logic

### Files with Similar Logic

| Repository | File | Purpose |
|------------|------|---------|
| Repo 1 (NoSQL) | `data-generator/Simulator.py` | Continuous data generation (every 2 seconds) |
| Repo 2 (Airflow) | `python/generate_data.py` | Batch data generation (one-time) |

### Comparison

#### Customer/Claim Generation

**Repo 1 - Simulator.py (Lines 14-29):**
```python
customer = {
    "customer_id": f"CUST-{random.randint(100,999)}",
    "name": fake.name(),
    "state": fake.state_abbr(),
    "policy_type": random.choice(["Auto", "Home", "Health"])
}

claim = {
    "claim_id": f"CLM-{random.randint(1000,9999)}",
    "customer_id": customer["customer_id"],
    "date": fake.date_between(start_date='-1y', end_date='today').isoformat(),
    "amount": round(random.uniform(100, 20000), 2),
    "claim_type": random.choice(["Accident", "Theft", "Fire"]),
    "is_fraud": random.random() < 0.05
}
```

**Repo 2 - generate_data.py (Lines 125-190):**
```python
# More sophisticated claim generation with:
# - Policy linkage
# - Multiple claim causes
# - Coverage types
# - Incurred/Paid/Reserve breakdown
# - Settlement dates
```

#### Key Differences

| Aspect | Repo 1 | Repo 2 |
|--------|--------|--------|
| Generation Mode | Continuous (infinite loop) | Batch (one-time) |
| Customer Detail | Basic (name, state) | Referenced only |
| Claim Fields | 6 fields | 13 fields |
| Financial Detail | Single amount | Incurred/Paid/Reserve |
| Fraud Detection | 5% random flag | Not implemented |
| Policy Linkage | None | Full linkage |
| Reproducibility | Non-deterministic | Seeded RNG (seed=42) |

## 2. Fraud Flag Logic

### Implementation Locations

| Repository | File | Line | Implementation |
|------------|------|------|----------------|
| Repo 1 | `data-generator/Simulator.py` | 28 | `is_fraud: random.random() < 0.05` |
| Repo 2 | N/A | N/A | **NOT IMPLEMENTED** |
| Repo 3 | N/A | N/A | **NOT IMPLEMENTED** |
| Repo 4 | N/A | N/A | **NOT IMPLEMENTED** |

### Analysis

Only Repo 1 implements fraud detection, using a simple 5% random probability. This is a significant gap as fraud detection is a critical insurance use case. The implementation is simplistic and does not consider:
- Claim amount thresholds
- Customer history
- Claim patterns
- Geographic indicators

**Recommendation:** Implement fraud scoring in Repo 2's generate_data.py based on multiple factors.

## 3. Risk Score Logic

### Implementation Locations

| Repository | File | Line | Implementation |
|------------|------|------|----------------|
| Repo 1 | N/A | N/A | **NOT IMPLEMENTED** |
| Repo 2 | `python/generate_data.py` | 45-46 | Beta distribution |
| Repo 3 | `models/raw/cust_policy.sql` | 34 | RISKPROFILE (source field) |
| Repo 4 | N/A | N/A | **NOT IMPLEMENTED** |

### Repo 2 Implementation (Lines 45-54)

```python
# Risk score between 0 and 1
risk_scores = rng.beta(a=2, b=5, size=N_QUOTES)  # more low-risk than high-risk

# Premium quoted depends on product and risk
base_premium = np.where(
    products == "Motor",
    400,
    np.where(products == "Home", 300, 150)
)
premium_quoted = base_premium * (0.6 + 1.2 * risk_score)  # risk lifts premium
```

### Analysis

The Beta(2,5) distribution creates a right-skewed distribution favoring lower risk scores, which is realistic for insurance portfolios. The premium calculation applies a multiplier of 0.6 to 1.8 based on risk.

## 4. Claim Severity Logic

### Implementation Locations

| Repository | File | Lines | Implementation |
|------------|------|-------|----------------|
| Repo 1 | `data-generator/Simulator.py` | 26 | `random.uniform(100, 20000)` |
| Repo 2 | `python/generate_data.py` | 165-176 | Product-based normal distribution |

### Repo 2 Implementation (Lines 165-176)

```python
# Incurred amount depends on product
if product == "Motor":
    base = rng.normal(3000, 1500)
elif product == "Home":
    base = rng.normal(5000, 3000)
else:  # Travel
    base = rng.normal(800, 400)

incurred = max(0, base)
paid = incurred * rng.uniform(0.2, 1.0)
reserve = max(0, incurred - paid)
```

### Comparison

| Aspect | Repo 1 | Repo 2 |
|--------|--------|--------|
| Distribution | Uniform | Normal (product-based) |
| Range | $100 - $20,000 | Product-dependent |
| Motor Average | ~$10,000 | ~$3,000 |
| Home Average | ~$10,000 | ~$5,000 |
| Travel Average | ~$10,000 | ~$800 |
| Paid/Reserve Split | N/A | 20-100% paid |

## 5. Loss Ratio Definitions

### Implementation Locations

| Repository | File | Implementation |
|------------|------|----------------|
| Repo 2 | `python/generate_data.py` | Lines 165-189 |
| Repo 2 | `dbt/models/marts/mart_loss_ratio_by_segment.sql` | Full implementation |

### Formula

```
Loss Ratio = Incurred Claims / Earned Premium
           = (Paid Amount + Reserve Amount) / Premium Written
```

### Repo 2 dbt Implementation

```sql
case
    when sum(ps.premium_written) > 0 
    then round(coalesce(sum(pc.incurred_amount), 0) / sum(ps.premium_written), 4)
    else 0
end as loss_ratio
```

### Gaps

- **Repo 1:** No loss ratio calculation
- **Repo 3:** No loss ratio calculation (only premium aggregation)
- **Repo 4:** No loss ratio calculation

## 6. Status/State Machine Logic

### Claim Status

| Repository | File | Statuses | Logic |
|------------|------|----------|-------|
| Repo 1 | N/A | N/A | **NOT IMPLEMENTED** |
| Repo 2 | `generate_data.py:154-160` | OPEN, CLOSED, REJECTED | Probabilistic |

**Repo 2 Implementation (Lines 154-160):**
```python
if rng.random() < 0.7:
    settlement_date = report_date + timedelta(days=int(rng.integers(0, 181)))
    claim_status = "CLOSED"
else:
    settlement_date = None
    claim_status = rng.choice(["OPEN", "REJECTED"], p=[0.8, 0.2])
```

**Missing Statuses:**
- REOPENED
- SUBROGATION
- LITIGATION
- UNDER_REVIEW

### Policy Status

| Repository | File | Statuses | Logic |
|------------|------|----------|-------|
| Repo 2 | `generate_data.py:103-107` | ACTIVE, LAPSED, CANCELLED | Probabilistic |

**Repo 2 Implementation (Lines 103-107):**
```python
policy_status = rng.choice(
    ["ACTIVE", "LAPSED", "CANCELLED"],
    size=n_policies,
    p=[0.8, 0.1, 0.1],
)
```

### Quote Status

| Repository | File | Statuses | Logic |
|------------|------|----------|-------|
| Repo 2 | `generate_data.py:56-61` | BOUND, DECLINED, EXPIRED | Probabilistic |

**Repo 2 Implementation (Lines 56-61):**
```python
quote_status = rng.choice(
    ["BOUND", "DECLINED", "EXPIRED"],
    size=N_QUOTES,
    p=[CONVERSION_RATE, 0.3, 0.3],  # 40% conversion
)
```

## 7. SCD (Slowly Changing Dimension) Logic

### Critical Finding

**NO SCD IMPLEMENTATIONS EXIST IN ANY REPOSITORY**

| Repository | Documentation | Actual Implementation |
|------------|---------------|----------------------|
| Repo 2 | README mentions `core_policy_snapshot.sql` | File exists but no SCD logic |
| Repo 3 | `dbt_project.yml` has snapshot path | No snapshot files exist |

### Gaps

- No historical tracking of policy changes
- No effective date/end date columns
- No version numbering
- No current record flags

## 8. dbt Model Duplication

### Staging Models

| Model Type | Repo 1 | Repo 2 | Repo 3 |
|------------|--------|--------|--------|
| Claims Staging | `stg_claims.sql` | `stg_claims.sql` | N/A |
| Policy Staging | N/A | `stg_policies.sql` | `cust_policy.sql` |
| Quote Staging | N/A | `stg_quotes.sql` | N/A |

### Transformation Patterns

**Common Pattern (CTE-based):**
```sql
with source as (
    select * from {{ source('...') }}
),
staged as (
    select
        cast(field as type) as field,
        ...
    from source
)
select * from staged
```

Both Repo 1 and Repo 2 use this pattern, but Repo 3 uses a slightly different structure.

## 9. File Grouping by Logic Type

### Data Generation

| Group | Files |
|-------|-------|
| Continuous Generation | `Repo1/data-generator/Simulator.py` |
| Batch Generation | `Repo2/python/generate_data.py` |

### Status Assignment

| Group | Files |
|-------|-------|
| Claim Status | `Repo2/python/generate_data.py:154-160` |
| Policy Status | `Repo2/python/generate_data.py:103-107` |
| Quote Status | `Repo2/python/generate_data.py:56-61` |

### Financial Calculations

| Group | Files |
|-------|-------|
| Premium Calculation | `Repo2/python/generate_data.py:48-54, 98-100` |
| Claim Amount | `Repo1/data-generator/Simulator.py:26`, `Repo2/python/generate_data.py:165-176` |
| Loss Ratio | `Repo2/dbt/models/marts/mart_loss_ratio_by_segment.sql` |

### Aggregation Models

| Group | Files |
|-------|-------|
| Claims Summary | `Repo1/ins_dbt/models/claims_summary.sql` |
| Customer Claims | `Repo3/models/mart/facts/customer_claims__facts.sql` |
| Policy Summary | `Repo3/models/mart/facts/policy_summary__facts.sql` |
| Loss Ratio | `Repo2/dbt/models/marts/mart_loss_ratio_by_segment.sql` |

## 10. Recommendations

### Consolidation Opportunities

1. **Merge Data Generators:** Create a unified data generator that supports both continuous and batch modes
2. **Standardize Status Codes:** Create a shared enum/lookup for all status values
3. **Implement Fraud Detection:** Add fraud scoring to Repo 2's generator
4. **Add SCD Logic:** Implement Type 2 SCD for policy tracking
5. **Unify dbt Patterns:** Create shared macros for common transformations

### Priority Actions

| Priority | Action | Impact |
|----------|--------|--------|
| High | Implement SCD for policies | Historical tracking |
| High | Add fraud detection to Repo 2 | Analytics capability |
| Medium | Standardize status codes | Data consistency |
| Medium | Create shared dbt package | Code reuse |
| Low | Merge data generators | Maintenance reduction |
