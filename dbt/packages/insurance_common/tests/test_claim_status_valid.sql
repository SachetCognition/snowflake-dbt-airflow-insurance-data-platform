{% test claim_status_valid(model, column_name) %}

select
    {{ column_name }}
from {{ model }}
where {{ column_name }} not in (
    'OPEN',
    'PENDING',
    'UNDER_REVIEW',
    'CLOSED',
    'SETTLED',
    'REJECTED',
    'DENIED',
    'REOPENED',
    'SUBROGATION',
    'LITIGATION',
    'UNKNOWN'
)
and {{ column_name }} is not null

{% endtest %}
