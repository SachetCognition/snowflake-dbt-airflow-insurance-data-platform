{% macro calculate_days_between(start_date_column, end_date_column) %}
    datediff('day', {{ start_date_column }}, {{ end_date_column }})
{% endmacro %}

{% macro calculate_months_between(start_date_column, end_date_column) %}
    datediff('month', {{ start_date_column }}, {{ end_date_column }})
{% endmacro %}

{% macro calculate_policy_term_days(inception_date_column, expiry_date_column) %}
    datediff('day', {{ inception_date_column }}, {{ expiry_date_column }})
{% endmacro %}

{% macro calculate_days_to_report(loss_date_column, report_date_column) %}
    datediff('day', {{ loss_date_column }}, {{ report_date_column }})
{% endmacro %}

{% macro calculate_days_to_settle(report_date_column, settlement_date_column) %}
    case
        when {{ settlement_date_column }} is not null
        then datediff('day', {{ report_date_column }}, {{ settlement_date_column }})
        else null
    end
{% endmacro %}

{% macro get_date_key(date_column) %}
    to_number(to_char({{ date_column }}, 'YYYYMMDD'))
{% endmacro %}

{% macro truncate_to_month(date_column) %}
    date_trunc('month', {{ date_column }})
{% endmacro %}

{% macro truncate_to_quarter(date_column) %}
    date_trunc('quarter', {{ date_column }})
{% endmacro %}

{% macro truncate_to_year(date_column) %}
    date_trunc('year', {{ date_column }})
{% endmacro %}

{% macro is_date_in_range(date_column, start_date, end_date) %}
    {{ date_column }} >= {{ start_date }} and {{ date_column }} <= {{ end_date }}
{% endmacro %}
