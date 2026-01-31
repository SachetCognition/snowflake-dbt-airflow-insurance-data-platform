{% macro map_policy_status(status_column) %}
    case
        when upper({{ status_column }}) in ('ACTIVE', 'IN_FORCE', 'INFORCE') then 'ACTIVE'
        when upper({{ status_column }}) in ('LAPSED', 'NON_PAYMENT', 'NONPAYMENT') then 'LAPSED'
        when upper({{ status_column }}) in ('CANCELLED', 'CANCELED', 'TERMINATED') then 'CANCELLED'
        when upper({{ status_column }}) in ('EXPIRED', 'MATURED') then 'EXPIRED'
        when upper({{ status_column }}) in ('PENDING', 'PENDING_ISSUE') then 'PENDING'
        when upper({{ status_column }}) in ('SUSPENDED') then 'SUSPENDED'
        else 'UNKNOWN'
    end
{% endmacro %}

{% macro map_policy_status_detail(status_column, expiry_date_column) %}
    case
        when upper({{ status_column }}) in ('ACTIVE', 'IN_FORCE', 'INFORCE') and {{ expiry_date_column }} > current_date() then 'In Force'
        when upper({{ status_column }}) in ('ACTIVE', 'IN_FORCE', 'INFORCE') and {{ expiry_date_column }} <= current_date() then 'Expired'
        when upper({{ status_column }}) in ('LAPSED', 'NON_PAYMENT', 'NONPAYMENT') then 'Lapsed'
        when upper({{ status_column }}) in ('CANCELLED', 'CANCELED', 'TERMINATED') then 'Cancelled'
        when upper({{ status_column }}) in ('EXPIRED', 'MATURED') then 'Expired'
        when upper({{ status_column }}) in ('PENDING', 'PENDING_ISSUE') then 'Pending Issue'
        when upper({{ status_column }}) in ('SUSPENDED') then 'Suspended'
        else 'Unknown'
    end
{% endmacro %}

{% macro is_policy_active(status_column) %}
    case
        when upper({{ status_column }}) in ('ACTIVE', 'IN_FORCE', 'INFORCE') then true
        else false
    end
{% endmacro %}

{% macro map_quote_status(status_column) %}
    case
        when upper({{ status_column }}) in ('BOUND', 'CONVERTED', 'ACCEPTED') then 'BOUND'
        when upper({{ status_column }}) in ('DECLINED', 'REJECTED', 'NOT_TAKEN_UP') then 'DECLINED'
        when upper({{ status_column }}) in ('EXPIRED', 'LAPSED', 'TIMEOUT') then 'EXPIRED'
        when upper({{ status_column }}) in ('PENDING', 'OPEN', 'IN_PROGRESS') then 'PENDING'
        else 'UNKNOWN'
    end
{% endmacro %}

{% macro is_quote_converted(status_column) %}
    case
        when upper({{ status_column }}) in ('BOUND', 'CONVERTED', 'ACCEPTED') then true
        else false
    end
{% endmacro %}
