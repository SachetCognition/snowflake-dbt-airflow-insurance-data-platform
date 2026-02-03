{{
    config(
        materialized='view',
        schema='core'
    )
}}

/*
    Core Policy Claims Model
    
    This model joins policies with their associated claims to create a unified
    fact table for loss ratio calculations and claims analysis.
    
    Grain: One row per policy-claim combination (policies without claims are included)
*/

with policies as (
    select * from {{ ref('stg_policies') }}
),

claims as (
    select * from {{ ref('stg_claims') }}
),

quotes as (
    select 
        quote_id,
        channel,
        risk_score,
        risk_band
    from {{ ref('stg_quotes') }}
),

policy_claims as (
    select
        -- Policy dimensions
        p.policy_id,
        p.policy_number,
        p.quote_id,
        p.customer_id,
        p.product,
        p.inception_date,
        p.expiry_date,
        p.policy_status,
        p.payment_frequency,
        p.policy_term_days,
        
        -- Quote dimensions (for channel and risk)
        q.channel,
        q.risk_score,
        q.risk_band,
        
        -- Policy premium metrics
        p.premium_written,
        p.earned_premium,
        
        -- Claim dimensions (null if no claim)
        c.claim_id,
        c.claim_number,
        c.loss_date,
        c.report_date,
        c.settlement_date,
        c.claim_status,
        c.claim_cause,
        c.coverage_type,
        c.days_to_report,
        c.days_to_settle,
        c.is_closed,
        c.is_rejected,
        
        -- Claim metrics (0 if no claim)
        coalesce(c.incurred_amount, 0) as incurred_amount,
        coalesce(c.paid_amount, 0) as paid_amount,
        coalesce(c.reserve_amount, 0) as reserve_amount,
        
        -- Flags
        case when c.claim_id is not null then 1 else 0 end as has_claim,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from policies p
    left join claims c on p.policy_id = c.policy_id
    left join quotes q on p.quote_id = q.quote_id
)

select * from policy_claims
