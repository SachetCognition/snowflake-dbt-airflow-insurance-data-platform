{{
    config(
        materialized='view',
        schema='core'
    )
}}

/*
    Core Policy Snapshot Model
    
    This model provides a policy-level summary with aggregated claims metrics.
    Used for policy-level analysis and customer risk assessment.
    
    Grain: One row per policy
*/

with policies as (
    select * from {{ ref('stg_policies') }}
),

claims_agg as (
    select
        policy_id,
        count(*) as claim_count,
        sum(incurred_amount) as total_incurred,
        sum(paid_amount) as total_paid,
        sum(reserve_amount) as total_reserve,
        sum(is_closed) as closed_claims,
        sum(is_rejected) as rejected_claims,
        min(loss_date) as first_loss_date,
        max(loss_date) as last_loss_date,
        avg(days_to_report) as avg_days_to_report,
        avg(days_to_settle) as avg_days_to_settle
    from {{ ref('stg_claims') }}
    group by policy_id
),

quotes as (
    select 
        quote_id,
        channel,
        risk_score,
        risk_band
    from {{ ref('stg_quotes') }}
),

policy_snapshot as (
    select
        -- Policy identifiers
        p.policy_id,
        p.policy_number,
        p.quote_id,
        p.customer_id,
        
        -- Policy dimensions
        p.product,
        p.policy_status,
        p.payment_frequency,
        q.channel,
        q.risk_band,
        
        -- Policy dates
        p.inception_date,
        p.expiry_date,
        p.policy_term_days,
        
        -- Premium metrics
        p.premium_written,
        p.earned_premium,
        q.risk_score,
        
        -- Claims summary
        coalesce(c.claim_count, 0) as claim_count,
        coalesce(c.total_incurred, 0) as total_incurred,
        coalesce(c.total_paid, 0) as total_paid,
        coalesce(c.total_reserve, 0) as total_reserve,
        coalesce(c.closed_claims, 0) as closed_claims,
        coalesce(c.rejected_claims, 0) as rejected_claims,
        c.first_loss_date,
        c.last_loss_date,
        c.avg_days_to_report,
        c.avg_days_to_settle,
        
        -- Derived metrics
        case 
            when coalesce(c.claim_count, 0) = 0 then 'NO_CLAIMS'
            when coalesce(c.claim_count, 0) = 1 then 'SINGLE_CLAIM'
            else 'MULTIPLE_CLAIMS'
        end as claims_category,
        
        -- Loss ratio at policy level
        case 
            when p.earned_premium > 0 
            then coalesce(c.total_incurred, 0) / p.earned_premium
            else null
        end as policy_loss_ratio,
        
        -- Flags
        case when coalesce(c.claim_count, 0) > 0 then 1 else 0 end as has_claims,
        
        -- Metadata
        current_timestamp() as snapshot_at,
        current_timestamp() as dbt_updated_at
        
    from policies p
    left join claims_agg c on p.policy_id = c.policy_id
    left join quotes q on p.quote_id = q.quote_id
)

select * from policy_snapshot
