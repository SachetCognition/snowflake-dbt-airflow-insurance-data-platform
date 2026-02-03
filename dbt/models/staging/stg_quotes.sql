{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_quotes') }}
),

cleaned as (
    select
        -- Primary key
        quote_id,
        
        -- Business identifiers
        quote_number,
        customer_id,
        
        -- Dates
        cast(quote_date as date) as quote_date,
        
        -- Dimensions
        upper(trim(product)) as product,
        upper(trim(channel)) as channel,
        upper(trim(quote_status)) as quote_status,
        
        -- Metrics
        coalesce(risk_score, 0) as risk_score,
        coalesce(premium_quoted, 0) as premium_quoted,
        
        -- Derived fields
        case 
            when risk_score < 0.3 then 'LOW'
            when risk_score < 0.6 then 'MEDIUM'
            else 'HIGH'
        end as risk_band,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from source
    where quote_id is not null
)

select * from cleaned
