-- Question 4 over time: aircraft within 50 km of each scheduled-service airport,
-- per committed history snapshot (collected by the scheduled snapshot workflow).
-- Empty until history/aircraft_states.parquet exists.
with airports as (
    select * from {{ ref('dim_airports_my') }}
    where has_scheduled_service
),

states as (
    select * from {{ ref('stg_aircraft_states_history') }}
),

paired as (
    select
        airports.ident,
        airports.name,
        airports.iata_code,
        states.snapshot_at,
        states.is_on_ground,
        {{ haversine_km(
            'airports.latitude', 'airports.longitude',
            'states.latitude', 'states.longitude'
        ) }} as distance_km
    from airports
    cross join states
)

select
    ident,
    name,
    iata_code,
    snapshot_at,
    count(*) filter (where distance_km <= 50) as aircraft_within_50km,
    count(*) filter (where distance_km <= 50 and not is_on_ground) as aircraft_airborne
from paired
group by ident, name, iata_code, snapshot_at
order by snapshot_at asc, aircraft_within_50km desc
