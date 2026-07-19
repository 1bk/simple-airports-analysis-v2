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

    WIDTH = 700  # one shared plot width so charts and captions align
    return WIDTH, alt, mo, pl


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
    _title = mo.md("# Airports Analysis · Classic")
    _stamp = mo.md(
        f"<span style='font-size:0.75rem;color:var(--gray-9);white-space:nowrap'>"
        f"generated {meta['generated_at_utc']} UTC</span>"
    )
    _sub = mo.md(
        "*A compact, grid-style view of the dataset — see the "
        "[Q&A walkthrough](../dashboard/) for the narrative version, or "
        "[chat with the data](../chat/).*"
    )
    mo.vstack(
        [mo.hstack([_title, _stamp], justify="space-between", align="center"), _sub],
        gap=0,
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
            mo.stat(value=f"{_total_arrivals:,}", label="Arrivals (7d)", bordered=True),
            mo.stat(value=_busiest, label="Busiest now", bordered=True),
        ],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(mo):
    mo.md("### Airports")
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
    _table = mo.ui.table(
        airports.select("name", "iata_code", "municipality", "airport_type"),
        selection=None,
        page_size=10,
        show_column_summaries=False,
    )
    # full-width map and table in tabs: no cramped side-by-side, no dead space
    mo.ui.tabs(
        {
            "Map": mo.iframe(_map.get_root().render(), height="420px"),
            "Table": _table,
        }
    )
    return


@app.cell
def _(mo):
    mo.md("### Congestion")
    return


@app.cell
def _(WIDTH, alt, congestion, mo):
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
                x=alt.X(
                    "aircraft_within_50km:Q",
                    title="Aircraft within 50 km",
                    # integer ticks; +1 headroom so the longest bar
                    # doesn't run flush into the plot edge
                    axis=alt.Axis(format="d", tickMinStep=1),
                    scale=alt.Scale(domain=[0, _busy["aircraft_within_50km"].max() + 1]),
                ),
                y=alt.Y("name:N", sort="-x", title=None),
                color=alt.Color(
                    "aircraft_within_50km:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                tooltip=["name:N", "iata_code:N", "aircraft_within_50km:Q"],
            )
            .properties(width=WIDTH, height=26 * _busy.height, title="Busiest airports right now")
        )
        _out = mo.ui.altair_chart(_bars)
    else:
        _out = mo.callout(mo.md("No aircraft near any airport in this snapshot."), kind="info")
    _caption = mo.md(
        "*Live aircraft within 50 km of each scheduled-service airport — a keyless "
        "proxy for current congestion.*"
    )
    mo.vstack([_out, _caption])
    return


@app.cell
def _(WIDTH, alt, congestion_history, mo, pl):
    if congestion_history.height:
        # keep the trend legible: top 6 airports by peak traffic
        _top6 = (
            congestion_history.group_by("iata_code")
            .agg(pl.col("aircraft_within_50km").max().alias("peak"))
            .sort("peak", descending=True)
            .head(6)["iata_code"]
        )
        _trend = (
            alt.Chart(congestion_history.filter(pl.col("iata_code").is_in(_top6)))
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X(
                    "snapshot_at:T",
                    title=None,
                    # no fixed format: vega adapts from seconds to days as the
                    # committed history grows
                    axis=alt.Axis(labelAngle=-30, tickCount=5),
                ),
                y=alt.Y(
                    "aircraft_within_50km:Q",
                    title="Aircraft within 50 km",
                    axis=alt.Axis(format="d", tickMinStep=1),
                ),
                color=alt.Color(
                    "iata_code:N", title="Airport", scale=alt.Scale(scheme="tableau10")
                ),
                tooltip=["snapshot_at:T", "iata_code:N", "aircraft_within_50km:Q"],
            )
            .properties(
                width=WIDTH,
                height=220,
                title="Congestion over time (top 6 airports, snapshot history)",
            )
        )
        _caption = mo.md(
            "*A scheduled workflow snapshots live traffic into committed Parquet, "
            "so this series grows with every run.*"
        )
        _out = mo.vstack([mo.ui.altair_chart(_trend), _caption])
    else:
        _out = mo.md("")  # no history committed yet: skip the section quietly
    _out
    return


@app.cell
def _(mo):
    mo.md("### Arrivals, last 7 days")
    return


@app.cell
def _(WIDTH, alt, arrivals, arrivals_daily, meta, mo, pl):
    if meta["arrivals_available"] and arrivals.height > 0:
        # drop partial edge days (the window rarely starts/ends at midnight)
        _dates = sorted(arrivals_daily["arrival_date"].unique().to_list())
        _daily = (
            arrivals_daily.filter(~pl.col("arrival_date").is_in([_dates[0], _dates[-1]]))
            if len(_dates) >= 4
            else arrivals_daily
        )
        _trend = (
            alt.Chart(_daily)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X(
                    "arrival_date:T",
                    title=None,
                    axis=alt.Axis(format="%a %d %b", tickCount="day"),
                ),
                y=alt.Y("arrivals:Q", title="Arrivals"),
                color=alt.Color(
                    "iata_code:N", title="Airport", scale=alt.Scale(scheme="tableau10")
                ),
                tooltip=["arrival_date:T", "iata_code:N", "arrivals:Q"],
            )
            .properties(width=WIDTH, height=220, title="Daily arrivals (full days only)")
        )
        _bars = (
            alt.Chart(arrivals)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X(
                    "arrivals_7d:Q",
                    title="Arrivals (7 days)",
                    scale=alt.Scale(domainMin=0, nice=True),
                ),
                y=alt.Y("airport_name:N", sort="-x", title=None),
                color=alt.Color("arrivals_7d:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=["airport_name:N", "iata_code:N", "arrivals_7d:Q", "arrivals_per_day:Q"],
            )
            .properties(width=WIDTH, height=30 * arrivals.height + 20, title="Total per airport")
        )
        _labels = (
            alt.Chart(arrivals)
            .mark_text(align="left", dx=4, color="var(--gray-11)")
            .encode(
                x=alt.X("arrivals_7d:Q"),
                y=alt.Y("airport_name:N", sort="-x"),
                text=alt.Text("arrivals_7d:Q", format=","),
            )
        )
        _detail = mo.ui.table(
            arrivals.with_columns(
                pl.col("earliest_arrival").str.slice(0, 16),
                pl.col("latest_arrival").str.slice(0, 16),
            ),
            selection=None,
            page_size=10,
            show_column_summaries=False,
        )
        _out = mo.ui.tabs(
            {
                "Daily trend": mo.ui.altair_chart(_trend),
                "Totals": mo.ui.altair_chart(_bars + _labels),
                "Detail": _detail,
            }
        )
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
    mo.md("### Distances")
    return


@app.cell
def _(WIDTH, alt, distances, mo, pl):
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
            x=alt.X("to_iata:N", title=None, sort=_order),
            y=alt.Y("from_iata:N", title=None, sort=_order),
            color=alt.Color("distance_km:Q", title="km", scale=alt.Scale(scheme="viridis")),
            tooltip=["from_name:N", "to_name:N", "distance_km:Q"],
        )
        .properties(width=WIDTH, height=WIDTH - 60, title="Distance matrix (km)")
    )
    _matrix = (
        _symmetric.pivot(on="to_iata", index="from_iata", values="distance_km")
        .sort("from_iata")
        .fill_null(0.0)
    )
    _out = mo.ui.tabs(
        {
            "Heatmap": mo.ui.altair_chart(_heatmap),
            "Table": mo.ui.table(
                _matrix, selection=None, page_size=12, show_column_summaries=False
            ),
        }
    )
    _caption = mo.md(
        "*Great-circle distance in km between every pair of scheduled-service "
        "airports, by IATA code — brighter (yellow) is farther apart.*"
    )
    mo.vstack([_out, _caption])
    return


if __name__ == "__main__":
    app.run()
