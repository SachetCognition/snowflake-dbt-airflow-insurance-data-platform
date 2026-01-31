{% test date_ordering(model, first_date_column, second_date_column) %}

select
    *
from {{ model }}
where {{ first_date_column }} is not null
and {{ second_date_column }} is not null
and {{ first_date_column }} > {{ second_date_column }}

{% endtest %}
