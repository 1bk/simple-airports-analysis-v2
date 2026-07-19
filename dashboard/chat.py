# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "altair",
#     "polars",
# ]
# ///

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", app_title="Chat with the Airports Data")


@app.cell
def _():
    import json
    import re

    import altair as alt
    import marimo as mo
    import polars as pl

    return alt, json, mo, pl, re


@app.cell
def _(mo, pl):
    _base = mo.notebook_location() / "public"
    airports = pl.read_csv(str(_base / "airports_my.csv"))
    distances = pl.read_csv(str(_base / "distances.csv"))
    congestion = pl.read_csv(str(_base / "congestion.csv"))
    arrivals = pl.read_csv(str(_base / "arrivals.csv"))
    arrivals_daily = pl.read_csv(str(_base / "arrivals_daily.csv"))
    arrival_origins = pl.read_csv(str(_base / "arrival_origins.csv"))
    meta = pl.read_csv(str(_base / "meta.csv")).row(0, named=True)
    return (
        airports,
        arrival_origins,
        arrivals,
        arrivals_daily,
        congestion,
        distances,
        meta,
    )


@app.cell
def _(airports, arrival_origins, arrivals, arrivals_daily, congestion, distances, meta, pl):
    # Bake the small marts into the system prompt so the model answers from
    # real data. The whole context is a few KB - well within any model's budget.
    _dist = distances["distance_km"]
    _scheduled = airports.filter(airports["has_scheduled_service"]).height
    _by_type = airports.group_by("airport_type").len().sort("len", descending=True).rows()
    _pair_cols = ["airport_a_name", "airport_b_name", "distance_km"]
    _closest = distances.sort("distance_km").head(5).select(_pair_cols).rows()
    _farthest = distances.sort("distance_km", descending=True).head(5).select(_pair_cols).rows()
    _by_country = (
        arrival_origins.group_by("origin_country")
        .agg(pl.col("flights").sum())
        .sort("flights", descending=True)
        .rows()
    )
    _by_intl = arrival_origins.group_by("is_international").agg(pl.col("flights").sum()).rows()
    _domestic_flights = next((n for is_intl, n in _by_intl if not is_intl), 0)
    _intl_flights = next((n for is_intl, n in _by_intl if is_intl), 0)
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

## Arrival origins, past 7 days (where inbound flights came from)
Domestic arrivals (origin in Malaysia): {_domestic_flights}.
International arrivals: {_intl_flights}.
Flights by origin country (country code, total flights): {_by_country}

## Charts
If the user asks for a chart, graph, or plot, reply with ONLY a fenced json
code block (no other text) matching this spec, computed from the data above:
```json
{{"chart": "bar" | "line" | "pie", "title": "...", "x_label": "...", "y_label": "...",
  "data": [{{"label": "...", "value": 0}}, ...]}}
```
`x_label`/`y_label` are optional. Keep `data` to at most ~15 points. For
anything else, answer normally in prose.
"""
    return (DATA_CONTEXT,)


@app.cell
def _(mo):
    mo.md(
        """
    # Chat with the Airports Data

    Ask questions about Malaysian airports, arrivals, and congestion — answered by
    a model of your choice using this dashboard's actual data.

    **Bring your own API key.** This page is a static site with no backend: the
    notebook runs entirely in your browser (WebAssembly), and your key is sent
    directly from your browser to the provider you pick below — nowhere else. It
    is never stored or logged.

    [Q&A dashboard](../dashboard/) · [classic](../classic/) · [project overview](../)
    """
    )
    return


@app.cell
def _(mo):
    provider_picker = mo.ui.dropdown(
        options={
            "Anthropic (Claude)": "anthropic",
            "OpenAI (GPT)": "openai",
            "Gemini (Google)": "gemini",
            "GLM (Zhipu)": "glm",
        },
        value="Anthropic (Claude)",
        label="Provider",
    )
    provider_picker
    return (provider_picker,)


@app.cell
def _(mo, provider_picker):
    # Placeholder / help link adapt to the chosen provider. Redefining the text
    # input here (keyed off provider_picker) also clears the field on provider
    # switch, so a key never gets silently sent to the wrong API.
    _provider_meta = {
        "anthropic": ("sk-ant-...", "https://console.anthropic.com/settings/keys"),
        "openai": ("sk-...", "https://platform.openai.com/api-keys"),
        "gemini": ("AIza...", "https://aistudio.google.com/apikey"),
        "glm": ("...", "https://z.ai/manage-apikey/apikey-list"),
    }
    _placeholder, _key_url = _provider_meta[provider_picker.value]
    api_key_input = mo.ui.text(
        kind="password",
        label="API key",
        placeholder=_placeholder,
        full_width=True,
    )
    key_help = mo.md(f"Get a key at [{_key_url}]({_key_url}).")
    return api_key_input, key_help


@app.cell
async def _(api_key_input, json, mo, provider_picker, re):
    async def _get_json(url: str, headers: dict) -> dict:
        try:
            from pyodide.http import pyfetch  # running in the browser (WASM)

            resp = await pyfetch(url, method="GET", headers=headers)
            return await resp.json()
        except ImportError:  # running locally (marimo edit / run)
            import urllib.error
            import urllib.request

            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                return json.loads(exc.read())

    # Small curated fallbacks, used when there's no key yet or the live fetch
    # fails (network error, bad key, provider outage).
    _fallback_models = {
        "anthropic": {
            "Claude Opus 4.8 (most capable)": "claude-opus-4-8",
            "Claude Sonnet 5 (balanced)": "claude-sonnet-5",
            "Claude Haiku 4.5 (fastest)": "claude-haiku-4-5",
        },
        "openai": {
            "GPT-5.6 Sol (most capable)": "gpt-5.6-sol",
            "GPT-5.6 Terra (balanced)": "gpt-5.6-terra",
            "GPT-5.6 Luna (fastest)": "gpt-5.6-luna",
        },
        "gemini": {
            "Gemini 3.1 Pro (most capable)": "gemini-3.1-pro-preview",
            "Gemini 3.5 Flash (balanced)": "gemini-3.5-flash",
            "Gemini 2.5 Flash-Lite (fastest)": "gemini-2.5-flash-lite",
        },
        "glm": {
            "GLM-5.2 (most capable)": "glm-5.2",
            "GLM-5-Turbo (fastest)": "glm-5-turbo",
            "GLM-4.6 (previous flagship)": "glm-4.6",
        },
    }

    async def _fetch_anthropic_models(key: str) -> dict | None:
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
        }
        data = await _get_json("https://api.anthropic.com/v1/models", headers)
        # The API already returns newest-released-first; no re-sort needed.
        _models = {m["display_name"]: m["id"] for m in data.get("data", [])}
        return _models or None

    async def _fetch_openai_models(key: str) -> dict | None:
        headers = {"Authorization": f"Bearer {key}"}
        data = await _get_json("https://api.openai.com/v1/models", headers)
        _include = re.compile(r"^(gpt-|o[0-9])")
        _exclude = re.compile(
            r"audio|realtime|transcribe|tts|whisper|embed|image|dall-e|moderation|instruct|search"
        )
        _ids = sorted(
            (
                m["id"]
                for m in data.get("data", [])
                if _include.match(m["id"]) and not _exclude.search(m["id"])
            ),
            reverse=True,
        )
        return {_id: _id for _id in _ids} or None

    async def _fetch_gemini_models(key: str) -> dict | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        data = await _get_json(url, {})
        _ids = []
        for m in data.get("models", []):
            _name = m.get("name", "")
            _methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in _methods and "gemini" in _name and "embedding" not in _name:
                _ids.append(_name.removeprefix("models/"))
        return {_id: _id for _id in _ids} or None

    async def _fetch_live_models(provider: str, key: str) -> dict | None:
        try:
            if provider == "anthropic":
                return await _fetch_anthropic_models(key)
            if provider == "openai":
                return await _fetch_openai_models(key)
            if provider == "gemini":
                return await _fetch_gemini_models(key)
        except Exception:
            return None  # any fetch/parse failure -> fall back to the static list
        return None  # glm has no reliable public models-list endpoint

    _provider = provider_picker.value
    _key = api_key_input.value.strip()
    _live_models = await _fetch_live_models(_provider, _key) if _key else None
    model_options = _live_models or _fallback_models[_provider]
    model_source = "your account's live model list" if _live_models else "a static fallback list"
    model_picker = mo.ui.dropdown(
        options=model_options, value=next(iter(model_options)), label="Model"
    )
    mo.hstack(
        [api_key_input, model_picker],
        widths=[2, 1],
        gap=1,
        align="end",
    )
    return model_picker, model_source


@app.cell
def _(key_help, mo, model_source):
    mo.vstack([key_help, mo.md(f"*Showing {model_source}.*")])
    return


@app.cell
def _(alt, json, pl, re):
    _ALLOWED_CHARTS = ("bar", "line", "pie")

    def parse_chart_reply(reply_text: str):
        """If reply_text is a valid chart spec (see DATA_CONTEXT's mini-spec),
        return (title, altair_chart). Otherwise return None so the caller can
        fall back to the raw text. Never raises - any malformed input just
        yields None.
        """
        _fence = re.search(r"```json\s*(.*?)\s*```", reply_text, re.DOTALL)
        _candidate = _fence.group(1) if _fence else reply_text.strip()
        if not _candidate.startswith("{"):
            return None
        try:
            _spec = json.loads(_candidate)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(_spec, dict):
            return None
        _chart_type = _spec.get("chart")
        _data = _spec.get("data")
        if _chart_type not in _ALLOWED_CHARTS or not isinstance(_data, list) or not _data:
            return None
        _valid_points = all(
            isinstance(_d, dict)
            and isinstance(_d.get("label"), str)
            and isinstance(_d.get("value"), (int, float))
            and not isinstance(_d.get("value"), bool)
            for _d in _data
        )
        if not _valid_points:
            return None
        _title = str(_spec.get("title", ""))
        _x_label = _spec.get("x_label")
        _y_label = _spec.get("y_label")
        _df = pl.DataFrame(_data[:15])
        if _chart_type == "bar":
            _chart = (
                alt.Chart(_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "value:Q",
                        title=_x_label or "Value",
                        axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                    y=alt.Y("label:N", sort="-x", title=_y_label),
                )
            )
        elif _chart_type == "line":
            _chart = (
                alt.Chart(_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("label:N", title=_x_label, sort=None),
                    y=alt.Y(
                        "value:Q",
                        title=_y_label or "Value",
                        axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                )
            )
        else:  # pie
            _chart = (
                alt.Chart(_df)
                .mark_arc()
                .encode(
                    theta=alt.Theta("value:Q"),
                    color=alt.Color("label:N", title=_y_label),
                )
            )
        return _title, _chart.properties(title=_title)

    return (parse_chart_reply,)


@app.cell
def _(
    DATA_CONTEXT,
    api_key_input,
    json,
    mo,
    model_picker,
    parse_chart_reply,
    provider_picker,
):
    async def _post_json(url: str, headers: dict, payload: dict) -> dict:
        headers = {**headers, "content-type": "application/json"}
        body = json.dumps(payload)
        try:
            from pyodide.http import pyfetch  # running in the browser (WASM)

            resp = await pyfetch(url, method="POST", headers=headers, body=body)
            return await resp.json()
        except ImportError:  # running locally (marimo edit / run)
            import urllib.error
            import urllib.request

            req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                return json.loads(exc.read())

    async def _call_anthropic(key: str, model: str, messages) -> str:
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            # required for direct browser -> API calls (CORS); the "danger" is
            # exposing a key in shipped frontend code - here the user supplies
            # their own key at runtime, which is the intended BYO-key pattern
            "anthropic-dangerous-direct-browser-access": "true",
        }
        payload = {
            "model": model,
            "max_tokens": 2048,
            "system": DATA_CONTEXT,
            "messages": [{"role": m.role, "content": str(m.content)} for m in messages],
        }
        data = await _post_json("https://api.anthropic.com/v1/messages", headers, payload)
        if data.get("type") == "error":
            return f"**API error** ({data['error'].get('type')}): {data['error'].get('message')}"
        if data.get("stop_reason") == "refusal":
            return "The model declined to answer that request."
        texts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n\n".join(texts) or "*(empty response)*"

    async def _call_openai_compatible(url: str, key: str, model: str, messages) -> str:
        headers = {"Authorization": f"Bearer {key}"}
        _history = [{"role": m.role, "content": str(m.content)} for m in messages]
        payload = {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "system", "content": DATA_CONTEXT}, *_history],
        }
        data = await _post_json(url, headers, payload)
        if "error" in data:
            _err = data["error"]
            _msg = _err.get("message") if isinstance(_err, dict) else _err
            return f"**API error**: {_msg}"
        _choices = data.get("choices", [])
        if not _choices:
            return "*(empty response)*"
        return _choices[0].get("message", {}).get("content") or "*(empty response)*"

    async def _call_gemini(key: str, model: str, messages) -> str:
        _base = "https://generativelanguage.googleapis.com/v1beta/models"
        url = f"{_base}/{model}:generateContent?key={key}"
        _contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": str(m.content)}],
            }
            for m in messages
        ]
        payload = {
            "contents": _contents,
            "systemInstruction": {"parts": [{"text": DATA_CONTEXT}]},
        }
        data = await _post_json(url, {}, payload)
        if "error" in data:
            return f"**API error**: {data['error'].get('message')}"
        _candidates = data.get("candidates", [])
        if not _candidates:
            return "*(empty response)*"
        _parts = _candidates[0].get("content", {}).get("parts", [])
        _texts = [p["text"] for p in _parts if "text" in p]
        return "".join(_texts) or "*(empty response)*"

    async def _dispatch(messages, provider, key, model) -> str:
        if provider == "anthropic":
            return await _call_anthropic(key, model, messages)
        if provider == "openai":
            return await _call_openai_compatible(
                "https://api.openai.com/v1/chat/completions", key, model, messages
            )
        if provider == "gemini":
            return await _call_gemini(key, model, messages)
        if provider == "glm":
            return await _call_openai_compatible(
                "https://api.z.ai/api/paas/v4/chat/completions", key, model, messages
            )
        return f"Unknown provider: {provider}"

    async def chat_model(messages, config):
        key = api_key_input.value.strip()
        provider = provider_picker.value
        if not key:
            return "Please paste your API key above first."
        model = model_picker.value
        reply_text = await _dispatch(messages, provider, key, model)
        # If the model answered with a chart spec, render it; otherwise (most
        # replies, and any malformed spec) fall through to the raw text - the
        # chat model function must never crash on a bad/unexpected reply.
        parsed = parse_chart_reply(reply_text)
        if parsed is None:
            return reply_text
        title, chart = parsed
        return mo.vstack([mo.md(f"**{title}**"), chart])

    chat = mo.ui.chat(
        chat_model,
        prompts=[
            "Which airport is the most congested right now?",
            "How many arrivals did KUL get in the last 7 days, per day on average?",
            "What are the two closest airports, and the two farthest apart?",
            "Draw a bar chart of 7-day arrivals by airport.",
            "Pie chart: domestic vs international arrival origins.",
        ],
        show_configuration_controls=False,
    )
    chat
    return


if __name__ == "__main__":
    app.run()
