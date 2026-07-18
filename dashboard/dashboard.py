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
    arrivals = pl.read_csv(str(_base / "arrivals.csv"))
    meta = pl.read_csv(str(_base / "meta.csv")).row(0, named=True)
    return airports, arrivals, congestion, distances, meta


@app.cell
def _(meta, mo):
    mo.md(
        f"""
    # Malaysian Airports Analysis

    An end-to-end open-source data stack demo: **dlt → DuckDB → dbt → marimo**,
    orchestrated by **Prefect** and deployed as a static WASM site.
    Data generated at **{meta["generated_at_utc"]} UTC** ·
    live-traffic source: **{meta["aircraft_source"]}** ·
    [dbt docs & lineage](dbt-docs/) ·
    [source on GitHub](https://github.com/1bk/simple-airports-analysis-v2)
    """
    )
    return


@app.cell
def _(airports, congestion, distances, mo):
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _top = congestion.row(0, named=True) if congestion.height else None
    _busiest = (
        f"{_top['name']} ({_top['aircraft_within_50km']} aircraft)"
        if _top and _top["aircraft_within_50km"] > 0
        else "quiet right now"
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
def _(mo):
    import json

    try:
        _text = (mo.notebook_location() / "public" / "malaysia.geo.json").read_text()
    except (FileNotFoundError, NotImplementedError, AttributeError, OSError):
        from pyodide.http import open_url

        _text = open_url(str(mo.notebook_location() / "public" / "malaysia.geo.json")).read()
    malaysia_geojson = json.loads(_text)
    return (malaysia_geojson,)


@app.cell
def _(airports, alt, malaysia_geojson, mo):
    _basemap = alt.Chart(alt.Data(values=malaysia_geojson["features"])).mark_geoshape(
        fill="#e8e8e8", stroke="#999"
    )
    _points = (
        alt.Chart(airports)
        .mark_circle(opacity=0.7)
        .encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            color=alt.Color("airport_type:N", title="Type"),
            size=alt.condition(alt.datum.has_scheduled_service, alt.value(140), alt.value(40)),
            tooltip=["name:N", "ident:N", "iata_code:N", "municipality:N", "airport_type:N"],
        )
    )
    _map = (
        (_basemap + _points)
        .project("mercator")
        .properties(
            width=700, height=350, title="Airports of Malaysia (larger = scheduled service)"
        )
    )
    # rendered directly: mo.ui.altair_chart selections don't support geo projections
    _map
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
    darker cells are farther apart.
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
def _(alt, arrivals, meta, mo):
    _heading = mo.md("## 3. How many flights are landing at Malaysian airports?")
    if meta["arrivals_available"] and arrivals.height > 0:
        _table = mo.ui.table(arrivals, selection=None)
        _bars = (
            alt.Chart(arrivals)
            .mark_bar()
            .encode(
                x=alt.X("arrivals_24h:Q", title="Arrivals (24h)"),
                y=alt.Y("airport_name:N", sort="-x", title=None),
                tooltip=["airport_name:N", "iata_code:N", "arrivals_24h:Q"],
            )
            .properties(width=650, title="Arrivals in the last 24h")
        )
        _out = mo.vstack([mo.ui.altair_chart(_bars), _table])
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
def _(mo):
    mo.md("All 34 scheduled-service airports, including those with zero nearby traffic:")
    return


@app.cell
def _(congestion, mo):
    mo.ui.table(congestion, selection=None, page_size=10)
    return


if __name__ == "__main__":
    app.run()
