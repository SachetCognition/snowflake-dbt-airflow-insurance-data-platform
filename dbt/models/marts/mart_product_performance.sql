{{
    config(
        materialized='view',
        schema='marts'
    )
}}

/*
    Product Performance Mart
    
    This mart provides product-level performance analytics over time.
    Used by business analysts for executive dashboards and product strategy.
    
    Grain: One row per product-year-quarter combination
*/

with policy_snapshot as (
    select * from {{ ref('core_policy_snapshot') }}
),

time_periods as (
    select
        product,
        year(inception_date) as policy_year,
        quarter(inception_date) as policy_quarter,
        concat(year(inception_date), '-Q', quarter(inception_date)) as period_label,
        
        -- Policy counts
        count(distinct policy_id) as new_policies,
        count(distinct customer_id) as unique_customers,
        
        -- Premium metrics
        sum(premium_written) as premium_written,
        sum(earned_premium) as earned_premium,
        avg(premium_written) as avg_premium,
        
        -- Claims metrics
        sum(claim_count) as total_claims,
        sum(total_incurred) as incurred_claims,
        sum(total_paid) as paid_claims,
        sum(total_reserve) as reserve_amount,
        
        -- Risk metrics
        avg(risk_score) as avg_risk_score,
        sum(has_claims) as policies_with_claims
        
    from policy_snapshot
    group by product, year(inception_date), quarter(inception_date)
),

final as (
    select
        -- Dimensions
        product,
        policy_year,
        policy_quarter,
        period_label,
        
        -- Policy metrics
        new_policies,
        unique_customers,
        
        -- Premium metrics
        premium_written,
        earned_premium,
        avg_premium,
        
        -- Claims metrics
        total_claims,
        incurred_claims,
        paid_claims,
        reserve_amount,
        
        -- Risk metrics
        avg_risk_score,
        policies_with_claims,
        
        -- Key ratios
        case 
            when earned_premium > 0 
            then incurred_claims / earned_premium
            else null
        end as loss_ratio,
        
        case 
            when new_policies > 0 
            then policies_with_claims::float / new_policies
            else null
        end as claim_frequency,
        
        case 
            when total_claims > 0 
            then incurred_claims / total_claims
            else null
        end as avg_claim_severity,
        
        -- Period-over-period metrics (using window functions)
        lag(premium_written) over (
            partition by product 
            order by policy_year, policy_quarter
        ) as prev_period_premium,
        
        lag(incurred_claims) over (
            partition by product 
            order by policy_year, policy_quarter
        ) as prev_period_claims,
        
        -- Growth calculations
        case 
            when lag(premium_written) over (
                partition by product 
                order by policy_year, policy_quarter
            ) > 0 
            then (premium_written - lag(premium_written) over (
                partition by product 
                order by policy_year, policy_quarter
            )) / lag(premium_written) over (
                partition by product 
                order by policy_year, policy_quarter
            )
            else null
        end as premium_growth_rate,
        
        -- Cumulative metrics
        sum(premium_written) over (
            partition by product 
            order by policy_year, policy_quarter
            rows unbounded preceding
        ) as cumulative_premium,
        
        sum(incurred_claims) over (
            partition by product 
            order by policy_year, policy_quarter
            rows unbounded preceding
        ) as cumulative_claims,
        
        -- Metadata
        current_timestamp() as dbt_updated_at
        
    from time_periods
)

select * from final
order by product, policy_year, policy_quarter
