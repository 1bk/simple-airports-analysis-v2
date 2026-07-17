{% macro haversine_km(lat1, lon1, lat2, lon2) -%}
    6371.0 * 2 * asin(sqrt(
        pow(sin(radians(({{ lat2 }}) - ({{ lat1 }})) / 2), 2)
        + cos(radians({{ lat1 }})) * cos(radians({{ lat2 }}))
        * pow(sin(radians(({{ lon2 }}) - ({{ lon1 }})) / 2), 2)
    ))
{%- endmacro %}
