# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org):
MAJOR for breaking changes to the pipeline contract or data models, MINOR for
new models, sources, or dashboard features, PATCH for fixes.

## [Unreleased]

### Added

- **Arrival-origins analysis** (question 5): new `fct_arrival_origins` mart
  joining arrivals to the worldwide OurAirports catalogue — where flights into
  Malaysia come from, split domestic vs international. Both dashboards gained
  a "Where flights come from" section (top origins, by country, live
  domestic/international stats), and the semantic layer grew to four semantic
  models and eleven metrics (including an `international_share` ratio).
- **Chart replies in the data chat**: asking for a chart makes the model answer
  with a small validated JSON spec, rendered natively as a bar, line, or pie
  chart (with new suggested prompts to try it); invalid specs fall back to
  prose. A full generative-UI answers page stays on the roadmap as exploratory.
- **dbt governance showcase**: enforced contracts (typed columns + not_null
  constraints in the DDL) on every mart, exposures for the four site surfaces,
  two unit tests with mocked inputs, two custom generic tests (`is_icao_code`,
  `is_recent_epoch`), and documented macros.
- **Multi-provider data chat**: the `/chat/` page now supports Anthropic,
  OpenAI, Gemini, and GLM. Model lists are discovered live from each
  provider's models endpoint with the user's own key (static fallback lists
  otherwise), so new models appear without a redeploy. All four providers
  support direct browser CORS calls — keys still never leave the browser
  except to the provider.

### Changed

- The dbt MCP demo screenshot now shows a headless `claude -p` session
  answering the new question 5 via the MCP tools (an animated-gif version was
  tried and reverted — the run is minutes of silent waiting, which a static
  shot of the finished answer shows better). Prefect UI screenshots refreshed.

- **Snapshot history is now partitioned monthly**: snapshots merge into
  append-only `history/{dataset}/{YYYY-MM}.parquet` files instead of rewriting
  one ever-growing Parquet per dataset, so git-history growth stays linear
  (~5 MB/year) instead of quadratic. The pipeline reads the whole directory
  with read-time deduplication (a flight fetched near a month boundary can
  land in two files); existing history was migrated losslessly and all
  dashboards/marts verified equal-or-better (dbt build 36/36).

- README: "Who consumes what" section explaining how each surface gets its
  data (baked mart extracts for the static site vs. on-demand semantic-layer /
  MCP queries against the warehouse); lineage screenshot now shows the
  semantic-layer nodes; chat screenshot shows a real conversation.
- Generic test arguments migrated to the nested `arguments:` YAML form
  (the top-level form is deprecated in dbt-core and errors in Fusion,
  silently dropping semantic nodes from the Docs v2 index).
- `docs/LEARNINGS.md` records the non-obvious gotchas hit while building.
- Dashboard showcase screenshots are full-page captures again (the previous
  refresh cropped both to the first viewport, making the two pages hard to
  tell apart).
- README documents the data-growth outlook: committed history and dashboard
  payloads grow ~5 MB/year, and a "bounded history growth" roadmap item covers
  the git-history cost of rewriting Parquet snapshots.

### Fixed

- Landing-page mermaid diagram could stay raw text on cold-cache visits:
  `startOnLoad` races the window `load` event when mermaid loads as a deferred
  CDN module. The landing page now calls `mermaid.run()` explicitly (and picks
  the dark theme under a dark color scheme).

## [2.6.0] - 2026-07-19

### Added

- **MetricFlow semantic layer**: three semantic models (arrivals, airports,
  congestion history) joined through a shared `airport` entity, six metrics
  (including a rolling 7-day cumulative and a day-over-day derived metric), a
  daily time spine, and `make metrics` / `make mf ARGS=...` targets. The
  MetricFlow CLI runs sandboxed via `uvx` (it pins `dbt-core < 1.12`); MetricFlow's
  BSL 1.1 license is flagged in the README.
- **dbt MCP server**: committed `.mcp.json` + `scripts/dbt_mcp.sh` launcher, so
  any MCP client opened in the repo can explore lineage, compile models, and
  query DuckDB — fully local, no dbt Cloud, Cloud-only tool groups disabled,
  telemetry off. README documents a headless `claude -p` example.
- **Data chat page** at `/chat/`: bring-your-own-API-key Claude chat over the
  dashboard's datasets, running entirely in the browser (WASM). The key goes
  straight from the browser to `api.anthropic.com` via Anthropic's CORS
  support — no backend, no proxy, nothing stored.

### Changed

- Classic dashboard redesigned for legibility: single-row header, full-width
  map/table and arrivals/distances sections in tabs, integer axis ticks with
  bar headroom, top-6 congestion-over-time trend with an adaptive time axis,
  partial edge days dropped from the daily-arrivals trend, table column
  summaries hidden, and a distance heatmap alongside the matrix table.
- Q&A dashboard links to the new chat page; README showcase screenshots
  refreshed for both dashboards.

## [2.5.0] - 2026-07-19

### Added

- **Snapshot history**: `pipelines/snapshot.py` merges live aircraft states and
  7-day arrivals into deduplicated Parquet under `history/`, committed to the
  repo (`make snapshot` locally).
- Scheduled `snapshot.yml` workflow (every 6 hours) that collects a snapshot,
  commits only when new data arrived, and dispatches a Pages redeploy.
- `fct_congestion_history` mart: the 50 km congestion proxy per committed
  snapshot — question 4 as a growing time series.
- Congestion-over-time chart on both the Q&A and classic dashboards.
- `stg_aircraft_states_history` staging model over the committed history.

### Changed

- `stg_arrivals` now unions the live credentialed fetch with committed snapshot
  history, deduplicated per flight — deploys no longer depend on OpenSky being
  reachable from CI runners (last-known-good by construction).
- Arrivals are fetched in one-day chunks: OpenSky now rejects queries spanning
  more than two day-partitions; a failed chunk is skipped instead of aborting
  the whole fetch.
- `fct_arrivals` applies an explicit trailing-7-day filter now that staging can
  span the full history (`fct_arrivals_daily` keeps the complete series).
- All telemetry disabled repo-wide: dbt anonymous usage stats, dlt telemetry,
  Prefect server analytics, plus `DO_NOT_TRACK=1` exported from the Makefile.

## [2.4.0] - 2026-07-19

### Added

- 7-day arrivals window (the OpenSky API maximum per request) and a new
  `fct_arrivals_daily` mart with daily-trend charts on both dashboards.

### Changed

- Classic dashboard redesigned as a compact grid: stat cards, top-10 congestion
  bar, arrivals trend/totals/detail, and a distance pivot matrix.
- GitHub Actions bumped to Node-24 majors (`checkout@v7`,
  `upload-pages-artifact@v5`, `deploy-pages@v5`); `setup-uv` pinned to `v8.3.2`
  (no floating `v8` tag exists).

### Fixed

- Distance-matrix caption described the viridis colour scale backwards.

## [2.3.0] - 2026-07-18

### Added

- Landing page at the site root: the README rendered to HTML (with mermaid
  diagrams), mirroring the v1 site structure; dashboards moved to `/dashboard/`
  and `/classic/`.
- Interactive folium/Leaflet maps with OpenStreetMap tiles, pan/zoom, and
  per-airport popups (replacing the static projected scatter).
- dbt Docs v2 preview screenshots in the README showcase.

### Changed

- Arrivals fetch is best-effort: a failed or credential-less run keeps the last
  successful load's rows instead of failing the deploy; dlt fully owns
  `raw.arrivals` and `stg_arrivals` compiles to an empty typed relation until
  the table exists.

## [2.2.0] - 2026-07-18

### Added

- Arrivals support end to end: OpenSky OAuth fetch, `fct_arrivals` mart, and
  dashboard sections (repo secrets in CI, `.env` locally).
- Classic dashboard page recreating the v1 Metabase layout.
- Richer Q&A dashboard: stat cards, symmetric distance-matrix heatmap,
  per-airport distance lookup, and full data tables.

## [2.1.0] - 2026-07-18

### Added

- `make docs-v2`: local demo of dbt Docs v2 on the dbt Fusion engine
  (sandboxed install; the hosted site keeps classic static docs).
- Project-specific `dbt/README.md` replacing the dbt starter boilerplate.
- README badges (CI, Pages, release, Python, code size, repo size) and links to
  the live dashboards and hosted dbt docs.

## [2.0.0] - 2026-07-18

First release of the v2 rewrite — the original 2020 interview project
([simple-airports-analysis](https://github.com/1bk/simple-airports-analysis))
rebuilt on a fully open-source, zero-Docker data stack.

### Added

- ELT pipeline: dlt → DuckDB → dbt-core 1.12 → marimo WASM dashboards,
  orchestrated headless by Prefect 3 and managed with uv.
- The original four analysis questions answered as dbt marts with tests:
  airport count, pairwise distances, arrivals, and congestion.
- Keyless-by-default sources: OurAirports catalogue and live aircraft states
  (OpenSky anonymous → adsb.lol → committed sample fallback chain).
- CI (pre-commit: gitleaks, ruff, sqlfluff), GitHub Pages deploy, static dbt
  docs, and tag-driven releases.

[Unreleased]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.6.0...HEAD
[2.6.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/1bk/simple-airports-analysis-v2/releases/tag/v2.0.0
