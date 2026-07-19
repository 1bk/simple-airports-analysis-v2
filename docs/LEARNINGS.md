# Learnings

Hard-won, non-obvious gotchas collected while building this project. Each entry
is a thing that cost real debugging time — recorded so it only costs it once.

## marimo

- **Module-level constants are invisible to cells.** A variable defined at the
  top of the notebook file (outside any `@app.cell`) is not in scope inside
  cells — cells only see names *returned by other cells*. Symptom: the cell
  renders empty with no visible error. Define constants inside a cell and
  return them.
- **A cell displays only its last expression.** To show several elements from
  one cell, combine them with `mo.vstack([...])` / `mo.hstack([...])` — an
  `mo.md()` on its own line mid-cell is silently discarded.
- **`mo.ui.altair_chart` breaks on geo-projected charts in WASM** (react-vega
  "reading 'on'" error). Render the chart object directly instead — or use
  folium for maps (see below).
- **folium works in WASM** via `mo.iframe(map.get_root().render(), ...)` —
  real OpenStreetMap tiles, pan/zoom, and popups, all pure Python.
- **`marimo export html-wasm` ships a `CLAUDE.md`** into the output directory.
  The Makefile removes it after every export.
- **`mo.ui.table(show_column_summaries=False)`** hides the per-column
  dtype/unique/histogram header noise — usually what a dashboard wants.

## Pyodide / the chat page

- **The `anthropic` (and `openai`) Python SDKs don't work under Pyodide** —
  they sit on `httpx`, which needs raw sockets the browser doesn't provide.
  Call the API with `pyodide.http.pyfetch` (a thin wrapper over browser
  `fetch`) instead.
- **Direct browser → Anthropic calls need the CORS opt-in header**
  `anthropic-dangerous-direct-browser-access: true` alongside `x-api-key`.
  The "danger" is shipping a key in frontend code; a bring-your-own-key page
  where the user pastes their key at runtime is the intended use.

## dlt

- **dlt drops all-null columns** on load. If a fallback source omits fields,
  downstream models break — guard with
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` after the load.
- **Failed load packages leak across runs.** A half-loaded package from a
  failed run is retried into the *next* run and can poison it. Call
  `pipeline.drop_pending_packages()` before every run.
- **Never pre-create a table dlt owns.** dlt will try to reconcile the schema
  with `ALTER ... ADD CONSTRAINT`, which DuckDB doesn't support. Let dlt create
  its tables; handle possibly-absent tables in dbt with `adapter.get_relation`
  compiling to an empty typed relation.

## dbt / MetricFlow

- **`dbt-metricflow` pins `dbt-core < 1.12`** (as of July 2026), so it can't
  share an environment with this project. The `mf` CLI runs sandboxed via
  `uvx --from 'dbt-metricflow[dbt-duckdb]'`, and the semantic-layer YAML uses
  the legacy spec that both dbt versions understand.
- **`mf` resolves relative paths from its working directory** — running it
  from `dbt/` means the profile's relative DuckDB path points at the wrong
  place. Same for dbt-mcp, which invokes dbt with the project dir as cwd.
  Export an absolute `DUCKDB_PATH` in both launchers.
- **sqlfluff's jinja templater can't resolve everything dbt can**: package
  macros (`dbt.date_spine`), `adapter.*`, and `target.*` all fail; those
  files are listed in `.sqlfluffignore`.
- **dbt Docs v2 (Fusion) is not static-hostable** — it needs a running server
  over parquet artifacts, so the hosted site keeps classic static docs and
  `make docs-v2` demos v2 locally.

## APIs & data sources

- **OpenSky blocks/throttles GitHub Actions runner IPs** (proven by a
  controlled comparison: identical code + credentials work locally while
  runners get TCP connect timeouts). The committed Parquet history under
  `history/` exists so deploys never depend on OpenSky being reachable
  from CI.
- **OpenSky's arrivals endpoint rejects queries spanning more than two UTC
  day-partitions** ("Your query will naturally spill into the 3rd day"), so
  the 7-day window is fetched in one-day chunks, skipping failed chunks.
- **adsb.lol reports `alt_baro` in feet and `gs` in knots**, while the
  OpenSky-shaped columns expect metres and m/s — convert (× 0.3048,
  × 0.514444) or every altitude is silently wrong.

## GitHub Actions

- **Pushes made with `GITHUB_TOKEN` do not trigger `on: push` workflows.**
  The snapshot workflow explicitly runs `gh workflow run pages.yml` after
  committing new data — `workflow_dispatch` via the API is the documented
  exception to the no-recursive-triggers rule.
- **`astral-sh/setup-uv` has no floating major tag** — `@v8` fails with a
  5-second "action not found" error. Pin the exact version.
- **Scheduled workflows are disabled after 60 days without repo activity**
  (GitHub emails a re-enable link). This repo's own snapshot commits count
  as activity.

## DuckDB

- **Don't open the file `read_only` while dbt runs in-process** — dbt's
  connection holds the file with a different configuration and the two
  conflict.
