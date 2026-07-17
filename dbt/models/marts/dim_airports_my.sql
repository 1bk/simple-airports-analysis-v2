select
    airport_id,
    ident,
    airport_type,
    name,
    latitude,
    longitude,
    elevation_ft,
    iso_region,
    municipality,
    has_scheduled_service,
    icao_code,
    iata_code
from {{ ref('stg_airports') }}
where iso_country = 'MY'
