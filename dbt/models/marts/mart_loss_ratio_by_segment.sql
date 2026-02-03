{{
    config(
        materialized='view',
        schema='marts'
    )
}}

/*
    Loss Ratio by Segment Mart
    
    This mart calculates the Loss Ratio (Incurred Claims / Earned Premium) 
    segmented by product, channel, and risk band.
    
    Loss Ratio is the primary profitability metric in insurance:
    - Loss Ratio < 100% indicates underwriting profit
    - Loss Ratio > 100% indicates underwriting loss
    
    Grain: One row per product-channel-risk_band combination
*/

with policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

segment_metrics as (
    select
        -- Segment dimensions
        product,
        channel,
        risk_band,
        
        -- Policy counts
        count(distinct policy_id) as policy_count,
        count(distinct customer_id) as customer_count,
        
        -- Premium metrics
        sum(premium_written) as total_premium_written,
        sum(earned_premium) as total_earned_premium,
        avg(premium_written) as avg_premium_written,
        
        -- Claims metrics
        sum(claim_count) as total_claims,
        sum(total_incurred) as total_incurred_claims,
        sum(total_paid) as total_paid_claims,
        sum(total_reserve) as total_reserve,
        
        -- Policy with claims
        sum(has_claims) as policies_with_claims,
        
        -- Average metrics
        avg(risk_score) as avg_risk_score,
        avg(claim_count) as avg_claims_per_policy
        
    from policy_snapshot
    group by product, channel, risk_band
),

final as (
    select
        -- Segment dimensions
        product,
        channel,
        risk_band,
        
        -- Policy metrics
        policy_count,
        customer_count,
        policies_with_claims,
        
        -- Premium metrics
        total_premium_written,
        total_earned_premium,
        avg_premium_written,
        
        -- Claims metrics
        total_claims,
        total_incurred_claims,
        total_paid_claims,
        total_reserve,
        avg_claims_per_policy,
        
        -- Risk metrics
        avg_risk_score,
        
        -- Key ratios
        case 
            when total_earned_premium > 0 
            then total_incurred_claims / total_earned_premium
            else null
        end as loss_ratio,
        
        case 
            when policy_count > 0 
            then policies_with_claims::float / policy_count
            else null
        end as claim_frequency,
        
        case 
            when total_claims > 0 
            then total_incurred_claims / total_claims
            else null
        end as avg_claim_severity,
        
        -- Profitability indicator
        case 
            when total_earned_premium > 0 and 
                 (total_incurred_claims / total_earned_premium) < 0.6 then 'HIGHLY_PROFITABLE'
            when total_earned_premium > 0 and 
                 (total_incurred_claims / total_earned_premium) < 0.8 then 'PROFITABLE'
            when total_earned_premium > 0 and 
                 (total_incurred_claims / total_earned_premium) < 1.0 then 'MARGINAL'
            when total_earned_premium > 0 then 'UNPROFITABLE'
            else 'UNKNOWN'
        end as profitability_tier,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from segment_metrics
)

select * from final
order by product, channel, risk_band
