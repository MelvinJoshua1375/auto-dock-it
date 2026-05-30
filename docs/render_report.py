"""Render docs/REPORT.md to docs/REPORT.pdf with a clean print stylesheet."""
from pathlib import Path

import markdown
from weasyprint import HTML, CSS


HERE = Path(__file__).resolve().parent
MD_PATH = HERE / "REPORT.md"
PDF_PATH = HERE / "REPORT.pdf"

CSS_TEXT = """
@page {
  size: A4;
  margin: 22mm 18mm 22mm 18mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-size: 9pt;
    color: #888;
  }
}
body {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1c1c1c;
}
h1 {
  font-size: 22pt;
  margin: 0 0 4mm 0;
  border-bottom: 2px solid #0db7ed;
  padding-bottom: 2mm;
}
h2 {
  font-size: 14pt;
  margin: 8mm 0 2mm 0;
  color: #0a6f8c;
  border-bottom: 1px solid #ddd;
  padding-bottom: 1mm;
}
h3 {
  font-size: 12pt;
  margin: 6mm 0 1mm 0;
  color: #444;
}
p { margin: 0 0 3mm 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 3mm 0 4mm 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #ccc;
  padding: 4px 8px;
  text-align: left;
  vertical-align: top;
}
th { background: #f3f7fa; font-weight: 600; }
code {
  font-family: "Menlo", "Consolas", monospace;
  font-size: 9pt;
  background: #f4f4f4;
  padding: 1px 4px;
  border-radius: 3px;
}
pre {
  background: #1e1e1e;
  color: #e0e0e0;
  padding: 6px 9px;
  border-radius: 4px;
  font-size: 8.5pt;
  line-height: 1.35;
  overflow-x: auto;
  page-break-inside: avoid;
}
pre code { background: transparent; color: inherit; padding: 0; }
a { color: #0a6f8c; text-decoration: none; }
hr { border: none; border-top: 1px solid #ddd; margin: 6mm 0; }
ul, ol { margin: 0 0 3mm 5mm; padding: 0; }
li { margin: 1mm 0; }
strong { color: #111; }
"""


def main() -> None:
    md_text = MD_PATH.read_text()
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Auto-Dock It Report</title></head>
<body>{html_body}</body></html>"""
    HTML(string=html_doc).write_pdf(PDF_PATH, stylesheets=[CSS(string=CSS_TEXT)])
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
