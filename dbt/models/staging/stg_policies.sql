{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_policies') }}
),

cleaned as (
    select
        -- Primary key
        policy_id,
        
        -- Foreign keys
        quote_id,
        customer_id,
        
        -- Business identifiers
        policy_number,
        
        -- Dates
        cast(inception_date as date) as inception_date,
        cast(expiry_date as date) as expiry_date,
        
        -- Dimensions
        upper(trim(product)) as product,
        upper(trim(payment_frequency)) as payment_frequency,
        upper(trim(policy_status)) as policy_status,
        
        -- Metrics
        coalesce(premium_written, 0) as premium_written,
        
        -- Derived fields
        datediff('day', inception_date, expiry_date) as policy_term_days,
        
        -- Calculate earned premium based on time elapsed
        -- For simplicity, assume linear earning over policy term
        case 
            when current_date() >= expiry_date then premium_written
            when current_date() <= inception_date then 0
            else premium_written * (datediff('day', inception_date, current_date()) / 
                 nullif(datediff('day', inception_date, expiry_date), 0))
        end as earned_premium,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from source
    where policy_id is not null
)

select * from cleaned
