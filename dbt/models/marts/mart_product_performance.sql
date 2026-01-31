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

quotes as (
    select * from {{ ref('stg_quotes') }}
),

product_performance as (
    select
        ps.product,
        date_trunc('quarter', ps.inception_date) as quarter,
        count(distinct q.quote_id) as total_quotes,
        count(distinct ps.policy_id) as total_policies,
        case
            when count(distinct q.quote_id) > 0
            then round(count(distinct ps.policy_id)::float / count(distinct q.quote_id), 4)
            else 0
        end as conversion_rate,
        sum(ps.premium_written) as earned_premium,
        avg(ps.premium_written) as avg_premium_per_policy,
        count(distinct pc.claim_id) as total_claims,
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
        sum(ps.premium_written) - coalesce(sum(pc.incurred_amount), 0) as underwriting_result,
        count(distinct case when ps.policy_status = 'ACTIVE' then ps.policy_id end) as active_policies,
        count(distinct case when ps.policy_status = 'LAPSED' then ps.policy_id end) as lapsed_policies,
        count(distinct case when ps.policy_status = 'CANCELLED' then ps.policy_id end) as cancelled_policies
    from policy_snapshot ps
    left join policy_claims pc on ps.policy_id = pc.policy_id
    left join quotes q on ps.quote_id = q.quote_id
    group by 1, 2
)

select * from product_performance
order by quarter, product
