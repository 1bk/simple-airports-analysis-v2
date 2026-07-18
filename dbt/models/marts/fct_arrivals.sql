-- Arrivals per Malaysian airport over the past 7 days (OpenSky flights API).
-- Empty (but valid) when OpenSky credentials are not configured.
select
    arrivals.arrival_airport_icao,
    airports.name as airport_name,
    airports.iata_code,
    count(*) as arrivals_7d,
    round(count(*) / 7.0, 1) as arrivals_per_day,
    min(arrivals.arrived_at) as earliest_arrival,
    max(arrivals.arrived_at) as latest_arrival
from {{ ref('stg_arrivals') }} as arrivals
left join {{ ref('dim_airports_my') }} as airports
    on arrivals.arrival_airport_icao = airports.icao_code
group by arrivals.arrival_airport_icao, airports.name, airports.iata_code
order by arrivals_7d desc
