{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_quotes') }}
),

staged as (
    select
        cast(quote_id as integer) as quote_id,
        quote_number,
        cast(customer_id as integer) as customer_id,
        cast(quote_date as date) as quote_date,
        product,
        channel,
        cast(risk_score as float) as risk_score,
        cast(premium_quoted as float) as premium_quoted,
        quote_status
    from source
)

select * from staged
