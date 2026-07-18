"""Snapshot collector: merge live aircraft states + 7-day arrivals into committed Parquet.

Run on a schedule by .github/workflows/snapshot.yml (and locally via `make snapshot`).
Each run deduplicates new rows into history/*.parquet, so the repo accumulates a
time series (last-known-good pattern) and deploys never depend on OpenSky being
reachable from CI runners. The committed sample seed is never written to history.
"""

import logging
import time
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from pipelines.sources import _states_from_adsblol, _states_from_opensky, arrivals

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
HISTORY_DIR = REPO_ROOT / "history"

STATE_COLUMNS = {
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
    "collected_at": "bigint",
}

ARRIVAL_COLUMNS = {
    "icao24": "varchar",
    "callsign": "varchar",
    "est_departure_airport": "varchar",
    "arrival_airport_icao": "varchar",
    "first_seen": "bigint",
    "last_seen": "bigint",
    "collected_at": "bigint",
}


def _fetch_states() -> list[dict]:
    # Same chain as the pipeline, minus the sample seed: history holds real data only.
    for fetch in (_states_from_opensky, _states_from_adsblol):
        try:
            rows = fetch()
            if rows:
                log.info("states: %d rows via %s", len(rows), fetch.__name__)
                return rows
        except Exception as exc:  # noqa: BLE001 - fall through the chain by design
            log.warning("states: %s failed (%s), trying next", fetch.__name__, exc)
    return []


def _fetch_arrivals() -> list[dict]:
    try:
        rows = []
        for flight in arrivals():  # dlt resources are plain iterables
            rows.append(
                {
                    "icao24": flight.get("icao24"),
                    "callsign": (flight.get("callsign") or "").strip() or None,
                    "est_departure_airport": flight.get("estDepartureAirport"),
                    "arrival_airport_icao": flight.get("arrival_airport_icao"),
                    "first_seen": flight.get("firstSeen"),
                    "last_seen": flight.get("lastSeen"),
                }
            )
        log.info("arrivals: %d rows fetched", len(rows))
        return rows
    except Exception as exc:  # noqa: BLE001 - best-effort, states may still succeed
        log.warning("arrivals fetch failed (%s)", exc)
        return []


def _merge(rows: list[dict], columns: dict, path: Path, key: list[str]) -> int:
    """Union new rows with the existing parquet, keep newest per key, rewrite. Returns growth."""
    collected_at = int(time.time())
    for row in rows:
        row["collected_at"] = collected_at
    with duckdb.connect() as con:
        con.execute(f"create table incoming ({', '.join(f'{c} {t}' for c, t in columns.items())})")
        con.executemany(
            f"insert into incoming values ({', '.join('?' for _ in columns)})",
            [[row.get(c) for c in columns] for row in rows],
        )
        before = 0
        if path.exists():
            before = con.execute(f"select count(*) from read_parquet('{path}')").fetchone()[0]
            con.execute(f"insert into incoming select * from read_parquet('{path}')")
        keys = ", ".join(key)
        after = con.execute(
            f"""
            copy (
                select * from incoming
                qualify row_number() over (partition by {keys} order by collected_at desc) = 1
                order by {keys}
            ) to '{path}' (format parquet, compression zstd)
            """
        ).fetchone()[0]
    return after - before


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")  # optional local secrets, see .env.example
    HISTORY_DIR.mkdir(exist_ok=True)
    states = _fetch_states()
    if states:
        grew = _merge(
            states,
            STATE_COLUMNS,
            HISTORY_DIR / "aircraft_states.parquet",
            ["icao24", "snapshot_ts"],
        )
        log.info("aircraft_states history: +%d rows", grew)
    arrival_rows = _fetch_arrivals()
    if arrival_rows:
        grew = _merge(
            arrival_rows,
            ARRIVAL_COLUMNS,
            HISTORY_DIR / "arrivals.parquet",
            ["icao24", "arrival_airport_icao", "first_seen"],
        )
        log.info("arrivals history: +%d rows", grew)
    if not states and not arrival_rows:
        # exit 0 anyway: runners are known to be blocked by OpenSky sometimes;
        # the workflow simply has nothing to commit this round
        log.warning("nothing fetched this run - history unchanged")


if __name__ == "__main__":
    main()
