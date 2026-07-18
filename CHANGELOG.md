# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org):
MAJOR for breaking changes to the pipeline contract or data models, MINOR for
new models, sources, or dashboard features, PATCH for fixes.

## [Unreleased]

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

[Unreleased]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.5.0...HEAD
[2.5.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/1bk/simple-airports-analysis-v2/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/1bk/simple-airports-analysis-v2/releases/tag/v2.0.0
