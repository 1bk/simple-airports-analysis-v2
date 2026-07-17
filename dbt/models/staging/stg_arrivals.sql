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
