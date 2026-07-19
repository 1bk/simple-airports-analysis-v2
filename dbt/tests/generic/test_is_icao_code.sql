{% test is_icao_code(model, column_name) %}
{#- Flags values that aren't a 4-character uppercase alphanumeric ICAO code.
    Nulls pass through untouched -- that's not_null's job, not this test's -- so
    this stays composable with data_tests: [not_null, is_icao_code]. -#}

with validation as (
    select {{ column_name }} as icao_code
    from {{ model }}
    where {{ column_name }} is not null
)

select *
from validation
where not regexp_matches(icao_code, '^[A-Z0-9]{4}$')

{% endtest %}
