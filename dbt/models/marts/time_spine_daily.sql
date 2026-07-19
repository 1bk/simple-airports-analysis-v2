-- Daily time spine required by MetricFlow for time-based joins and
-- cumulative metrics (see models/marts/_semantic.yml).
with base_dates as (
    {{ dbt.date_spine("day", "date '2020-01-01'", "date '2031-01-01'") }}
)

select cast(date_day as date) as date_day
from base_dates
