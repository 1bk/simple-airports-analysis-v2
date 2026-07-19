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
app = marimo.App(width="medium", app_title="Malaysian Airports Analysis")


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
    mo.md(
        f"""
    # Malaysian Airports Analysis

    An end-to-end open-source data stack demo: **dlt → DuckDB → dbt → marimo**,
    orchestrated by **Prefect** and deployed as a static WASM site.
    Data generated at **{meta["generated_at_utc"]} UTC** ·
    live-traffic source: **{meta["aircraft_source"]}** ·
    [project overview](../) ·
    [classic dashboard](../classic/) ·
    [chat with the data](../chat/) ·
    [dbt docs & lineage](../dbt-docs/) ·
    [source on GitHub](https://github.com/1bk/simple-airports-analysis-v2)
    """
    )
    return


@app.cell
def _(airports, congestion, distances, mo):
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _top = congestion.row(0, named=True) if congestion.height else None
    _busiest = (
        f"{_top['iata_code']} · {_top['aircraft_within_50km']} aircraft"
        if _top and _top["aircraft_within_50km"] > 0
        else "quiet now"
    )
    mo.hstack(
        [
            mo.stat(value=airports.height, label="Airports", bordered=True),
            mo.stat(value=_scheduled, label="Scheduled service", bordered=True),
            mo.stat(value=distances.height, label="Distance pairs", bordered=True),
            mo.stat(value=_busiest, label="Busiest airport now", bordered=True),
        ],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(airports, mo):
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    mo.md(
        f"""
    ## 1. How many airports are there in Malaysia?

    **{airports.height} airports** (large, medium, or small), of which
    **{_scheduled}** have scheduled commercial service.
    """
    )
    return


@app.cell
def _(airports, mo):
    import folium

    _colors = {
        "large_airport": "steelblue",
        "medium_airport": "orange",
        "small_airport": "indianred",
    }
    _map = folium.Map(tiles="OpenStreetMap")
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
    _map.fit_bounds(
        [
            [airports["latitude"].min(), airports["longitude"].min()],
            [airports["latitude"].max(), airports["longitude"].max()],
        ]
    )
    # rendered via mo.iframe: real OSM tiles, pan/zoom, per-airport popups
    mo.iframe(_map.get_root().render(), height="450px")
    return


@app.cell
def _(distances, mo):
    mo.md(
        f"""
    ## 2. What is the distance between the airports?

    Pairwise great-circle (haversine) distances between the scheduled-service airports —
    **{distances.height} pairs**. Pick an airport to see how far everything else is.
    """
    )
    return


@app.cell
def _(distances, mo, pl):
    _names = sorted(
        set(distances["airport_a_name"].to_list()) | set(distances["airport_b_name"].to_list())
    )
    airport_picker = mo.ui.dropdown(
        options=_names, value="Kuala Lumpur International Airport", label="From airport"
    )
    airport_picker
    return (airport_picker,)


@app.cell
def _(airport_picker, distances, mo, pl):
    _sel = airport_picker.value
    _from = (
        distances.filter((pl.col("airport_a_name") == _sel) | (pl.col("airport_b_name") == _sel))
        .with_columns(
            pl.when(pl.col("airport_a_name") == _sel)
            .then(pl.col("airport_b_name"))
            .otherwise(pl.col("airport_a_name"))
            .alias("to_airport")
        )
        .select("to_airport", "distance_km")
        .sort("distance_km")
    )
    mo.ui.table(_from, selection=None, page_size=10)
    return


@app.cell
def _(mo):
    mo.md(
        """
    ### Full distance matrix

    Every scheduled-service airport against every other, by IATA code —
    brighter (yellow) cells are farther apart, darker cells are closer.
    """
    )
    return


@app.cell
def _(alt, distances, mo, pl):
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
    ).with_columns(
        pl.col("from_iata").replace(_iata_names).alias("from_name"),
        pl.col("to_iata").replace(_iata_names).alias("to_name"),
    )
    _order = sorted(_iata_names)
    _heatmap = (
        alt.Chart(_symmetric)
        .mark_rect()
        .encode(
            x=alt.X("to_iata:N", title="To", sort=_order),
            y=alt.Y("from_iata:N", title="From", sort=_order),
            color=alt.Color("distance_km:Q", title="km", scale=alt.Scale(scheme="viridis")),
            tooltip=["from_name:N", "to_name:N", "distance_km:Q"],
        )
        .properties(width=640, height=640, title="Distance matrix (km)")
    )
    mo.ui.altair_chart(_heatmap)
    return


@app.cell
def _(alt, arrivals, arrivals_daily, meta, mo):
    _heading = mo.md(
        "## 3. How many flights are landing at Malaysian airports?\n\n"
        "Looking at the last **7 days** of arrivals."
    )
    if meta["arrivals_available"] and arrivals.height > 0:
        _table = mo.ui.table(arrivals, selection=None)
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
                tooltip=["airport_name:N", "iata_code:N", "arrivals_7d:Q"],
            )
            .properties(width=650, title="Arrivals in the last 7 days")
        )
        _out = mo.vstack([mo.ui.altair_chart(_trend), mo.ui.altair_chart(_bars), _table])
    else:
        _out = mo.callout(
            mo.md(
                "**Arrivals history needs OpenSky credentials.** This keyless build skips "
                "it gracefully — set `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` (free "
                "account at [opensky-network.org](https://opensky-network.org)) and re-run "
                "the pipeline to light this section up. Question 4 below answers congestion "
                "without any credentials."
            ),
            kind="info",
        )
    mo.vstack([_heading, _out])
    return


@app.cell
def _(congestion, meta, mo):
    _top = congestion.row(0, named=True) if congestion.height else None
    _headline = (
        f"**{_top['name']} ({_top['iata_code']})** is the busiest right now with "
        f"**{_top['aircraft_within_50km']} aircraft** within 50 km."
        if _top
        else "No aircraft near any airport in this snapshot."
    )
    mo.md(
        f"""
    ## 4. Which airport is most congested?

    Keyless congestion proxy: live aircraft within 50 km of each scheduled-service airport,
    snapshotted from **{meta["aircraft_source"]}** at pipeline run time. {_headline}
    """
    )
    return


@app.cell
def _(alt, congestion, mo):
    _busy = congestion.filter(congestion["aircraft_within_50km"] > 0)
    if _busy.height:
        _bars = (
            alt.Chart(_busy)
            .mark_bar()
            .encode(
                x=alt.X("aircraft_within_50km:Q", title="Aircraft within 50 km"),
                y=alt.Y("name:N", sort="-x", title=None),
                color=alt.Color(
                    "aircraft_airborne:Q", title="Airborne", scale=alt.Scale(scheme="blues")
                ),
                tooltip=[
                    "name:N",
                    "aircraft_within_50km:Q",
                    "aircraft_on_ground:Q",
                    "aircraft_airborne:Q",
                ],
            )
            .properties(width=650, title="Live aircraft near Malaysian airports")
        )
        _chart = mo.ui.altair_chart(_bars)
    else:
        _chart = mo.callout(mo.md("No aircraft near any airport in this snapshot."), kind="info")
    _chart
    return


@app.cell
def _(alt, congestion_history, mo, pl):
    _heading = mo.md(
        "### Congestion over time\n\n"
        "A scheduled workflow snapshots live traffic into committed Parquet, so the "
        "50 km congestion proxy becomes a time series that grows with every run."
    )
    if congestion_history.height:
        # keep the chart legible: only airports that ever saw traffic
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
            .properties(width=650, height=240, title="Aircraft near each airport, by snapshot")
        )
        _out = mo.ui.altair_chart(_trend)
    else:
        _out = mo.callout(
            mo.md("No snapshot history committed yet — the scheduled workflow fills this in."),
            kind="info",
        )
    mo.vstack([_heading, _out])
    return


@app.cell
def _(mo):
    mo.md("All 34 scheduled-service airports, including those with zero nearby traffic:")
    return


@app.cell
def _(congestion, mo):
    mo.ui.table(congestion, selection=None, page_size=10)
    return


if __name__ == "__main__":
    app.run()
