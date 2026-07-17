with source as (
    select * from {{ source('raw', 'aircraft_states') }}
)

select
    icao24,
    nullif(trim(callsign), '') as callsign,
    origin_country,
    cast(longitude as double) as longitude,
    cast(latitude as double) as latitude,
    cast(baro_altitude as double) as baro_altitude_m,
    cast(on_ground as boolean) as is_on_ground,
    cast(velocity as double) as velocity_ms,
    cast(snapshot_ts as bigint) as snapshot_ts,
    to_timestamp(cast(snapshot_ts as bigint)) as snapshot_at,
    source as data_source
from source
where latitude is not null and longitude is not null
