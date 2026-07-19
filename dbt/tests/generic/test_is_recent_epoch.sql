{% test is_recent_epoch(model, column_name, min_epoch=946684800, max_skew_seconds=86400) %}
{#- Flags unix-epoch-seconds columns outside a sane real-world range: before
    min_epoch (default 2000-01-01, well before any source this project has)
    or more than max_skew_seconds (default 1 day) ahead of now -- catching a
    unit mistake (millis vs. seconds) or a corrupt/garbage timestamp. Nulls
    pass through -- that's not_null's job. -#}

with validation as (
    select {{ column_name }} as epoch_value
    from {{ model }}
    where {{ column_name }} is not null
)

select *
from validation
where epoch_value < {{ min_epoch }}
   or epoch_value > epoch(current_timestamp) + {{ max_skew_seconds }}

{% endtest %}
