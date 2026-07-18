"""End-to-end ELT flow: dlt extract/load -> DuckDB -> dbt build -> dashboard data export.

Runs headless (no Prefect server needed): `uv run python -m pipelines.flow`.
"""

import csv
import logging
import os
import time
from pathlib import Path

import dlt
import duckdb
from dotenv import load_dotenv
from prefect import flow, task
from prefect.assets import materialize
from prefect_dbt import PrefectDbtRunner, PrefectDbtSettings

from pipelines.sources import aircraft_states, airports, arrivals, opensky_credentials

logging.basicConfig(level=logging.INFO)

REPO_ROOT = Path(__file__).parent.parent
load_dotenv(REPO_ROOT / ".env")  # optional local secrets, see .env.example
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "airports.duckdb"))
PUBLIC_DIR = REPO_ROOT / "dashboard" / "public"

# Marts exported for the static (WASM) dashboard, keyed by output filename stem.
DASHBOARD_EXPORTS = {
    "airports_my": "select * from marts.dim_airports_my",
    "distances": """
        select
            d.*,
            coalesce(nullif(a.iata_code, ''), d.airport_a) as iata_a,
            coalesce(nullif(b.iata_code, ''), d.airport_b) as iata_b
        from marts.fct_airport_distances as d
        left join marts.dim_airports_my as a on d.airport_a = a.ident
        left join marts.dim_airports_my as b on d.airport_b = b.ident
    """,
    "congestion": "select * from marts.fct_congestion",
    "arrivals": "select * from marts.fct_arrivals",
}


def _load(resource, asset_name: str) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="airports_v2",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw",
    )
    info = pipeline.run(resource)
    logging.info("loaded %s: %s", asset_name, info)


@materialize("duckdb://raw/airports")
def load_airports() -> None:
    _load(airports(), "airports")


# dlt drops all-null columns, and the fallback sources omit some fields —
# guarantee the columns dbt expects so staging models always compile.
EXPECTED_STATE_COLUMNS = {
    "icao24": "varchar",
    "callsign": "varchar",
    "origin_country": "varchar",
    "longitude": "double",
    "latitude": "double",
    "baro_altitude": "double",
    "on_ground": "boolean",
    "velocity": "double",
    "snapshot_ts": "bigint",
    "source": "varchar",
}


@materialize("duckdb://raw/aircraft_states")
def load_aircraft_states() -> None:
    _load(aircraft_states(), "aircraft_states")
    with duckdb.connect(DUCKDB_PATH) as con:
        for col, typ in EXPECTED_STATE_COLUMNS.items():
            con.execute(f"alter table raw.aircraft_states add column if not exists {col} {typ}")


ARRIVALS_SCHEMA_DDL = """
    create table {exists_clause} raw.arrivals (
        icao24 varchar, first_seen bigint, est_departure_airport varchar,
        last_seen bigint, est_arrival_airport varchar, callsign varchar,
        arrival_airport_icao varchar
    )
"""


@materialize("duckdb://raw/arrivals")
def load_arrivals() -> None:
    # Always drop first: a credential-less run must not keep stale rows from a
    # previous credentialed run, and dlt must create its own table on load —
    # pre-creating an empty one makes dlt ALTER in its internal NOT NULL
    # columns, which DuckDB rejects.
    with duckdb.connect(DUCKDB_PATH) as con:
        con.execute("create schema if not exists raw")
        con.execute("drop table if exists raw.arrivals")
    if opensky_credentials():
        try:
            _load(arrivals(), "arrivals")
        except Exception:
            # Best-effort source: an OpenSky outage must not fail the pipeline —
            # dashboards degrade to the "no arrivals data" state instead.
            logging.warning("arrivals load failed - continuing with empty table", exc_info=True)
    # Ensure the table exists for dbt when there were no creds (or zero rows).
    with duckdb.connect(DUCKDB_PATH) as con:
        con.execute(ARRIVALS_SCHEMA_DDL.format(exists_clause="if not exists"))


@task
def dbt_build() -> None:
    settings = PrefectDbtSettings(
        project_dir=str(REPO_ROOT / "dbt"), profiles_dir=str(REPO_ROOT / "dbt")
    )
    PrefectDbtRunner(settings=settings).invoke(["build"])


@task
def export_dashboard_data() -> None:
    """Bake small mart extracts as CSV + metadata for the static WASM dashboard."""
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    # not read_only: dbt's in-process connection holds the file with different config
    with duckdb.connect(DUCKDB_PATH) as con:
        for name, query in DASHBOARD_EXPORTS.items():
            con.execute(f"copy ({query}) to '{PUBLIC_DIR / name}.csv' (header, delimiter ',')")
        states_source = con.execute("select distinct source from raw.aircraft_states").fetchall()
        arrivals_rows = con.execute("select count(*) from marts.fct_arrivals").fetchone()[0]
    meta = {
        "generated_at_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        # actual data presence, not just credentials - the fetch is best-effort
        "arrivals_available": arrivals_rows > 0,
        "aircraft_source": states_source[0][0] if states_source else "unknown",
    }
    with open(PUBLIC_DIR / "meta.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(meta))
        writer.writeheader()
        writer.writerow(meta)


@flow(name="airports-v2-elt", log_prints=True)
def elt() -> None:
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    load_airports()
    load_aircraft_states()
    load_arrivals()
    dbt_build()
    export_dashboard_data()


if __name__ == "__main__":
    elt()
