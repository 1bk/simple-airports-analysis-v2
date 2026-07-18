"""dlt resources: airports (OurAirports), live aircraft snapshot, optional arrivals.

All sources are keyless except OpenSky arrivals history, which activates only
when OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET are set.
"""

import csv
import io
import logging
import os
import time
from pathlib import Path

import dlt
import requests

log = logging.getLogger(__name__)

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)
OPENSKY_ARRIVALS_URL = "https://opensky-network.org/api/flights/arrival"
ADSBLOL_URL = "https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{dist}"

# Bounding box covering Peninsular + East Malaysia
MY_BBOX = {"lamin": 0.8, "lomin": 99.6, "lamax": 7.4, "lomax": 119.3}

# Fallback query centres for adsb.lol (250 nm radius each): KUL, Kuching, Kota Kinabalu
ADSBLOL_CENTRES = [(2.74, 101.70), (1.48, 110.34), (5.94, 116.05)]

# Major Malaysian international airports polled for arrivals (when creds exist)
ARRIVAL_AIRPORTS_ICAO = ["WMKK", "WMKP", "WMKJ", "WBKK", "WBGG", "WMKL"]

SAMPLE_STATES_CSV = Path(__file__).parent.parent / "seeds" / "sample_aircraft_states.csv"

OPENSKY_STATE_FIELDS = [
    "icao24",
    "callsign",
    "origin_country",
    "time_position",
    "last_contact",
    "longitude",
    "latitude",
    "baro_altitude",
    "on_ground",
    "velocity",
    "true_track",
    "vertical_rate",
    "sensors",
    "geo_altitude",
    "squawk",
    "spi",
    "position_source",
]


@dlt.resource(name="airports", write_disposition="replace")
def airports():
    """Full OurAirports airport catalogue (keyless, ~80k rows)."""
    resp = requests.get(OURAIRPORTS_URL, timeout=60)
    resp.raise_for_status()
    yield from csv.DictReader(io.StringIO(resp.text))


def _states_from_opensky() -> list[dict]:
    resp = requests.get(OPENSKY_STATES_URL, params=MY_BBOX, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    snapshot_ts = payload.get("time") or int(time.time())
    rows = []
    for state in payload.get("states") or []:
        # strict=False: OpenSky may append fields (e.g. category); extras are dropped
        row = dict(zip(OPENSKY_STATE_FIELDS, state, strict=False))
        row.pop("sensors", None)  # nested & always null anonymously
        row["snapshot_ts"] = snapshot_ts
        row["source"] = "opensky"
        rows.append(row)
    return rows


def _states_from_adsblol() -> list[dict]:
    rows, seen = [], set()
    snapshot_ts = int(time.time())
    for lat, lon in ADSBLOL_CENTRES:
        resp = requests.get(ADSBLOL_URL.format(lat=lat, lon=lon, dist=250), timeout=30)
        resp.raise_for_status()
        for ac in resp.json().get("ac") or []:
            hexid = ac.get("hex")
            if hexid in seen or ac.get("lat") is None:
                continue
            seen.add(hexid)
            # adsb.lol/readsb reports alt_baro in feet and gs in knots, while
            # downstream (OpenSky-shaped) columns expect metres and m/s.
            alt_baro = ac.get("alt_baro")
            gs = ac.get("gs")
            rows.append(
                {
                    "icao24": hexid,
                    "callsign": (ac.get("flight") or "").strip(),
                    "origin_country": None,
                    "longitude": ac.get("lon"),
                    "latitude": ac.get("lat"),
                    "baro_altitude": alt_baro * 0.3048 if alt_baro != "ground" else 0,
                    "on_ground": alt_baro == "ground",
                    "velocity": gs * 0.514444 if gs is not None else None,
                    "snapshot_ts": snapshot_ts,
                    "source": "adsb.lol",
                }
            )
    return rows


def _states_from_sample() -> list[dict]:
    with open(SAMPLE_STATES_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["source"] = "sample"
    return rows


@dlt.resource(name="aircraft_states", write_disposition="replace")
def aircraft_states():
    """Snapshot of live aircraft over Malaysia: OpenSky -> adsb.lol -> committed sample."""
    for fetch in (_states_from_opensky, _states_from_adsblol, _states_from_sample):
        try:
            rows = fetch()
            if rows:
                log.info("aircraft_states: %d rows via %s", len(rows), fetch.__name__)
                yield from rows
                return
        except Exception as exc:  # noqa: BLE001 - fall through the chain by design
            log.warning("aircraft_states: %s failed (%s), trying next", fetch.__name__, exc)
    raise RuntimeError("all aircraft state sources failed, including committed sample")


def opensky_credentials() -> tuple[str, str] | None:
    cid = os.environ.get("OPENSKY_CLIENT_ID")
    secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    return (cid, secret) if cid and secret else None


# OpenSky's arrivals endpoint caps each request at a 7-day interval
ARRIVALS_WINDOW_SECONDS = 7 * 86400


@dlt.resource(name="arrivals", write_disposition="replace")
def arrivals():
    """Arrivals over the past 7 days at major MY airports.

    Requires OpenSky credentials; skips gracefully otherwise.
    """
    creds = opensky_credentials()
    if not creds:
        log.info("arrivals: no OpenSky credentials set, skipping (dashboards degrade gracefully)")
        return
    cid, secret = creds
    token_resp = requests.post(
        OPENSKY_TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": cid, "client_secret": secret},
        timeout=30,
    )
    token_resp.raise_for_status()
    headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}
    end = int(time.time())
    begin = end - ARRIVALS_WINDOW_SECONDS
    for icao in ARRIVAL_AIRPORTS_ICAO:
        resp = requests.get(
            OPENSKY_ARRIVALS_URL,
            params={"airport": icao, "begin": begin, "end": end},
            headers=headers,
            timeout=60,
        )
        if resp.status_code == 404:  # no flights found for this airport/window
            continue
        resp.raise_for_status()
        for flight in resp.json():
            flight["arrival_airport_icao"] = icao
            yield flight
