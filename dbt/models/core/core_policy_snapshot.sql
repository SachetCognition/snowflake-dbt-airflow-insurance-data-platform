{{
    config(
        materialized='table',
        schema='core'
    )
}}

with policies as (
    select * from {{ ref('stg_policies') }}
),

quotes as (
    select * from {{ ref('stg_quotes') }}
),

policy_snapshot as (
    select
        p.policy_id,
        p.policy_number,
        p.customer_id,
        p.product,
        p.inception_date,
        p.expiry_date,
        p.premium_written,
        p.payment_frequency,
        p.policy_status,
        q.quote_id,
        q.quote_number,
        q.quote_date,
        q.channel,
        q.risk_score,
        q.premium_quoted,
        q.quote_status,
        p.premium_written - q.premium_quoted as premium_adjustment,
        case
            when p.policy_status = 'ACTIVE' and p.expiry_date > current_date() then 'In Force'
            when p.policy_status = 'ACTIVE' and p.expiry_date <= current_date() then 'Expired'
            when p.policy_status = 'LAPSED' then 'Lapsed'
            when p.policy_status = 'CANCELLED' then 'Cancelled'
            else 'Unknown'
        end as policy_status_detail,
        datediff('day', p.inception_date, p.expiry_date) as policy_term_days,
        datediff('day', q.quote_date, p.inception_date) as quote_to_inception_days,
        current_timestamp() as snapshot_at
    from policies p
    left join quotes q on p.quote_id = q.quote_id
)

select * from policy_snapshot
