-- Congestion proxy: live aircraft within 50 km of each scheduled-service Malaysian
-- airport at snapshot time. A keyless alternative to arrivals history.
with airports as (
    select * from {{ ref('dim_airports_my') }}
    where has_scheduled_service
),

aircraft as (
    select * from {{ ref('stg_aircraft_states') }}
),

paired as (
    select
        airports.ident,
        airports.name,
        airports.iata_code,
        aircraft.icao24,
        aircraft.is_on_ground,
        aircraft.snapshot_at,
        aircraft.data_source,
        {{ haversine_km(
            'airports.latitude', 'airports.longitude',
            'aircraft.latitude', 'aircraft.longitude'
        ) }} as distance_km
    from airports
    cross join aircraft
)

select
    ident,
    name,
    iata_code,
    count(*) filter (where distance_km <= 50) as aircraft_within_50km,
    count(*) filter (where distance_km <= 50 and is_on_ground) as aircraft_on_ground,
    count(*) filter (where distance_km <= 50 and not is_on_ground) as aircraft_airborne,
    max(snapshot_at) as snapshot_at,
    max(data_source) as data_source
from paired
group by ident, name, iata_code
order by aircraft_within_50km desc
