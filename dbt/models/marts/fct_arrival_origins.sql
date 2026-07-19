-- Arrival origins (extends question 3): one row per (arrival airport, origin
-- airport, arrival date), for flights where OpenSky could determine
-- est_departure_airport (~45% of arrivals; the rest have a NULL origin because
-- OpenSky couldn't establish it — excluded here, not because they didn't fly).
-- Origin metadata comes from stg_airports, which is worldwide (only
-- type-filtered, not country-filtered), so this joins international and
-- domestic origins alike.
select
    arrivals.arrival_airport_icao,
    dest.name as arrival_airport_name,
    cast(arrivals.arrived_at as date) as arrival_date,
    arrivals.departure_airport_icao as origin_ident,
    origin.name as origin_name,
    origin.iso_country as origin_country,
    origin.municipality as origin_municipality,
    origin.iso_country != 'MY' as is_international,
    count(*) as flights
from {{ ref('stg_arrivals') }} as arrivals
inner join {{ ref('stg_airports') }} as origin
    on arrivals.departure_airport_icao = origin.ident
left join {{ ref('dim_airports_my') }} as dest
    on arrivals.arrival_airport_icao = dest.icao_code
where arrivals.departure_airport_icao is not null
group by
    arrivals.arrival_airport_icao,
    dest.name,
    cast(arrivals.arrived_at as date),
    arrivals.departure_airport_icao,
    origin.name,
    origin.iso_country,
    origin.municipality,
    origin.iso_country != 'MY'
order by arrival_date asc, flights desc
