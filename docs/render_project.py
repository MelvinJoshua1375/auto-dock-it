"""Render docs/PROJECT.md to a self-contained, browser-friendly HTML file.

Usage: python docs/render_project.py [--open]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys

import markdown


HERE = Path(__file__).resolve().parent
MD_PATH = HERE / "PROJECT.md"
HTML_PATH = HERE / "PROJECT.html"


CSS_TEXT = """
:root {
  --bg: #fafafa;
  --fg: #1c1c1c;
  --muted: #555;
  --accent: #0a6f8c;
  --accent-bright: #0db7ed;
  --code-bg: #f4f4f4;
  --pre-bg: #1e1e1e;
  --pre-fg: #e0e0e0;
  --border: #e0e0e0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #181818;
    --fg: #e8e8e8;
    --muted: #aaa;
    --accent: #0db7ed;
    --accent-bright: #4dd0ff;
    --code-bg: #2a2a2a;
    --pre-bg: #0e0e0e;
    --pre-fg: #e8e8e8;
    --border: #333;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: var(--fg);
  background: var(--bg);
  margin: 0;
  padding: 32px 16px 64px;
}
.container {
  max-width: 880px;
  margin: 0 auto;
}
h1, h2, h3, h4 {
  color: var(--fg);
  margin-top: 1.6em;
  margin-bottom: 0.6em;
  line-height: 1.25;
  scroll-margin-top: 16px;
}
h1 {
  font-size: 2.1em;
  border-bottom: 2px solid var(--accent-bright);
  padding-bottom: 0.3em;
  margin-top: 0;
}
h2 {
  font-size: 1.55em;
  color: var(--accent);
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.2em;
}
h3 { font-size: 1.25em; color: var(--accent); }
h4 { font-size: 1.05em; }
p, ul, ol { margin: 0.7em 0; }
ul, ol { padding-left: 1.6em; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  font-family: "JetBrains Mono", Menlo, Consolas, monospace;
  font-size: 0.92em;
  background: var(--code-bg);
  padding: 1px 5px;
  border-radius: 4px;
}
pre {
  background: var(--pre-bg);
  color: var(--pre-fg);
  padding: 14px 18px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.88em;
  line-height: 1.45;
}
pre code { background: transparent; color: inherit; padding: 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.94em;
}
th, td {
  border: 1px solid var(--border);
  padding: 8px 12px;
  text-align: left;
  vertical-align: top;
}
th { background: var(--code-bg); font-weight: 600; }
blockquote {
  border-left: 4px solid var(--accent-bright);
  margin: 1em 0;
  padding: 0.4em 1em;
  color: var(--muted);
  background: var(--code-bg);
}
hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
strong { color: var(--fg); }
.toc-floating {
  position: fixed;
  top: 12px;
  right: 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.84em;
  max-width: 220px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.toc-floating summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--accent);
}
.toc-floating ol { padding-left: 1.2em; margin: 0.4em 0 0; }
.toc-floating li { margin: 2px 0; }
.toc-floating a { color: var(--fg); }
@media (max-width: 1100px) {
  .toc-floating { display: none; }
}
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auto-Dock It: Project Reference</title>
<style>{css}</style>
</head>
<body>
<details class="toc-floating" open>
  <summary>On this page</summary>
  <ol>{floating_toc}</ol>
</details>
<main class="container">
{body}
</main>
</body>
</html>
"""


def _extract_h2_anchors(html: str) -> str:
    items = []
    for m in re.finditer(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', html, re.DOTALL):
        anchor, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        items.append(f'<li><a href="#{anchor}">{title}</a></li>')
    return "\n".join(items)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true", help="Open the rendered HTML in the default browser")
    args = parser.parse_args()

    md_text = MD_PATH.read_text()
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
    )
    floating_toc = _extract_h2_anchors(body)
    html = HTML_TEMPLATE.format(css=CSS_TEXT, body=body, floating_toc=floating_toc)
    HTML_PATH.write_text(html)
    print(f"Wrote {HTML_PATH}")

    if args.open:
        try:
            subprocess.run(["xdg-open", str(HTML_PATH)], check=False)
        except FileNotFoundError:
            print("xdg-open not found. Open the file manually:", HTML_PATH, file=sys.stderr)


if __name__ == "__main__":
    main()
