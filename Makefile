.PHONY: all install pipeline snapshot docs docs-v2 dashboard site clean lint ui metrics mf

DUCKDB_PATH ?= data/airports.duckdb

# No telemetry, ever: DO_NOT_TRACK is the cross-tool standard; the explicit
# flags cover dbt/Fusion and the Prefect server, which don't all honor it.
export DO_NOT_TRACK = 1
export DBT_SEND_ANONYMOUS_USAGE_STATS = false
export PREFECT_SERVER_ANALYTICS_ENABLED = false
export MF_DISABLE_TELEMETRY = 1

all: install pipeline

install:
	uv sync

# Full ELT: dlt extract/load -> DuckDB -> dbt build, orchestrated by Prefect (headless)
pipeline:
	uv run dbt deps --project-dir dbt --profiles-dir dbt
	uv run python -m pipelines.flow

# MetricFlow semantic layer. The mf CLI runs in its own sandboxed env (uvx)
# because dbt-metricflow currently pins dbt-core < 1.12 while this project is
# on 1.12; the legacy semantic-layer spec is readable by both. Run
# `make metrics` for a validated demo query, or ad-hoc queries with
#   make mf ARGS='query --metrics total_arrivals --group-by airport__name'
# mf runs from dbt/, so point the profile at the repo-root DuckDB file
MF := DUCKDB_PATH=../data/airports.duckdb uvx --python 3.12 --from 'dbt-metricflow[dbt-duckdb]' mf
metrics:
	cd dbt && $(MF) validate-configs
	cd dbt && $(MF) query --metrics total_arrivals,arriving_aircraft --group-by airport__name --order -total_arrivals

mf:
	cd dbt && $(MF) $(ARGS)

# Merge a live aircraft-state + arrivals snapshot into committed history/*.parquet
# (run on a schedule by .github/workflows/snapshot.yml)
snapshot:
	uv run python -m pipelines.snapshot

lint:
	uv run pre-commit run --all-files

# Optional: Prefect UI to watch flow runs (pair with PREFECT_API_URL=http://127.0.0.1:4200/api make pipeline)
ui:
	uv run prefect server start

# Static dbt docs -> _site/dbt-docs/
docs:
	uv run dbt docs generate --project-dir dbt --profiles-dir dbt --static
	mkdir -p _site/dbt-docs
	cp dbt/target/static_index.html _site/dbt-docs/index.html

# Local-only demo of dbt Docs v2 (alpha, dbt Fusion engine). Docs v2 needs a
# running server (parquet artifacts + local HTTP server), so it isn't
# static-hostable yet -- the hosted site keeps the classic static dbt docs
# above. Requires the sandboxed Fusion CLI; install with:
#   curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh | sh -s -- --to .fusion
FUSION_BIN ?= .fusion/dbt
docs-v2:
	@test -x "$(FUSION_BIN)" || { \
		echo "Fusion CLI not found at $(FUSION_BIN). Install it (sandboxed, won't shadow your dbt) with:"; \
		echo "  curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh | sh -s -- --to .fusion"; \
		exit 1; \
	}
	$(FUSION_BIN) compile --write-index --project-dir dbt --profiles-dir dbt
	$(FUSION_BIN) docs serve --target-path dbt/target

# Static marimo dashboards (WASM) -> _site/dashboard/, _site/classic/, _site/chat/
dashboard:
	uv run marimo export html-wasm dashboard/dashboard.py -o _site/dashboard --mode run --no-show-code
	rm -f _site/dashboard/CLAUDE.md
	uv run marimo export html-wasm dashboard/classic.py -o _site/classic --mode run --no-show-code
	rm -f _site/classic/CLAUDE.md
	uv run marimo export html-wasm dashboard/chat.py -o _site/chat --mode run --no-show-code
	rm -f _site/chat/CLAUDE.md

# Full static site: landing page (rendered README) at root, Q&A dashboard at
# /dashboard/, classic dashboard at /classic/, BYO-key chat at /chat/, dbt docs at /dbt-docs/
site: dashboard docs
	uv run python scripts/build_landing.py

clean:
	rm -rf _site dbt/target data/*.duckdb data/*.duckdb.wal
