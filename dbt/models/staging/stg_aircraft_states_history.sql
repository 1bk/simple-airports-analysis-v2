{#- raw.aircraft_states_history only exists once the snapshot workflow has
    committed history parquet; compile to an empty typed relation until then. -#}
{%- set hist = adapter.get_relation(
    database=target.database, schema='raw', identifier='aircraft_states_history'
) -%}

{% if hist %}

select
    icao24,
    nullif(trim(callsign), '') as callsign,
    cast(longitude as double) as longitude,
    cast(latitude as double) as latitude,
    cast(on_ground as boolean) as is_on_ground,
    cast(snapshot_ts as bigint) as snapshot_ts,
    to_timestamp(cast(snapshot_ts as bigint)) as snapshot_at,
    source as data_source
from {{ source('raw', 'aircraft_states_history') }}
where latitude is not null and longitude is not null

{% else %}

select
    cast(null as varchar) as icao24,
    cast(null as varchar) as callsign,
    cast(null as double) as longitude,
    cast(null as double) as latitude,
    cast(null as boolean) as is_on_ground,
    cast(null as bigint) as snapshot_ts,
    cast(null as timestamp with time zone) as snapshot_at,
    cast(null as varchar) as data_source
where false

{% endif %}
