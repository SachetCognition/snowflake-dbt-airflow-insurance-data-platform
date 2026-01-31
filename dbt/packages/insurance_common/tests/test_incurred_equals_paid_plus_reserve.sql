{% test incurred_equals_paid_plus_reserve(model, incurred_column, paid_column, reserve_column, tolerance=0.01) %}

select
    *
from {{ model }}
where abs(
    coalesce({{ incurred_column }}, 0) - 
    (coalesce({{ paid_column }}, 0) + coalesce({{ reserve_column }}, 0))
) > {{ tolerance }}

{% endtest %}
