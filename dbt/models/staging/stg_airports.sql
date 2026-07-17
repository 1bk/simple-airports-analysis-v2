with source as (
    select * from {{ source('raw', 'airports') }}
)

select
    cast(id as integer) as airport_id,
    ident,
    type as airport_type,
    name,
    try_cast(latitude_deg as double) as latitude,
    try_cast(longitude_deg as double) as longitude,
    try_cast(elevation_ft as integer) as elevation_ft,
    continent,
    iso_country,
    iso_region,
    municipality,
    scheduled_service = 'yes' as has_scheduled_service,
    icao_code,
    iata_code
from source
where type in ('large_airport', 'medium_airport', 'small_airport')
