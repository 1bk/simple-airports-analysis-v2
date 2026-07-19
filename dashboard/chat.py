# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
# ]
# ///

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", app_title="Chat with the Airports Data")


@app.cell
def _():
    import json

    import marimo as mo
    import polars as pl

    return json, mo, pl


@app.cell
def _(mo, pl):
    _base = mo.notebook_location() / "public"
    airports = pl.read_csv(str(_base / "airports_my.csv"))
    distances = pl.read_csv(str(_base / "distances.csv"))
    congestion = pl.read_csv(str(_base / "congestion.csv"))
    arrivals = pl.read_csv(str(_base / "arrivals.csv"))
    arrivals_daily = pl.read_csv(str(_base / "arrivals_daily.csv"))
    meta = pl.read_csv(str(_base / "meta.csv")).row(0, named=True)
    return airports, arrivals, arrivals_daily, congestion, distances, meta


@app.cell
def _(airports, arrivals, arrivals_daily, congestion, distances, meta):
    # Bake the small marts into the system prompt so the model answers from
    # real data. The whole context is a few KB - well within any model's budget.
    _dist = distances["distance_km"]
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _by_type = airports.group_by("airport_type").len().sort("len", descending=True).rows()
    _pair_cols = ["airport_a_name", "airport_b_name", "distance_km"]
    _closest = distances.sort("distance_km").head(5).select(_pair_cols).rows()
    _farthest = distances.sort("distance_km", descending=True).head(5).select(_pair_cols).rows()
    DATA_CONTEXT = f"""
You are the data assistant for the Malaysian Airports Analysis dashboard
(https://github.com/1bk/simple-airports-analysis-v2). Answer questions using
ONLY the datasets below (they are the dashboard's own data). Be concise; use
plain numbers and airport names. If asked something outside this data, say the
dashboard doesn't cover it.

Data generated at {meta["generated_at_utc"]} UTC. Live-traffic source: {meta["aircraft_source"]}.

## Airports (summary)
Total Malaysian airports: {airports.height}. With scheduled service: {_scheduled}.
Breakdown by type: {_by_type}

## Congestion right now (aircraft within 50 km per airport, latest snapshot)
{congestion.write_csv()}

## Arrivals, past 7 days (per airport)
{arrivals.write_csv()}

## Daily arrivals
{arrivals_daily.write_csv()}

## Pairwise distances between scheduled-service airports (km)
{distances.height} pairs. Min {_dist.min()} km, max {_dist.max()} km, mean {round(_dist.mean(), 1)}.
Closest pairs: {_closest}
Farthest pairs: {_farthest}
"""
    return (DATA_CONTEXT,)


@app.cell
def _(mo):
    mo.md(
        """
    # Chat with the Airports Data

    Ask questions about Malaysian airports, arrivals, and congestion — answered by
    Claude using this dashboard's actual data.

    **Bring your own API key.** This page is a static site with no backend: the
    notebook runs entirely in your browser (WebAssembly), and your key is sent
    directly from your browser to `api.anthropic.com` — nowhere else. It is never
    stored or logged. Get a key at
    [console.anthropic.com](https://console.anthropic.com/settings/keys).

    [Q&A dashboard](../dashboard/) · [classic](../classic/) · [project overview](../)
    """
    )
    return


@app.cell
def _(mo):
    api_key_input = mo.ui.text(
        kind="password", label="Anthropic API key", placeholder="sk-ant-...", full_width=True
    )
    model_picker = mo.ui.dropdown(
        options={
            "Claude Opus 4.8 (most capable)": "claude-opus-4-8",
            "Claude Sonnet 5 (balanced)": "claude-sonnet-5",
            "Claude Haiku 4.5 (fastest)": "claude-haiku-4-5",
        },
        value="Claude Opus 4.8 (most capable)",
        label="Model",
    )
    mo.hstack([api_key_input, model_picker], widths=[2, 1], gap=1, align="end")
    return api_key_input, model_picker


@app.cell
def _(DATA_CONTEXT, api_key_input, json, mo, model_picker):
    async def _post_anthropic(payload: dict, key: str) -> dict:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            # required for direct browser -> API calls (CORS); the "danger" is
            # exposing a key in shipped frontend code - here the user supplies
            # their own key at runtime, which is the intended BYO-key pattern
            "anthropic-dangerous-direct-browser-access": "true",
        }
        body = json.dumps(payload)
        try:
            from pyodide.http import pyfetch  # running in the browser (WASM)

            resp = await pyfetch(url, method="POST", headers=headers, body=body)
            return await resp.json()
        except ImportError:  # running locally (marimo edit / run)
            import urllib.request

            req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                return json.loads(exc.read())

    async def claude_model(messages, config):
        key = api_key_input.value.strip()
        if not key:
            return "Please paste your Anthropic API key above first."
        payload = {
            "model": model_picker.value,
            "max_tokens": 2048,
            "system": DATA_CONTEXT,
            "messages": [{"role": m.role, "content": str(m.content)} for m in messages],
        }
        data = await _post_anthropic(payload, key)
        if data.get("type") == "error":
            return f"**API error** ({data['error'].get('type')}): {data['error'].get('message')}"
        if data.get("stop_reason") == "refusal":
            return "The model declined to answer that request."
        texts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n\n".join(texts) or "*(empty response)*"

    chat = mo.ui.chat(
        claude_model,
        prompts=[
            "Which airport is the most congested right now?",
            "How many arrivals did KUL get in the last 7 days, per day on average?",
            "What are the two closest airports, and the two farthest apart?",
            "Summarise this dashboard's data in three bullet points.",
        ],
        show_configuration_controls=False,
    )
    chat
    return


if __name__ == "__main__":
    app.run()
