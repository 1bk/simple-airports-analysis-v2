{% docs __overview__ %}

# Simple Airports Analysis v2 — Malaysia

This dbt project transforms raw data loaded by **dlt** into a **DuckDB** warehouse to
answer four questions about Malaysian aviation:

1. **How many airports are there in Malaysia?** → `dim_airports_my`
2. **What is the distance between the airports?** → `fct_airport_distances`
3. **How many flights are landing at Malaysian airports?** → `fct_arrivals` *(requires OpenSky credentials; empty otherwise)*
4. **Which airport is the most congested?** → `fct_congestion` *(keyless live-traffic proxy)*

## Layers

- **`raw`** — tables loaded by dlt (OurAirports catalogue, live aircraft snapshot, optional arrivals)
- **`staging`** — one view per raw table: typed, renamed, filtered
- **`marts`** — the analysis tables above

Use the lineage graph (bottom-right icon) to see how everything connects.

## Links

- [Interactive dashboard](https://1bk.dev/simple-airports-analysis-v2/) (marimo, WASM)
- [Source on GitHub](https://github.com/1bk/simple-airports-analysis-v2)
- Original 2020 project: [simple-airports-analysis](https://github.com/1bk/simple-airports-analysis)

{% enddocs %}
