{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_policies') }}
),

staged as (
    select
        cast(policy_id as integer) as policy_id,
        policy_number,
        cast(quote_id as integer) as quote_id,
        cast(customer_id as integer) as customer_id,
        product,
        cast(inception_date as date) as inception_date,
        cast(expiry_date as date) as expiry_date,
        cast(premium_written as float) as premium_written,
        payment_frequency,
        policy_status
    from source
)

select * from staged
