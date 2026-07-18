"""Render README.md into a static landing page at _site/index.html.

Run after the marimo/dbt-docs exports (site root must already contain
dashboard/, classic/, dbt-docs/) so relative links resolve correctly.
"""

import html
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SITE = ROOT / "_site"
DOCS_IMG_SRC = ROOT / "docs" / "img"
DOCS_IMG_DST = SITE / "docs" / "img"

SITE_BASE = "https://1bk.dev/simple-airports-analysis-v2/"

# Longest/most-specific URLs first so the bare base URL doesn't eat their prefixes.
LINK_REWRITES = [
    (SITE_BASE + "dbt-docs/", "dbt-docs/"),
    (SITE_BASE + "classic/", "classic/"),
    (SITE_BASE + "dashboard/", "dashboard/"),
    (SITE_BASE, "./"),  # bare root: self-link back to this landing page
]

STYLE = """
:root {
  color-scheme: light dark;
  --fg: #1f2328;
  --bg: #ffffff;
  --muted: #57606a;
  --border: #d0d7de;
  --code-bg: #f6f8fa;
  --link: #0969da;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #e6edf3;
    --bg: #0d1117;
    --muted: #8d96a0;
    --border: #30363d;
    --code-bg: #161b22;
    --link: #4493f8;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
  max-width: 900px;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif,
    "Apple Color Emoji", "Segoe UI Emoji";
  line-height: 1.6;
}
a { color: var(--link); }
h1, h2, h3, h4 { line-height: 1.25; }
h1 { border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
h2 { border-bottom: 1px solid var(--border); padding-bottom: 0.3em; margin-top: 2em; }
img { max-width: 100%; }
hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
table { border-collapse: collapse; width: 100%; overflow-x: auto; display: block; }
th, td { border: 1px solid var(--border); padding: 0.4em 0.8em; }
th { background: var(--code-bg); }
code {
  background: var(--code-bg);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1em;
  overflow-x: auto;
}
pre code { background: none; padding: 0; }
pre.mermaid {
  background: var(--bg);
  display: flex;
  justify-content: center;
}
blockquote {
  color: var(--muted);
  border-left: 4px solid var(--border);
  margin: 0;
  padding: 0 1em;
}
"""

MERMAID_SCRIPT = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'default' });
</script>
"""


def render_body(readme_text: str) -> str:
    body = markdown.markdown(readme_text, extensions=["extra", "toc"])

    # Turn <pre><code class="language-mermaid">...</code></pre> into
    # <pre class="mermaid">...</pre> (unescaped) so mermaid.js can render it.
    def _mermaid_sub(m: re.Match) -> str:
        code = html.unescape(m.group(1))
        return f'<pre class="mermaid">{code}</pre>'

    body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        _mermaid_sub,
        body,
        flags=re.DOTALL,
    )

    for absolute, relative in LINK_REWRITES:
        body = body.replace(f'"{absolute}"', f'"{relative}"')

    return body


def build() -> None:
    readme_text = README.read_text()
    body = render_body(readme_text)

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simple Airports Analysis v2 — Malaysia</title>
<style>{STYLE}</style>
{MERMAID_SCRIPT}
</head>
<body>
{body}
</body>
</html>
"""

    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(html_doc)

    if DOCS_IMG_SRC.is_dir():
        DOCS_IMG_DST.mkdir(parents=True, exist_ok=True)
        for img in DOCS_IMG_SRC.iterdir():
            if img.is_file():
                shutil.copy2(img, DOCS_IMG_DST / img.name)

    # Belt-and-suspenders: marimo exports already create this, but make sure
    # it exists at the site root regardless of export order.
    (SITE / ".nojekyll").touch()

    print(f"Wrote {SITE / 'index.html'}")


if __name__ == "__main__":
    build()
