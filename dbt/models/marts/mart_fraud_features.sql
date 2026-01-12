{{
    config(
        materialized='view'
    )
}}

with claims as (
    select * from {{ ref('stg_claims') }}
),

policies as (
    select * from {{ ref('stg_policies') }}
),

policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

policy_claims as (
    select * from {{ ref('core_policy_claims') }}
),

-- Calculate claim velocity (multiple claims in short time periods)
claim_velocity as (
    select
        c.customer_id,
        c.policy_id,
        c.claim_id,
        c.loss_date,
        c.report_date,
        c.incurred_amount,
        count(*) over (
            partition by c.customer_id 
            order by c.loss_date 
            rows between 30 preceding and current row
        ) as claims_last_30_days,
        count(*) over (
            partition by c.customer_id 
            order by c.loss_date 
            rows between 90 preceding and current row
        ) as claims_last_90_days,
        count(*) over (
            partition by c.policy_id 
            order by c.loss_date 
            rows between unbounded preceding and current row
        ) as cumulative_policy_claims
    from claims c
),

-- Calculate amount statistics for anomaly detection
amount_stats as (
    select
        avg(incurred_amount) as avg_claim_amount,
        stddev(incurred_amount) as stddev_claim_amount,
        percentile_cont(0.95) within group (order by incurred_amount) as p95_claim_amount,
        percentile_cont(0.99) within group (order by incurred_amount) as p99_claim_amount
    from claims
),

-- Calculate product-level statistics
product_stats as (
    select
        ps.product,
        avg(c.incurred_amount) as avg_product_claim,
        stddev(c.incurred_amount) as stddev_product_claim
    from claims c
    join policy_snapshot ps on c.policy_id = ps.policy_id
    group by ps.product
),

-- Customer claim history aggregation
customer_claim_history as (
    select
        customer_id,
        count(distinct claim_id) as total_claims,
        count(distinct policy_id) as policies_with_claims,
        sum(incurred_amount) as total_claim_amount,
        avg(incurred_amount) as avg_claim_amount,
        min(loss_date) as first_claim_date,
        max(loss_date) as last_claim_date,
        count(distinct claim_cause) as distinct_claim_causes,
        sum(case when claim_status = 'REJECTED' then 1 else 0 end) as rejected_claims
    from claims
    group by customer_id
),

-- Claim timing analysis
claim_timing as (
    select
        c.claim_id,
        c.policy_id,
        c.customer_id,
        c.loss_date,
        c.report_date,
        p.inception_date,
        datediff('day', c.loss_date, c.report_date) as days_to_report,
        datediff('day', p.inception_date, c.loss_date) as days_from_inception,
        case 
            when datediff('day', p.inception_date, c.loss_date) <= 30 then true 
            else false 
        end as claim_within_30_days_of_inception,
        case 
            when datediff('day', c.loss_date, c.report_date) <= 1 then true 
            else false 
        end as same_day_reporting
    from claims c
    join policies p on c.policy_id = p.policy_id
),

-- Repeated claim cause patterns
claim_cause_patterns as (
    select
        customer_id,
        claim_cause,
        count(*) as cause_count,
        row_number() over (partition by customer_id order by count(*) desc) as cause_rank
    from claims
    group by customer_id, claim_cause
),

-- Main fraud features aggregation
fraud_features as (
    select
        c.claim_id,
        c.claim_number,
        c.policy_id,
        c.customer_id,
        c.loss_date,
        c.report_date,
        c.settlement_date,
        c.claim_status,
        c.claim_cause,
        c.coverage_type,
        c.incurred_amount,
        c.paid_amount,
        c.reserve_amount,
        
        -- Ground truth fraud labels (from data generation)
        c.is_fraud,
        c.fraud_score as ground_truth_fraud_score,
        c.fraud_indicators,
        
        -- Policy context
        ps.product,
        ps.channel,
        ps.risk_score,
        ps.risk_band,
        ps.premium_written,
        ps.inception_date,
        ps.expiry_date,
        
        -- Velocity indicators
        cv.claims_last_30_days,
        cv.claims_last_90_days,
        cv.cumulative_policy_claims,
        
        -- Timing indicators
        ct.days_to_report,
        ct.days_from_inception,
        ct.claim_within_30_days_of_inception,
        ct.same_day_reporting,
        
        -- Amount anomaly indicators
        case 
            when c.incurred_amount > (ast.avg_claim_amount + 3 * ast.stddev_claim_amount) then true 
            else false 
        end as amount_3_std_above_mean,
        case 
            when c.incurred_amount > ast.p95_claim_amount then true 
            else false 
        end as amount_above_p95,
        case 
            when c.incurred_amount > ast.p99_claim_amount then true 
            else false 
        end as amount_above_p99,
        
        -- Product-specific anomaly
        case 
            when pst.stddev_product_claim > 0 
                 and c.incurred_amount > (pst.avg_product_claim + 2 * pst.stddev_product_claim) 
            then true 
            else false 
        end as amount_anomaly_for_product,
        
        -- Customer history indicators
        cch.total_claims as customer_total_claims,
        cch.policies_with_claims as customer_policies_with_claims,
        cch.total_claim_amount as customer_total_claim_amount,
        cch.rejected_claims as customer_rejected_claims,
        
        -- Pattern indicators
        case 
            when ccp.cause_count >= 3 then true 
            else false 
        end as repeated_claim_cause,
        
        -- Claim-to-premium ratio
        case 
            when ps.premium_written > 0 
            then round(c.incurred_amount / ps.premium_written, 4)
            else 0 
        end as claim_to_premium_ratio,
        
        -- Composite fraud score (rule-based)
        (
            case when cv.claims_last_30_days > 2 then 20 else 0 end +
            case when cv.claims_last_90_days > 4 then 15 else 0 end +
            case when ct.claim_within_30_days_of_inception then 15 else 0 end +
            case when ct.same_day_reporting then 10 else 0 end +
            case when c.incurred_amount > (ast.avg_claim_amount + 3 * ast.stddev_claim_amount) then 20 else 0 end +
            case when c.incurred_amount > ast.p99_claim_amount then 15 else 0 end +
            case when cch.rejected_claims > 0 then 10 else 0 end +
            case when ccp.cause_count >= 3 then 10 else 0 end +
            case when ps.premium_written > 0 and c.incurred_amount / ps.premium_written > 5 then 15 else 0 end
        ) as rule_based_fraud_score,
        
        -- Fraud risk tier based on composite score
        case
            when (
                case when cv.claims_last_30_days > 2 then 20 else 0 end +
                case when cv.claims_last_90_days > 4 then 15 else 0 end +
                case when ct.claim_within_30_days_of_inception then 15 else 0 end +
                case when ct.same_day_reporting then 10 else 0 end +
                case when c.incurred_amount > (ast.avg_claim_amount + 3 * ast.stddev_claim_amount) then 20 else 0 end +
                case when c.incurred_amount > ast.p99_claim_amount then 15 else 0 end +
                case when cch.rejected_claims > 0 then 10 else 0 end +
                case when ccp.cause_count >= 3 then 10 else 0 end +
                case when ps.premium_written > 0 and c.incurred_amount / ps.premium_written > 5 then 15 else 0 end
            ) >= 50 then 'HIGH'
            when (
                case when cv.claims_last_30_days > 2 then 20 else 0 end +
                case when cv.claims_last_90_days > 4 then 15 else 0 end +
                case when ct.claim_within_30_days_of_inception then 15 else 0 end +
                case when ct.same_day_reporting then 10 else 0 end +
                case when c.incurred_amount > (ast.avg_claim_amount + 3 * ast.stddev_claim_amount) then 20 else 0 end +
                case when c.incurred_amount > ast.p99_claim_amount then 15 else 0 end +
                case when cch.rejected_claims > 0 then 10 else 0 end +
                case when ccp.cause_count >= 3 then 10 else 0 end +
                case when ps.premium_written > 0 and c.incurred_amount / ps.premium_written > 5 then 15 else 0 end
            ) >= 25 then 'MEDIUM'
            else 'LOW'
        end as fraud_risk_tier,
        
        current_timestamp() as calculated_at
        
    from claims c
    join policy_snapshot ps on c.policy_id = ps.policy_id
    join claim_velocity cv on c.claim_id = cv.claim_id
    join claim_timing ct on c.claim_id = ct.claim_id
    cross join amount_stats ast
    left join product_stats pst on ps.product = pst.product
    left join customer_claim_history cch on c.customer_id = cch.customer_id
    left join claim_cause_patterns ccp on c.customer_id = ccp.customer_id 
        and c.claim_cause = ccp.claim_cause 
        and ccp.cause_rank = 1
)

select * from fraud_features
order by rule_based_fraud_score desc, claim_id
