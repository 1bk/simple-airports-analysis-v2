# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "altair",
#     "polars",
#     "folium",
# ]
# ///

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", app_title="Malaysian Airports Analysis (Classic)")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import polars as pl

    return alt, mo, pl


@app.cell
def _(mo, pl):
    _base = mo.notebook_location() / "public"
    airports = pl.read_csv(str(_base / "airports_my.csv"))
    distances = pl.read_csv(str(_base / "distances.csv"))
    congestion = pl.read_csv(str(_base / "congestion.csv"))
    congestion_history = pl.read_csv(str(_base / "congestion_history.csv"))
    arrivals = pl.read_csv(str(_base / "arrivals.csv"))
    arrivals_daily = pl.read_csv(str(_base / "arrivals_daily.csv"))
    meta = pl.read_csv(str(_base / "meta.csv")).row(0, named=True)
    return airports, arrivals, arrivals_daily, congestion, congestion_history, distances, meta


@app.cell
def _(meta, mo):
    mo.hstack(
        [
            mo.md(
                """
        # Airports Analysis · Classic

        *A compact, grid-style view of the same dataset — see the
        [Q&A walkthrough](../dashboard/) for the narrative version.*
        """
            ),
            mo.md(
                f"<span style='font-size:0.8rem;color:var(--gray-9)'>"
                f"generated {meta['generated_at_utc']} UTC</span>"
            ).right(),
        ],
        justify="space-between",
        align="start",
    )
    return


@app.cell
def _(airports, arrivals, congestion, meta, mo):
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _total_arrivals = arrivals["arrivals_7d"].sum() if meta["arrivals_available"] else 0
    _top = congestion.row(0, named=True) if congestion.height else None
    _busiest = (
        f"{_top['iata_code']} · {_top['aircraft_within_50km']} aircraft"
        if _top and _top["aircraft_within_50km"] > 0
        else "quiet now"
    )
    mo.hstack(
        [
            mo.stat(value=airports.height, label="Airports", bordered=True),
            mo.stat(value=_scheduled, label="Scheduled", bordered=True),
            mo.stat(value=_total_arrivals, label="Arrivals (7d total)", bordered=True),
            mo.stat(value=_busiest, label="Busiest now", bordered=True),
        ],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(mo):
    mo.md("### Airports map")
    return


@app.cell
def _(airports, mo):
    import folium

    _colors = {
        "large_airport": "steelblue",
        "medium_airport": "orange",
        "small_airport": "indianred",
    }
    _map = folium.Map(location=[4.0, 108.5], zoom_start=6, tiles="OpenStreetMap")
    for _row in airports.iter_rows(named=True):
        folium.CircleMarker(
            location=[_row["latitude"], _row["longitude"]],
            radius=9 if _row["has_scheduled_service"] else 5,
            color=_colors.get(_row["airport_type"], "gray"),
            fill=True,
            fill_color=_colors.get(_row["airport_type"], "gray"),
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(
                f"<b>{_row['name']}</b><br>"
                f"IATA: {_row['iata_code'] or '—'}<br>"
                f"{_row['municipality']}<br>"
                f"{_row['airport_type'].replace('_', ' ').title()}",
                max_width=250,
            ),
        ).add_to(_map)
    # rendered via mo.iframe: real OSM tiles, pan/zoom, per-airport popups;
    # centered on Malaysia rather than fit_bounds, so outlying reef/island
    # airports don't zoom the whole map out to a speck
    _airports_table = mo.ui.table(
        airports.select("name", "iata_code", "municipality", "airport_type"),
        selection=None,
        page_size=8,
        label="Airports",
    )
    mo.hstack(
        [
            mo.iframe(_map.get_root().render(), width="480px", height="420px"),
            _airports_table,
        ],
        widths=[1, 1],
        gap=1,
        align="start",
    )
    return


@app.cell
def _(mo):
    mo.md("### Busiest airports right now")
    return


@app.cell
def _(alt, congestion, mo):
    _busy = (
        congestion.filter(congestion["aircraft_within_50km"] > 0)
        .sort("aircraft_within_50km", descending=True)
        .head(10)
    )
    if _busy.height:
        _bars = (
            alt.Chart(_busy)
            .mark_bar()
            .encode(
                x=alt.X("aircraft_within_50km:Q", title="Aircraft within 50 km"),
                y=alt.Y("name:N", sort="-x", title=None),
                color=alt.Color(
                    "aircraft_within_50km:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                tooltip=["name:N", "iata_code:N", "aircraft_within_50km:Q"],
            )
            .properties(width=650, height=260)
        )
        _chart = mo.ui.altair_chart(_bars)
    else:
        _chart = mo.callout(mo.md("No aircraft near any airport in this snapshot."), kind="info")
    _caption = mo.md(
        "*Top 10 scheduled-service airports by live aircraft count within 50 km, "
        "a keyless proxy for current congestion.*"
    )
    mo.vstack([_chart, _caption])
    return


@app.cell
def _(alt, congestion_history, mo, pl):
    if congestion_history.height:
        _active = (
            congestion_history.group_by("iata_code")
            .agg(pl.col("aircraft_within_50km").max().alias("peak"))
            .filter(pl.col("peak") > 0)["iata_code"]
        )
        _trend = (
            alt.Chart(congestion_history.filter(pl.col("iata_code").is_in(_active)))
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("snapshot_at:T", title=None),
                y=alt.Y("aircraft_within_50km:Q", title="Aircraft within 50 km"),
                color=alt.Color(
                    "iata_code:N", title="Airport", scale=alt.Scale(scheme="tableau10")
                ),
                tooltip=["snapshot_at:T", "iata_code:N", "aircraft_within_50km:Q"],
            )
            .properties(width=650, height=220, title="Congestion over time (snapshot history)")
        )
        _out = mo.ui.altair_chart(_trend)
    else:
        _out = mo.md("")  # no history committed yet: skip the section quietly
    _out
    return


@app.cell
def _(mo):
    mo.md("### Arrivals, last 7 days")
    return


@app.cell
def _(alt, arrivals, arrivals_daily, meta, mo):
    if meta["arrivals_available"] and arrivals.height > 0:
        _trend = (
            alt.Chart(arrivals_daily)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("arrival_date:T", title=None),
                y=alt.Y("arrivals:Q", title="Arrivals"),
                color=alt.Color(
                    "iata_code:N", title="Airport", scale=alt.Scale(scheme="tableau10")
                ),
                tooltip=["arrival_date:T", "iata_code:N", "arrivals:Q"],
            )
            .properties(width=650, height=220, title="Daily arrivals by airport")
        )
        _bars = (
            alt.Chart(arrivals)
            .mark_bar()
            .encode(
                x=alt.X("arrivals_7d:Q", title="Arrivals (7 days)"),
                y=alt.Y("airport_name:N", sort="-x", title=None),
                color=alt.Color("arrivals_7d:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=["airport_name:N", "iata_code:N", "arrivals_7d:Q", "arrivals_per_day:Q"],
            )
            .properties(width=650, height=220, title="Total arrivals per airport")
        )
        _table = mo.ui.table(arrivals, selection=None, page_size=10, label="Arrivals detail")
        _out = mo.vstack([mo.ui.altair_chart(_trend), mo.ui.altair_chart(_bars), _table])
    else:
        _out = mo.callout(
            mo.md(
                "**Arrivals history needs OpenSky credentials.** This keyless build skips "
                "it gracefully — set `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` (free "
                "account at [opensky-network.org](https://opensky-network.org)) and re-run "
                "the pipeline to light this section up."
            ),
            kind="info",
        )
    _out
    return


@app.cell
def _(mo):
    mo.md("### Distance matrix (km)")
    return


@app.cell
def _(distances, mo, pl):
    _iata_names = dict(
        zip(distances["iata_a"].to_list(), distances["airport_a_name"].to_list(), strict=True)
    )
    _iata_names.update(
        zip(distances["iata_b"].to_list(), distances["airport_b_name"].to_list(), strict=True)
    )
    _symmetric = pl.concat(
        [
            distances.select(
                pl.col("iata_a").alias("from_iata"),
                pl.col("iata_b").alias("to_iata"),
                "distance_km",
            ),
            distances.select(
                pl.col("iata_b").alias("from_iata"),
                pl.col("iata_a").alias("to_iata"),
                "distance_km",
            ),
        ]
    )
    _matrix = _symmetric.pivot(on="to_iata", index="from_iata", values="distance_km").sort(
        "from_iata"
    )
    _table = mo.ui.table(_matrix, selection=None, page_size=10, label="Distance matrix (km)")
    _caption = mo.md(
        "*Great-circle distance in km between every pair of scheduled-service "
        "airports, by IATA code.*"
    )
    mo.vstack([_table, _caption])
    return


if __name__ == "__main__":
    app.run()
