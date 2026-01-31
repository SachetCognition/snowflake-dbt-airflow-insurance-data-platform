{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with policy_claims as (
    select * from {{ ref('core_policy_claims') }}
),

policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

loss_ratio_by_segment as (
    select
        ps.product,
        ps.channel,
        date_trunc('month', ps.inception_date) as inception_month,
        count(distinct ps.policy_id) as policy_count,
        sum(ps.premium_written) as earned_premium,
        count(distinct pc.claim_id) as claim_count,
        coalesce(sum(pc.incurred_amount), 0) as incurred_claims,
        coalesce(sum(pc.paid_amount), 0) as paid_claims,
        coalesce(sum(pc.reserve_amount), 0) as reserve_amount,
        case
            when sum(ps.premium_written) > 0 
            then round(coalesce(sum(pc.incurred_amount), 0) / sum(ps.premium_written), 4)
            else 0
        end as loss_ratio,
        case
            when count(distinct ps.policy_id) > 0
            then round(count(distinct pc.claim_id)::float / count(distinct ps.policy_id), 4)
            else 0
        end as claim_frequency,
        case
            when count(distinct pc.claim_id) > 0
            then round(coalesce(sum(pc.incurred_amount), 0) / count(distinct pc.claim_id), 2)
            else 0
        end as average_claim_severity
    from policy_snapshot ps
    left join policy_claims pc on ps.policy_id = pc.policy_id
    group by 1, 2, 3
)

select * from loss_ratio_by_segment
order by inception_month, product, channel
