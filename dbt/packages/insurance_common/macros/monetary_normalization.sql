{% macro calculate_incurred_amount(paid_column, reserve_column) %}
    coalesce({{ paid_column }}, 0) + coalesce({{ reserve_column }}, 0)
{% endmacro %}

{% macro calculate_loss_ratio(incurred_column, premium_column) %}
    case
        when coalesce({{ premium_column }}, 0) > 0
        then round(coalesce({{ incurred_column }}, 0) / {{ premium_column }}, 4)
        else 0
    end
{% endmacro %}

{% macro calculate_claim_frequency(claim_count_column, policy_count_column) %}
    case
        when coalesce({{ policy_count_column }}, 0) > 0
        then round({{ claim_count_column }}::float / {{ policy_count_column }}, 4)
        else 0
    end
{% endmacro %}

{% macro calculate_average_severity(incurred_column, claim_count_column) %}
    case
        when coalesce({{ claim_count_column }}, 0) > 0
        then round(coalesce({{ incurred_column }}, 0) / {{ claim_count_column }}, 2)
        else 0
    end
{% endmacro %}

{% macro calculate_underwriting_result(premium_column, incurred_column) %}
    coalesce({{ premium_column }}, 0) - coalesce({{ incurred_column }}, 0)
{% endmacro %}

{% macro normalize_currency(amount_column, decimal_places=2) %}
    round(coalesce({{ amount_column }}, 0), {{ decimal_places }})
{% endmacro %}

{% macro calculate_paid_ratio(paid_column, incurred_column) %}
    case
        when coalesce({{ incurred_column }}, 0) > 0
        then round(coalesce({{ paid_column }}, 0) / {{ incurred_column }}, 4)
        else 0
    end
{% endmacro %}

{% macro calculate_reserve_ratio(reserve_column, incurred_column) %}
    case
        when coalesce({{ incurred_column }}, 0) > 0
        then round(coalesce({{ reserve_column }}, 0) / {{ incurred_column }}, 4)
        else 0
    end
{% endmacro %}
