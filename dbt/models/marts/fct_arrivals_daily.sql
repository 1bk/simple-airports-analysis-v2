-- Daily arrivals per Malaysian airport over the fetched window (question 3
-- over time). Empty (but valid) without OpenSky credentials.
select
    arrivals.arrival_airport_icao,
    airports.name as airport_name,
    airports.iata_code,
    cast(arrivals.arrived_at as date) as arrival_date,
    count(*) as arrivals
from {{ ref('stg_arrivals') }} as arrivals
left join {{ ref('dim_airports_my') }} as airports
    on arrivals.arrival_airport_icao = airports.icao_code
group by
    arrivals.arrival_airport_icao,
    airports.name,
    airports.iata_code,
    cast(arrivals.arrived_at as date)
order by arrival_date asc, arrivals desc
