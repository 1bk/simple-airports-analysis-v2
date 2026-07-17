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
def _(airports, alt, mo):
    _map = (
        alt.Chart(airports)
        .mark_circle(opacity=0.7)
        .encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            color=alt.Color("airport_type:N", title="Type"),
            size=alt.condition(alt.datum.has_scheduled_service, alt.value(140), alt.value(40)),
            tooltip=["name:N", "ident:N", "iata_code:N", "municipality:N", "airport_type:N"],
        )
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
def _(arrivals, meta, mo):
    mo.md("## 3. How many flights are landing at Malaysian airports?")
    if meta["arrivals_available"] and arrivals.height > 0:
        _out = mo.ui.table(arrivals, selection=None)
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
    _out
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
    _bars = (
        alt.Chart(congestion)
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
    mo.ui.altair_chart(_bars)
    return


if __name__ == "__main__":
    app.run()
