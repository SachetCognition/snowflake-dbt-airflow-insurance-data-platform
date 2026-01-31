{{
    config(
        materialized='table',
        schema='core'
    )
}}

with policies as (
    select * from {{ ref('stg_policies') }}
),

claims as (
    select * from {{ ref('stg_claims') }}
),

policy_claims as (
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
        c.claim_id,
        c.claim_number,
        c.loss_date,
        c.report_date,
        c.settlement_date,
        c.claim_status,
        c.claim_cause,
        c.coverage_type,
        c.incurred_amount,
        c.paid_amount,
        c.reserve_amount,
        datediff('day', c.loss_date, c.report_date) as days_to_report,
        datediff('day', c.report_date, c.settlement_date) as days_to_settle,
        case
            when c.claim_status = 'CLOSED' then 'Settled'
            when c.claim_status = 'OPEN' then 'Pending'
            when c.claim_status = 'REJECTED' then 'Denied'
            else 'Unknown'
        end as claim_status_category
    from policies p
    left join claims c on p.policy_id = c.policy_id
)

select * from policy_claims
