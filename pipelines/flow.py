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
from prefect import flow, task
from prefect.assets import materialize
from prefect_dbt import PrefectDbtRunner, PrefectDbtSettings

from pipelines.sources import aircraft_states, airports, arrivals, opensky_credentials

logging.basicConfig(level=logging.INFO)

REPO_ROOT = Path(__file__).parent.parent
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "airports.duckdb"))
PUBLIC_DIR = REPO_ROOT / "dashboard" / "public"

# Marts exported for the static (WASM) dashboard, keyed by output filename stem.
DASHBOARD_EXPORTS = {
    "airports_my": "select * from marts.dim_airports_my",
    "distances": "select * from marts.fct_airport_distances",
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


@materialize("duckdb://raw/aircraft_states")
def load_aircraft_states() -> None:
    _load(aircraft_states(), "aircraft_states")


@materialize("duckdb://raw/arrivals")
def load_arrivals() -> None:
    if opensky_credentials():
        _load(arrivals(), "arrivals")
    # Ensure the table always exists so dbt models compile without creds.
    with duckdb.connect(DUCKDB_PATH) as con:
        con.execute("create schema if not exists raw")
        con.execute(
            """
            create table if not exists raw.arrivals (
                icao24 varchar, first_seen bigint, est_departure_airport varchar,
                last_seen bigint, est_arrival_airport varchar, callsign varchar,
                arrival_airport_icao varchar
            )
            """
        )


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
    meta = {
        "generated_at_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "arrivals_available": bool(opensky_credentials()),
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
