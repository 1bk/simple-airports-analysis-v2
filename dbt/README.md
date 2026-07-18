# dbt project — Simple Airports Analysis v2

Transforms the raw tables loaded by dlt (`raw.airports`, `raw.aircraft_states`,
`raw.arrivals`) into staging views and marts in DuckDB, answering the four
analysis questions:

1. How many airports are there in Malaysia?
2. What is the distance between the airports in Malaysia?
3. How many flights are landing at Malaysian airports?
4. Which airport is the most congested?

## Layer conventions

- **staging** (`models/staging/`) — one view per source table, materialized as
  `view`. Casts types, renames columns, drops obviously unusable rows (e.g.
  missing coordinates). No business logic, no joins.
- **marts** (`models/marts/`) — `table`-materialized models with the actual
  business logic: filtering to Malaysia, joining airports to live aircraft,
  computing distances, aggregating arrivals.
- **Schema names are literal.** The custom `generate_schema_name` macro
  (`macros/generate_schema_name.sql`) ignores dbt's default target-prefixing
  behaviour, so models always land in `staging` and `marts` — never
  `dev_staging` or similar — regardless of the target name.
- **`haversine_km(lat1, lon1, lat2, lon2)`** (`macros/haversine_km.sql`) —
  great-circle distance in kilometres, used by both `fct_airport_distances`
  and `fct_congestion`.

## Models

| Model | Layer | Answers / contains |
|---|---|---|
| `stg_airports` | staging | Cleaned OurAirports catalogue, restricted to large/medium/small airports (heliports and seaplane bases dropped) |
| `stg_aircraft_states` | staging | One row per aircraft in the live snapshot over Malaysia, with a valid position |
| `stg_arrivals` | staging | Arrivals at major Malaysian airports over the past 24h (empty without OpenSky credentials) |
| `dim_airports_my` | marts | All Malaysian airports — question 1 |
| `fct_airport_distances` | marts | Pairwise haversine distance between every pair of Malaysian airports with scheduled service — question 2 |
| `fct_congestion` | marts | Count of live aircraft within 50km of each scheduled-service Malaysian airport — question 4, a keyless proxy for arrivals |
| `fct_arrivals` | marts | Arrivals per Malaysian airport over the past 24h from the OpenSky flights API — question 3 |

## Running standalone

Normally dbt is invoked as part of the Prefect flow (`python -m
pipelines.flow`), which runs `dbt deps` then builds the models in-process via
`PrefectDbtRunner` so each model surfaces as a Prefect asset with lineage.
`make all` / `make pipeline` from the repo root drive this end to end.

To run dbt directly instead, from the repo root:

```sh
uv run dbt deps --project-dir dbt --profiles-dir dbt
uv run dbt build --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
```

The DuckDB file path is controlled by the `DUCKDB_PATH` env var (default
`data/airports.duckdb`), created by `make pipeline` (dlt extract/load must run
first — the raw tables need to exist before dbt can build on top of them).

## Testing

- `unique` / `not_null` on natural keys (`airport_id`, `ident`, `icao24`,
  `arrival_airport_icao`).
- `accepted_values` on categorical columns (`airport_type`, `data_source`).
- `dbt_utils.accepted_range` on `fct_airport_distances.distance_km` (0–5000km)
  as a sanity bound on the haversine calculation.

Tests focus on the transformation logic rather than raw input shape: the dlt
loader guarantees the raw tables' schema (see the root README and
`pipelines/`), so staging models don't re-test source columns for existence.
`stg_arrivals` / `fct_arrivals` are allowed to be empty — that's the expected,
valid state when OpenSky credentials aren't configured — so tests here assert
uniqueness/non-null on the columns that matter rather than row counts.

## More

- [Root README](../README.md) — full pipeline, architecture, and quickstart.
- [Hosted dbt docs & lineage graph](https://1bk.dev/simple-airports-analysis-v2/dbt-docs/).
