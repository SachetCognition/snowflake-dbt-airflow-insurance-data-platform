{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'raw_claims') }}
),

cleaned as (
    select
        -- Primary key
        claim_id,
        
        -- Foreign keys
        policy_id,
        customer_id,
        
        -- Business identifiers
        claim_number,
        
        -- Dates
        cast(loss_date as date) as loss_date,
        cast(report_date as date) as report_date,
        cast(settlement_date as date) as settlement_date,
        
        -- Dimensions
        upper(trim(claim_status)) as claim_status,
        upper(trim(claim_cause)) as claim_cause,
        upper(trim(coverage_type)) as coverage_type,
        
        -- Metrics
        coalesce(incurred_amount, 0) as incurred_amount,
        coalesce(paid_amount, 0) as paid_amount,
        coalesce(reserve_amount, 0) as reserve_amount,
        
        -- Derived fields
        datediff('day', loss_date, report_date) as days_to_report,
        datediff('day', report_date, settlement_date) as days_to_settle,
        
        case 
            when claim_status = 'CLOSED' then 1
            else 0
        end as is_closed,
        
        case 
            when claim_status = 'REJECTED' then 1
            else 0
        end as is_rejected,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from source
    where claim_id is not null
)

select * from cleaned
