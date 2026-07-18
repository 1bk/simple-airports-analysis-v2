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
    arrivals = pl.read_csv(str(_base / "arrivals.csv"))
    meta = pl.read_csv(str(_base / "meta.csv")).row(0, named=True)
    return airports, arrivals, congestion, distances, meta


@app.cell
def _(meta, mo):
    mo.hstack(
        [
            mo.md(
                """
        # Airports Analysis (Classic)

        A dense, grid-style rebuild of the original v1 Metabase dashboard —
        see the [Q&A-style walkthrough](../dashboard/) for the narrative version.
        """
            ),
            mo.md(f"Data generated at **{meta['generated_at_utc']} UTC**").right(),
        ],
        justify="space-between",
        align="start",
    )
    return


@app.cell
def _(airports, arrivals, congestion, meta, mo):
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _total_arrivals = arrivals["arrivals_24h"].sum() if meta["arrivals_available"] else 0
    _top = congestion.row(0, named=True) if congestion.height else None
    _busiest = (
        f"{_top['name']} ({_top['aircraft_within_50km']} aircraft)"
        if _top and _top["aircraft_within_50km"] > 0
        else "quiet right now"
    )
    mo.hstack(
        [
            mo.stat(value=airports.height, label="Airports in Malaysia", bordered=True),
            mo.stat(value=_scheduled, label="Scheduled airports", bordered=True),
            mo.stat(value=_total_arrivals, label="Arrivals (24h)", bordered=True),
            mo.stat(value=_busiest, label="Busiest airport now", bordered=True),
        ],
        widths="equal",
        gap=1,
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
    _airports_table = mo.ui.table(
        airports.select(
            "name", "iata_code", "municipality", "airport_type", "latitude", "longitude"
        ),
        selection=None,
        page_size=8,
        label="Airports",
    )
    mo.hstack(
        [
            mo.iframe(_map.get_root().render(), width="420px", height="450px"),
            _airports_table,
        ],
        widths=[1, 1],
        gap=1,
        align="start",
    )
    return


@app.cell
def _(airports, alt, congestion, mo):
    _busy = airports.join(
        congestion.select("ident", "aircraft_within_50km"), on="ident", how="inner"
    )
    _scatter = (
        alt.Chart(_busy)
        .mark_circle(opacity=0.75)
        .encode(
            x=alt.X("longitude:Q", title="Longitude"),
            y=alt.Y("aircraft_within_50km:Q", title="Aircraft within 50km"),
            size=alt.Size("aircraft_within_50km:Q", legend=None),
            color=alt.Color("airport_type:N", title="Type"),
            tooltip=["name:N", "iata_code:N", "aircraft_within_50km:Q"],
        )
        .properties(width=650, height=260, title="Airport Busyness")
    )
    mo.ui.altair_chart(_scatter)
    return


@app.cell
def _(meta, mo):
    mo.md(
        f"""
    <div style="text-align:center; font-size:2rem; font-weight:600; padding: 0.5rem 0;">
    Arrivals snapshot as of {meta["generated_at_utc"]} UTC
    </div>
    """
    )
    return


@app.cell
def _(alt, arrivals, meta, mo):
    if meta["arrivals_available"] and arrivals.height > 0:
        _bars = (
            alt.Chart(arrivals)
            .mark_bar()
            .encode(
                x=alt.X("arrivals_24h:Q", title="Arrivals (24h)"),
                y=alt.Y("airport_name:N", sort="-x", title=None),
                tooltip=["airport_name:N", "iata_code:N", "arrivals_24h:Q"],
            )
            .properties(width=650, height=260, title="Arrivals in the last 24h, per airport")
        )
        _table = mo.ui.table(arrivals, selection=None, page_size=10, label="Arrivals detail")
        _out = mo.vstack([mo.ui.altair_chart(_bars), _table])
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
    mo.md("### Distance Between Malaysian Airports (in KM)")
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
    mo.ui.table(_matrix, selection=None, page_size=15, label="Distance matrix (km)")
    return


if __name__ == "__main__":
    app.run()
