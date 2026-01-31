{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

policy_claims as (
    select * from {{ ref('core_policy_claims') }}
),

customer_metrics as (
    select
        ps.customer_id,
        count(distinct ps.policy_id) as total_policies,
        sum(ps.premium_written) as total_premium_written,
        avg(ps.risk_score) as avg_risk_score,
        count(distinct pc.claim_id) as total_claims,
        coalesce(sum(pc.incurred_amount), 0) as total_incurred,
        coalesce(sum(pc.paid_amount), 0) as total_paid,
        case
            when count(distinct ps.policy_id) > 0
            then count(distinct pc.claim_id)::float / count(distinct ps.policy_id)
            else 0
        end as claim_frequency,
        case
            when count(distinct pc.claim_id) > 0
            then coalesce(sum(pc.incurred_amount), 0) / count(distinct pc.claim_id)
            else 0
        end as avg_claim_severity
    from policy_snapshot ps
    left join policy_claims pc on ps.policy_id = pc.policy_id
    group by 1
),

customer_risk as (
    select
        customer_id,
        total_policies,
        total_premium_written,
        round(avg_risk_score, 4) as avg_risk_score,
        total_claims,
        round(total_incurred, 2) as total_incurred,
        round(total_paid, 2) as total_paid,
        round(claim_frequency, 4) as claim_frequency,
        round(avg_claim_severity, 2) as avg_claim_severity,
        case
            when avg_risk_score < 0.3 and claim_frequency < 0.5 then 'LOW'
            when avg_risk_score >= 0.3 and avg_risk_score < 0.6 then 'MEDIUM'
            when avg_risk_score >= 0.6 or claim_frequency >= 1.0 then 'HIGH'
            else 'MEDIUM'
        end as risk_band,
        case
            when total_incurred > 0 and total_premium_written > 0
            then round(total_incurred / total_premium_written, 4)
            else 0
        end as customer_loss_ratio
    from customer_metrics
)

select * from customer_risk
order by risk_band desc, total_incurred desc
