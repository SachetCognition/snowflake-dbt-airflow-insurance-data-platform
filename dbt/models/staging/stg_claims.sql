with source as (
    select * from {{ source('raw', 'claims') }}
),

staged as (
    select
        claim_id,
        claim_number,
        policy_id,
        customer_id,
        loss_date::date as loss_date,
        report_date::date as report_date,
        case when settlement_date = '' or settlement_date is null then null else settlement_date::date end as settlement_date,
        claim_status,
        claim_cause,
        coverage_type,
        incurred_amount::float as incurred_amount,
        paid_amount::float as paid_amount,
        reserve_amount::float as reserve_amount,
        -- Fraud detection fields
        coalesce(is_fraud::boolean, false) as is_fraud,
        coalesce(fraud_score::int, 0) as fraud_score,
        fraud_indicators,
        current_timestamp() as loaded_at
    from source
)

select * from staged
