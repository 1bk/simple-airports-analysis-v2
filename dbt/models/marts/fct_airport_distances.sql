-- Pairwise great-circle distances between Malaysian airports with scheduled service.
with scheduled as (
    select * from {{ ref('dim_airports_my') }}
    where has_scheduled_service
)

select
    a.ident as airport_a,
    a.name as airport_a_name,
    b.ident as airport_b,
    b.name as airport_b_name,
    round({{ haversine_km('a.latitude', 'a.longitude', 'b.latitude', 'b.longitude') }}, 1)
        as distance_km
from scheduled as a
inner join scheduled as b
    on a.ident < b.ident
