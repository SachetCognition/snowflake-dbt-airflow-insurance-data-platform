{{
    config(
        materialized='view',
        schema='marts'
    )
}}

/*
    Customer Risk Mart
    
    This mart provides customer-level risk assessment based on their
    policy and claims history. Used by underwriters for policy approval
    decisions and premium adjustments.
    
    Grain: One row per customer
*/

with policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

customer_metrics as (
    select
        customer_id,
        
        -- Policy counts
        count(distinct policy_id) as total_policies,
        count(distinct case when policy_status = 'ACTIVE' then policy_id end) as active_policies,
        count(distinct case when policy_status = 'CANCELLED' then policy_id end) as cancelled_policies,
        count(distinct case when policy_status = 'LAPSED' then policy_id end) as lapsed_policies,
        
        -- Product diversity
        count(distinct product) as product_count,
        listagg(distinct product, ', ') within group (order by product) as products_held,
        
        -- Premium metrics
        sum(premium_written) as total_premium_written,
        sum(earned_premium) as total_earned_premium,
        avg(premium_written) as avg_premium_per_policy,
        
        -- Claims metrics
        sum(claim_count) as total_claims,
        sum(total_incurred) as total_incurred_amount,
        sum(total_paid) as total_paid_amount,
        sum(total_reserve) as total_reserve_amount,
        
        -- Risk metrics
        avg(risk_score) as avg_risk_score,
        max(risk_score) as max_risk_score,
        
        -- Tenure
        min(inception_date) as first_policy_date,
        max(inception_date) as latest_policy_date,
        datediff('day', min(inception_date), current_date()) as customer_tenure_days,
        
        -- Policies with claims
        sum(has_claims) as policies_with_claims
        
    from policy_snapshot
    group by customer_id
),

final as (
    select
        customer_id,
        
        -- Policy metrics
        total_policies,
        active_policies,
        cancelled_policies,
        lapsed_policies,
        product_count,
        products_held,
        
        -- Premium metrics
        total_premium_written,
        total_earned_premium,
        avg_premium_per_policy,
        
        -- Claims metrics
        total_claims,
        total_incurred_amount,
        total_paid_amount,
        total_reserve_amount,
        
        -- Risk metrics
        avg_risk_score,
        max_risk_score,
        
        -- Tenure
        first_policy_date,
        latest_policy_date,
        customer_tenure_days,
        
        -- Derived metrics
        case 
            when total_policies > 0 
            then policies_with_claims::float / total_policies
            else 0
        end as claim_frequency_rate,
        
        case 
            when total_earned_premium > 0 
            then total_incurred_amount / total_earned_premium
            else null
        end as customer_loss_ratio,
        
        case 
            when total_claims > 0 
            then total_incurred_amount / total_claims
            else 0
        end as avg_claim_severity,
        
        -- Risk band classification
        case 
            when avg_risk_score < 0.3 then 'LOW'
            when avg_risk_score < 0.6 then 'MEDIUM'
            else 'HIGH'
        end as risk_band,
        
        -- Customer value tier
        case 
            when total_premium_written >= 5000 and total_policies >= 3 then 'PLATINUM'
            when total_premium_written >= 2000 and total_policies >= 2 then 'GOLD'
            when total_premium_written >= 1000 then 'SILVER'
            else 'BRONZE'
        end as customer_tier,
        
        -- Retention risk
        case 
            when cancelled_policies > 0 or lapsed_policies > 0 then 'AT_RISK'
            when customer_tenure_days > 730 and active_policies > 0 then 'LOYAL'
            when active_policies > 0 then 'ACTIVE'
            else 'INACTIVE'
        end as retention_status,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from customer_metrics
)

select * from final
order by total_premium_written desc
