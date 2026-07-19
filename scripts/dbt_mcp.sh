#!/usr/bin/env sh
# Launch the dbt MCP server for this project (used by .mcp.json, so any AI
# client opened in this repo can inspect and run the dbt project).
# Works fully offline/local: dbt CLI tools only, no dbt Cloud account needed.
cd "$(dirname "$0")/.." || exit 1

export DBT_PROJECT_DIR="$PWD/dbt"
export DBT_PROFILES_DIR="$PWD/dbt"
export DBT_PATH="$PWD/.venv/bin/dbt" # provided by `make install` (uv sync)
# absolute path: dbt-mcp invokes dbt from inside dbt/, where the profile's
# relative default would resolve to the wrong place
export DUCKDB_PATH="$PWD/data/airports.duckdb"

# dbt Cloud-backed tool groups are off: this is a dbt-core-only setup
export DISABLE_SEMANTIC_LAYER=true
export DISABLE_DISCOVERY=true
export DISABLE_ADMIN_API=true

# no telemetry, ever (matches the Makefile)
export DO_NOT_TRACK=1
export DBT_SEND_ANONYMOUS_USAGE_STATS=false

exec uvx --python 3.12 dbt-mcp
