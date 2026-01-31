# Canonical Insurance Claims Data Model

## Overview

This document defines the canonical data model for insurance claims across four repositories, providing a unified view of entities, their attributes, and mappings between different implementations.

## Entity Mapping Across Repositories

### 1. Claim Entity

The claim entity represents an insurance claim filed by a policyholder.

| Canonical Field | Repo 1 (NoSQL) | Repo 2 (Airflow) | Repo 3 (dbt) | Repo 4 (ML) |
|-----------------|----------------|------------------|--------------|-------------|
| claim_id | claim_id | claim_id | N/A (aggregated) | N/A |
| claim_number | N/A | claim_number | N/A | N/A |
| policy_id | N/A | policy_id | N/A | IDPOL |
| customer_id | customer_id | customer_id | CUSTOMERID | N/A |
| loss_date | date | loss_date | N/A | N/A |
| report_date | N/A | report_date | N/A | N/A |
| settlement_date | N/A | settlement_date | N/A | N/A |
| claim_status | N/A | claim_status (OPEN/CLOSED/REJECTED) | N/A | N/A |
| claim_type | claim_type (Accident/Theft/Fire) | claim_cause (Collision/Theft/Fire/Weather/Other) | N/A | N/A |
| coverage_type | N/A | coverage_type (Third Party/Comprehensive) | N/A | N/A |
| claim_amount | amount | incurred_amount | CLAIMHISTORY (count) | CLAIMNB |
| paid_amount | N/A | paid_amount | N/A | N/A |
| reserve_amount | N/A | reserve_amount | N/A | N/A |
| is_fraud | is_fraud (5% probability) | N/A | N/A | N/A |

**Grain Levels:**
- **Claim Header**: One row per claim (Repos 1, 2)
- **Claim Aggregation**: Aggregated at customer level (Repo 3)
- **Combined**: Claims embedded in policy data (Repo 4)

### 2. Policy Entity

The policy entity represents an insurance policy contract.

| Canonical Field | Repo 1 (NoSQL) | Repo 2 (Airflow) | Repo 3 (dbt) | Repo 4 (ML) |
|-----------------|----------------|------------------|--------------|-------------|
| policy_id | N/A | policy_id | N/A | IDPOL |
| policy_number | N/A | policy_number | N/A | N/A |
| quote_id | N/A | quote_id | N/A | N/A |
| customer_id | customer_id | customer_id | CUSTOMERID | N/A |
| product | policy_type (Auto/Home/Health) | product (Motor/Home/Travel) | POLICYTYPE | N/A |
| inception_date | N/A | inception_date | POLICYSTARTDATE | N/A |
| expiry_date | N/A | expiry_date | POLICYRENEWALDATE | N/A |
| premium_amount | N/A | premium_written | PREMIUMAMOUNT | N/A |
| payment_frequency | N/A | payment_frequency (ANNUAL/MONTHLY) | N/A | N/A |
| policy_status | N/A | policy_status (ACTIVE/LAPSED/CANCELLED) | N/A | N/A |
| coverage_amount | N/A | N/A | COVERAGEAMOUNT | N/A |
| deductible | N/A | N/A | DEDUCTIBLE | N/A |
| exposure | N/A | N/A | N/A | EXPOSURE |

### 3. Customer/Policyholder Entity

The customer entity represents the insured party.

| Canonical Field | Repo 1 (NoSQL) | Repo 2 (Airflow) | Repo 3 (dbt) | Repo 4 (ML) |
|-----------------|----------------|------------------|--------------|-------------|
| customer_id | customer_id | customer_id | CUSTOMERID | N/A |
| name | name | N/A | N/A | N/A |
| age | N/A | N/A | AGE | DRIVAGE |
| gender | N/A | N/A | GENDER | N/A |
| marital_status | N/A | N/A | MARITALSTATUS | N/A |
| occupation | N/A | N/A | OCCUPATION | N/A |
| income_level | N/A | N/A | INCOMELEVEL | N/A |
| education_level | N/A | N/A | EDUCATIONLEVEL | N/A |
| location | state | N/A | LOCATION | REGION |
| geographic_info | N/A | N/A | GEOGRAPHICINFORMATION | AREA |
| segmentation_group | N/A | N/A | SEGMENTATIONGROUP | N/A |
| credit_score | N/A | N/A | CREDITSCORE | BONUSMALUS |
| risk_profile | N/A | N/A | RISKPROFILE | N/A |

### 4. Quote Entity (Only in Repo 2)

The quote entity represents a price quotation before policy binding.

| Canonical Field | Repo 2 (Airflow) |
|-----------------|------------------|
| quote_id | quote_id |
| quote_number | quote_number |
| customer_id | customer_id |
| quote_date | quote_date |
| product | product |
| channel | channel (Online/Agent/Broker) |
| risk_score | risk_score (Beta distribution 0-1) |
| premium_quoted | premium_quoted |
| quote_status | quote_status (BOUND/DECLINED/EXPIRED) |

### 5. Vehicle Entity (Only in Repo 4)

| Canonical Field | Repo 4 (ML) |
|-----------------|-------------|
| vehicle_power | VEHPOWER |
| vehicle_age | VEHAGE |
| vehicle_brand | VEHBRAND |
| vehicle_gas | VEHGAS |
| density | DENSITY |

### 6. Missing Entities

The following entities are commonly found in insurance systems but are **NOT IMPLEMENTED** in any repository:

- **Adjuster**: Claims adjuster handling the claim
- **Provider/Repairer**: Service provider for repairs
- **Payment Transaction**: Individual payment records
- **Document**: Claim-related documents
- **Note/Activity**: Claim activity log

## Synonym Mapping

| Canonical Term | Repo 1 | Repo 2 | Repo 3 | Repo 4 |
|----------------|--------|--------|--------|--------|
| claim_amount | amount | incurred_amount | claimhistory | CLAIMNB |
| policy_type | policy_type | product | policytype | N/A |
| customer_location | state | N/A | location | REGION |
| risk_indicator | is_fraud | risk_score | riskprofile | BONUSMALUS |
| claim_category | claim_type | claim_cause | N/A | N/A |

## Data Type Standardization

| Field Category | Canonical Type | Notes |
|----------------|----------------|-------|
| IDs | INTEGER | All identifiers should be integers |
| Dates | DATE | ISO 8601 format (YYYY-MM-DD) |
| Timestamps | TIMESTAMP_NTZ | No timezone for consistency |
| Monetary | DECIMAL(18,2) | Two decimal places for currency |
| Percentages | DECIMAL(5,4) | Four decimal places (0.0000 to 1.0000) |
| Status Codes | VARCHAR(50) | Uppercase, underscore-separated |
| Boolean Flags | BOOLEAN | True/False |

## Grain Specifications

### Fact Table Grains

| Fact Table | Grain | Primary Key | Description |
|------------|-------|-------------|-------------|
| fact_claims | Claim Header | claim_id | One row per claim |
| fact_claim_transactions | Transaction | transaction_id | One row per payment/reserve change |
| fact_policy_premium | Policy Period | policy_id + period_date | Monthly premium recognition |
| fact_quotes | Quote | quote_id | One row per quote |

### Dimension Table Grains

| Dimension | Grain | Primary Key | SCD Type |
|-----------|-------|-------------|----------|
| dim_customer | Customer | customer_id | Type 2 |
| dim_policy | Policy Version | policy_id + version | Type 2 |
| dim_coverage | Coverage Type | coverage_id | Type 1 |
| dim_date | Calendar Day | date_key | Type 0 |
| dim_adjuster | Adjuster | adjuster_id | Type 2 |
| dim_provider | Provider | provider_id | Type 2 |

## Relationship Diagram

```
                    ┌─────────────┐
                    │  dim_date   │
                    └──────┬──────┘
                           │
┌─────────────┐    ┌───────┴───────┐    ┌─────────────┐
│ dim_customer│◄───┤  fact_claims  ├───►│ dim_policy  │
└─────────────┘    └───────┬───────┘    └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐ ┌───┴───┐ ┌──────┴──────┐
       │dim_coverage │ │dim_   │ │dim_provider │
       └─────────────┘ │adjuster└─────────────┘
                       └───────┘
```

## Key Business Rules

### Claim Amount Calculations

1. **Incurred Amount** = Paid Amount + Reserve Amount
2. **Loss Ratio** = Incurred Claims / Earned Premium
3. **Claim Frequency** = Number of Claims / Number of Policies
4. **Average Severity** = Total Incurred / Number of Claims

### Status Transitions

**Claim Status Flow:**
```
OPEN → CLOSED (settled)
OPEN → REJECTED (denied)
CLOSED → REOPENED (rare, not implemented)
```

**Policy Status Flow:**
```
ACTIVE → LAPSED (non-payment)
ACTIVE → CANCELLED (voluntary)
ACTIVE → EXPIRED (term end)
```

**Quote Status Flow:**
```
PENDING → BOUND (converted to policy)
PENDING → DECLINED (rejected)
PENDING → EXPIRED (timeout)
```

## Data Quality Rules

| Rule | Description | Applies To |
|------|-------------|------------|
| NOT NULL | Required fields | claim_id, policy_id, customer_id |
| UNIQUE | No duplicates | claim_id, policy_id, quote_id |
| REFERENTIAL | Foreign key exists | policy_id in claims → policies |
| RANGE | Value within bounds | risk_score BETWEEN 0 AND 1 |
| CONSISTENCY | Logical consistency | incurred = paid + reserve |
| TEMPORAL | Date ordering | loss_date <= report_date <= settlement_date |
