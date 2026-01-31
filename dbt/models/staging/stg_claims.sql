{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_claims') }}
),

staged as (
    select
        cast(claim_id as integer) as claim_id,
        claim_number,
        cast(policy_id as integer) as policy_id,
        cast(customer_id as integer) as customer_id,
        cast(loss_date as date) as loss_date,
        cast(report_date as date) as report_date,
        cast(settlement_date as date) as settlement_date,
        claim_status,
        claim_cause,
        coverage_type,
        cast(incurred_amount as float) as incurred_amount,
        cast(paid_amount as float) as paid_amount,
        cast(reserve_amount as float) as reserve_amount
    from source
)

select * from staged
