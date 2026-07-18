.PHONY: all install pipeline docs docs-v2 dashboard site clean lint ui

DUCKDB_PATH ?= data/airports.duckdb

all: install pipeline

install:
	uv sync

# Full ELT: dlt extract/load -> DuckDB -> dbt build, orchestrated by Prefect (headless)
pipeline:
	uv run dbt deps --project-dir dbt --profiles-dir dbt
	uv run python -m pipelines.flow

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

# Static marimo dashboards (WASM) -> _site/dashboard/, _site/classic/
dashboard:
	uv run marimo export html-wasm dashboard/dashboard.py -o _site/dashboard --mode run --no-show-code
	rm -f _site/dashboard/CLAUDE.md
	uv run marimo export html-wasm dashboard/classic.py -o _site/classic --mode run --no-show-code
	rm -f _site/classic/CLAUDE.md

# Full static site: landing page (rendered README) at root, Q&A dashboard at
# /dashboard/, classic dashboard at /classic/, dbt docs at /dbt-docs/
site: dashboard docs
	uv run python scripts/build_landing.py

clean:
	rm -rf _site dbt/target data/*.duckdb data/*.duckdb.wal
