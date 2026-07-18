{#- raw.arrivals only exists after a credentialed OpenSky fetch has succeeded;
    compile to an empty, correctly-typed relation until then. -#}
{%- set arrivals_relation = adapter.get_relation(
    database=target.database, schema='raw', identifier='arrivals'
) -%}

{% if arrivals_relation %}

with source as (
    select * from {{ source('raw', 'arrivals') }}
)

select
    icao24,
    nullif(trim(callsign), '') as callsign,
    est_departure_airport as departure_airport_icao,
    arrival_airport_icao,
    to_timestamp(cast(first_seen as bigint)) as departed_at,
    to_timestamp(cast(last_seen as bigint)) as arrived_at
from source

{% else %}

select
    cast(null as varchar) as icao24,
    cast(null as varchar) as callsign,
    cast(null as varchar) as departure_airport_icao,
    cast(null as varchar) as arrival_airport_icao,
    cast(null as timestamp with time zone) as departed_at,
    cast(null as timestamp with time zone) as arrived_at
where false

{% endif %}
