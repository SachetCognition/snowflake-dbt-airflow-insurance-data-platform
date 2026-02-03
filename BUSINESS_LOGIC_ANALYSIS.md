# Business Logic Analysis

This document provides a comprehensive analysis of the Insurance Data Platform's business logic, data flows, and key metrics.

## Table of Contents

1. [Data Flow Overview](#data-flow-overview)
2. [Business Entities](#business-entities)
3. [Data Layer Architecture](#data-layer-architecture)
4. [Key Business Metrics](#key-business-metrics)
5. [Business Value by Mart](#business-value-by-mart)

---

## Data Flow Overview

### Quote to Policy Conversion

The insurance business process begins with quotes and follows a conversion funnel:

```
QUOTES (5000 records)
    |
    |-- BOUND (40%) -----> POLICIES (2000 records)
    |                           |
    |-- DECLINED (30%)          |-- 60% have NO claims
    |                           |-- 25% have 1 claim
    |-- EXPIRED (30%)           |-- 10% have 2 claims
                                |-- 5% have 3 claims
                                        |
                                        v
                                CLAIMS (~1200 records)
```

The 40% conversion rate represents the proportion of quotes that result in bound policies. This is a critical business metric that indicates sales effectiveness and pricing competitiveness. Quotes that don't convert are either declined by the customer (often due to price) or expire without action.

### Claims Distribution

The claims distribution follows a realistic insurance pattern where most policies never have a claim:

| Claims per Policy | Probability | Business Implication |
|-------------------|-------------|----------------------|
| 0 claims | 60% | Profitable policies with no loss |
| 1 claim | 25% | Single incident, typical claim pattern |
| 2 claims | 10% | Multiple incidents, higher risk |
| 3 claims | 5% | Frequent claimers, potential fraud risk |

This distribution ensures that approximately 40% of policies will have at least one claim, which is realistic for a mixed portfolio of Motor, Home, and Travel insurance products.

---

## Business Entities

### Quotes

Quotes represent potential business opportunities. Each quote captures:

| Attribute | Description | Business Use |
|-----------|-------------|--------------|
| quote_id | Unique identifier | Tracking and reference |
| customer_id | Customer reference | Customer relationship management |
| product | Motor, Home, or Travel | Product line analysis |
| channel | Online, Agent, or Broker | Distribution channel performance |
| risk_score | 0-1 scale (Beta distribution) | Underwriting decisions |
| premium_quoted | Calculated premium | Pricing analysis |
| quote_status | BOUND, DECLINED, EXPIRED | Conversion tracking |

**Risk Score Calculation**: The risk score uses a Beta(2,5) distribution, which produces values skewed toward lower risk (mean ~0.29). This reflects the reality that most customers are low-risk, with fewer high-risk customers. The premium is then calculated as:

```
premium = base_premium * (0.6 + 1.2 * risk_score)
```

This means premiums range from 60% to 180% of the base premium depending on risk.

### Policies

Policies represent active insurance contracts:

| Attribute | Description | Business Use |
|-----------|-------------|--------------|
| policy_id | Unique identifier | Policy administration |
| quote_id | Link to originating quote | Quote-to-policy tracking |
| inception_date | Coverage start date | Earned premium calculation |
| expiry_date | Coverage end date | Renewal management |
| premium_written | Final premium amount | Revenue recognition |
| policy_status | ACTIVE, LAPSED, CANCELLED | Portfolio management |

**Premium Written vs Earned**: Premium written is the total contract value. Earned premium is the portion recognized as revenue based on time elapsed:

```
earned_premium = premium_written * (days_elapsed / policy_term_days)
```

### Claims

Claims represent loss events and their financial impact:

| Attribute | Description | Business Use |
|-----------|-------------|--------------|
| claim_id | Unique identifier | Claims management |
| policy_id | Link to policy | Policy claims history |
| loss_date | Date of incident | Loss pattern analysis |
| report_date | Date reported | Reporting lag analysis |
| settlement_date | Date settled (if closed) | Settlement efficiency |
| incurred_amount | Total estimated cost | Loss ratio calculation |
| paid_amount | Amount actually paid | Cash flow management |
| reserve_amount | Amount held for future payment | Reserve adequacy |

**Incurred = Paid + Reserve**: The incurred amount represents the total estimated cost of a claim, split between what has been paid and what is reserved for future payment.

---

## Data Layer Architecture

### Staging Layer (STAGING Schema)

The staging layer performs minimal transformations to clean and standardize raw data:

**stg_quotes**
- Type casting (dates, numbers)
- Null handling with COALESCE
- Standardization (UPPER, TRIM)
- Derived field: risk_band (LOW/MEDIUM/HIGH based on risk_score thresholds)

**stg_policies**
- Date standardization
- Earned premium calculation based on time elapsed
- Policy term calculation in days

**stg_claims**
- Date standardization
- Days to report/settle calculations
- Status flags (is_closed, is_rejected)

### Core Layer (CORE Schema)

The core layer implements business logic and creates reusable entities:

**core_policy_claims**
- Joins policies with claims (left join to include policies without claims)
- Enriches with quote data (channel, risk_score)
- Grain: One row per policy-claim combination
- Use case: Detailed claim-level analysis

**core_policy_snapshot**
- Aggregates claims to policy level
- Calculates policy-level loss ratio
- Classifies policies by claims category
- Grain: One row per policy
- Use case: Policy-level analysis and customer risk assessment

### Marts Layer (MARTS Schema)

The marts layer provides analytics-ready aggregations for specific business use cases:

**mart_loss_ratio_by_segment**
- Aggregates by product, channel, and risk band
- Calculates loss ratio, claim frequency, and severity
- Classifies profitability tier
- Use case: Segment profitability analysis

**mart_customer_risk**
- Aggregates to customer level
- Calculates customer lifetime metrics
- Classifies risk band and customer tier
- Identifies retention risk
- Use case: Customer risk assessment and retention

**mart_product_performance**
- Time-series analysis by product and quarter
- Period-over-period comparisons
- Cumulative metrics
- Use case: Product strategy and trend analysis

---

## Key Business Metrics

### Loss Ratio

**Definition**: Loss Ratio = Incurred Claims / Earned Premium

This is the primary profitability metric in insurance. It measures how much of premium revenue is consumed by claims.

| Loss Ratio | Interpretation | Action |
|------------|----------------|--------|
| < 60% | Highly Profitable | Consider competitive pricing |
| 60-80% | Profitable | Maintain current strategy |
| 80-100% | Marginal | Review pricing and underwriting |
| > 100% | Unprofitable | Immediate remediation required |

**Example Calculation**:
```sql
loss_ratio = total_incurred_claims / total_earned_premium
-- If earned_premium = $100,000 and incurred_claims = $65,000
-- loss_ratio = 0.65 (65%)
```

### Claim Frequency

**Definition**: Claim Frequency = Policies with Claims / Total Policies

Measures how often claims occur across the portfolio.

```sql
claim_frequency = policies_with_claims / policy_count
-- If 400 policies have claims out of 1000 total
-- claim_frequency = 0.40 (40%)
```

### Claim Severity

**Definition**: Average Claim Severity = Total Incurred / Number of Claims

Measures the average cost per claim.

```sql
avg_claim_severity = total_incurred_claims / total_claims
-- If total_incurred = $500,000 and total_claims = 200
-- avg_claim_severity = $2,500
```

### Combined Ratio Components

The loss ratio is one component of the combined ratio:

```
Combined Ratio = Loss Ratio + Expense Ratio
```

A combined ratio below 100% indicates underwriting profit. This platform focuses on the loss ratio component; expense ratio would require additional operational cost data.

---

## Business Value by Mart

### mart_loss_ratio_by_segment

**Target Users**: Actuaries, Pricing Analysts, Underwriting Managers

**Business Questions Answered**:
1. Which product-channel-risk combinations are most profitable?
2. Where should we adjust pricing?
3. Which segments have unacceptable loss ratios?
4. How does risk band correlate with actual losses?

**Key Insights**:
- Compare loss ratios across products (Motor vs Home vs Travel)
- Identify channel effectiveness (Online vs Agent vs Broker)
- Validate risk scoring accuracy (do HIGH risk customers have higher loss ratios?)

**Sample Analysis**:
```sql
SELECT 
    product,
    channel,
    risk_band,
    loss_ratio,
    profitability_tier
FROM mart_loss_ratio_by_segment
WHERE loss_ratio > 0.8
ORDER BY loss_ratio DESC;
```

### mart_customer_risk

**Target Users**: Underwriters, Customer Service, Marketing

**Business Questions Answered**:
1. Which customers are high-risk based on claims history?
2. Who are our most valuable customers?
3. Which customers are at risk of churning?
4. How should we tier customers for service levels?

**Key Insights**:
- Customer lifetime value assessment
- Risk-based pricing recommendations
- Retention targeting for at-risk customers
- Cross-sell opportunities (customers with single product)

**Sample Analysis**:
```sql
SELECT 
    customer_id,
    total_policies,
    total_premium_written,
    customer_loss_ratio,
    risk_band,
    customer_tier,
    retention_status
FROM mart_customer_risk
WHERE retention_status = 'AT_RISK'
  AND customer_tier IN ('GOLD', 'PLATINUM')
ORDER BY total_premium_written DESC;
```

### mart_product_performance

**Target Users**: Product Managers, Executives, Business Analysts

**Business Questions Answered**:
1. How is each product performing over time?
2. Are loss ratios improving or deteriorating?
3. What is the premium growth rate by product?
4. Which quarters show seasonal patterns?

**Key Insights**:
- Product profitability trends
- Seasonal claim patterns
- Growth trajectory by product line
- Period-over-period comparisons

**Sample Analysis**:
```sql
SELECT 
    product,
    period_label,
    new_policies,
    premium_written,
    loss_ratio,
    premium_growth_rate
FROM mart_product_performance
WHERE policy_year >= 2023
ORDER BY product, policy_year, policy_quarter;
```

---

## Data Quality Considerations

### Synthetic Data Characteristics

This platform uses synthetic data with the following characteristics:

1. **Reproducibility**: RNG seed of 42 ensures identical data generation across runs
2. **Realistic Distributions**: Beta distribution for risk scores, normal distributions for claim amounts
3. **Referential Integrity**: All claims reference valid policies, all policies reference valid quotes
4. **Business Rules**: 40% conversion rate, 60% no-claims rate enforced

### Known Limitations

1. **No Geographic Data**: Real insurance would segment by region/state
2. **Simplified Premium Calculation**: Real pricing uses many more factors
3. **No Reinsurance**: Large claims would typically be ceded to reinsurers
4. **Static Risk Scores**: Real systems update risk scores over time
5. **No Fraud Indicators**: Real systems would flag suspicious patterns

---

## Glossary

| Term | Definition |
|------|------------|
| **Earned Premium** | Premium revenue recognized for coverage already provided |
| **Written Premium** | Total premium for the policy contract |
| **Incurred Claims** | Total estimated cost of claims (paid + reserves) |
| **Loss Ratio** | Incurred Claims / Earned Premium |
| **Claim Frequency** | Rate at which claims occur |
| **Claim Severity** | Average cost per claim |
| **IBNR** | Incurred But Not Reported - claims that occurred but haven't been reported yet |
| **Reserve** | Amount set aside for future claim payments |
| **Underwriting** | Process of evaluating and pricing risk |
| **Conversion Rate** | Percentage of quotes that become policies |

---

## Conclusion

This Insurance Data Platform provides a comprehensive analytics foundation for insurance operations. The medallion architecture (RAW → STAGING → CORE → MARTS) ensures data quality and enables flexible analysis. The three mart models address the primary analytical needs of actuaries, underwriters, and business analysts, with the loss ratio serving as the central profitability metric.

The platform can be extended with additional data sources (geographic, demographic, external risk factors) and more sophisticated models (predictive analytics, fraud detection) as business needs evolve.
