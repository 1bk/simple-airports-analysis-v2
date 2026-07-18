{#- Arrivals come from two optional tables: raw.arrivals (live credentialed
    fetch, this run) and raw.arrivals_history (committed parquet snapshots).
    Either or both may be absent; compile to an empty, correctly-typed
    relation when neither exists, and dedupe overlaps when both do. -#}
{%- set live = adapter.get_relation(
    database=target.database, schema='raw', identifier='arrivals'
) -%}
{%- set hist = adapter.get_relation(
    database=target.database, schema='raw', identifier='arrivals_history'
) -%}

with unioned as (

    {% if live %}
    select
        icao24,
        callsign,
        est_departure_airport,
        arrival_airport_icao,
        cast(first_seen as bigint) as first_seen,
        cast(last_seen as bigint) as last_seen
    from {{ source('raw', 'arrivals') }}
    {% endif %}

    {% if live and hist %}union all{% endif %}

    {% if hist %}
    select
        icao24,
        callsign,
        est_departure_airport,
        arrival_airport_icao,
        first_seen,
        last_seen
    from {{ source('raw', 'arrivals_history') }}
    {% endif %}

    {% if not live and not hist %}
    select
        cast(null as varchar) as icao24,
        cast(null as varchar) as callsign,
        cast(null as varchar) as est_departure_airport,
        cast(null as varchar) as arrival_airport_icao,
        cast(null as bigint) as first_seen,
        cast(null as bigint) as last_seen
    where false
    {% endif %}

),

deduped as (
    select * from unioned
    qualify row_number() over (
        partition by icao24, arrival_airport_icao, first_seen
        order by last_seen desc
    ) = 1
)

select
    icao24,
    nullif(trim(callsign), '') as callsign,
    est_departure_airport as departure_airport_icao,
    arrival_airport_icao,
    to_timestamp(first_seen) as departed_at,
    to_timestamp(last_seen) as arrived_at
from deduped
