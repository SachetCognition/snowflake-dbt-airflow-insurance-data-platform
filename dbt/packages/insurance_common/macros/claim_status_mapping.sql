{% macro map_claim_status(status_column) %}
    case
        when upper({{ status_column }}) in ('CLOSED', 'SETTLED') then 'CLOSED'
        when upper({{ status_column }}) in ('OPEN', 'PENDING', 'IN_PROGRESS', 'UNDER_REVIEW') then 'OPEN'
        when upper({{ status_column }}) in ('REJECTED', 'DENIED', 'DECLINED') then 'REJECTED'
        when upper({{ status_column }}) in ('REOPENED') then 'REOPENED'
        when upper({{ status_column }}) in ('SUBROGATION', 'SUBRO') then 'SUBROGATION'
        when upper({{ status_column }}) in ('LITIGATION', 'LEGAL') then 'LITIGATION'
        else 'UNKNOWN'
    end
{% endmacro %}

{% macro map_claim_status_category(status_column) %}
    case
        when upper({{ status_column }}) in ('CLOSED', 'SETTLED', 'REJECTED', 'DENIED', 'DECLINED') then 'Resolved'
        when upper({{ status_column }}) in ('OPEN', 'PENDING', 'IN_PROGRESS', 'UNDER_REVIEW', 'REOPENED', 'SUBROGATION', 'LITIGATION') then 'Active'
        else 'Unknown'
    end
{% endmacro %}

{% macro is_claim_open(status_column) %}
    case
        when upper({{ status_column }}) in ('OPEN', 'PENDING', 'IN_PROGRESS', 'UNDER_REVIEW', 'REOPENED', 'SUBROGATION', 'LITIGATION') then true
        else false
    end
{% endmacro %}

{% macro is_claim_closed(status_column) %}
    case
        when upper({{ status_column }}) in ('CLOSED', 'SETTLED') then true
        else false
    end
{% endmacro %}

{% macro is_claim_denied(status_column) %}
    case
        when upper({{ status_column }}) in ('REJECTED', 'DENIED', 'DECLINED') then true
        else false
    end
{% endmacro %}
