#!/usr/bin/env python3
"""Build a single study-handout PDF of a course's entire slide deck.

Each page = one slide (rendered in the real deck look via render_slides) across
the top, with a ruled "Notes" area beneath for writing while you watch. Pages
follow manifest order, then slide-filename order within each section.

    build_deck.py [--out dist/slides.pdf] [--only <slug>]

Run from the course ROOT (the dir containing course/ and pipeline/). Reuses the
video pipeline's headless-Chrome rasterizer for the slides, then lays them into
a print HTML and lets Chrome print the multi-page PDF (no extra Python deps;
sidesteps Pillow's optional-JPEG PDF encoder).
"""
import html as _html
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import render_slides  # noqa: E402


def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


OUT = Path(_arg("--out", str(ROOT / "dist" / "slides.pdf"))).resolve()
ONLY = _arg("--only")

PAGE_CSS = """
@page { size: Letter portrait; margin: 0.5in; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; color: #18181c; }
.page { page-break-after: always; }
.page:last-child { page-break-after: auto; }
.hdr { font-size: 13pt; font-weight: bold; margin-bottom: 7px; }
.slide { width: 100%; display: block; border: 1px solid #d8d8de; }
.nlabel { font-size: 10.5pt; color: #6a6a72; letter-spacing: .08em;
          text-transform: uppercase; margin: 16px 0 4px; }
.notes { height: 3.7in;
         background-image: repeating-linear-gradient(#fff 0 31px, #dcdce2 31px 33px); }
"""


def _sections():
    import csv
    with open(ROOT / "course" / "manifest.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if ONLY and row["slug"] != ONLY:
                continue
            yield row["slug"], row.get("section", ""), row.get("title", "")


def build():
    tmp = Path(tempfile.mkdtemp(prefix="deck-"))
    blocks, n = [], 0
    for slug, sec, title in _sections():
        for html_path in sorted((ROOT / "course" / slug / "slides").glob("*.html")):
            png = tmp / f"{slug}-{html_path.stem}.png"
            try:
                render_slides.render(html_path, png)
            except Exception as e:  # one bad slide shouldn't sink the deck
                print(f"skip {html_path.name}: {e}", file=sys.stderr)
                continue
            hdr = _html.escape(f"§{sec}  {title}")
            blocks.append(
                f'<div class="page"><div class="hdr">{hdr}</div>'
                f'<img class="slide" src="{png.as_uri()}">'
                f'<div class="nlabel">Notes</div><div class="notes"></div></div>'
            )
            n += 1
    if not blocks:
        sys.exit("build_deck: no slides found")
    page = tmp / "handout.html"
    page.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><style>{PAGE_CSS}</style>"
        f"</head><body>{''.join(blocks)}</body></html>",
        encoding="utf-8",
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            render_slides.CHROME, "--headless=new", "--disable-gpu",
            "--no-pdf-header-footer", "--virtual-time-budget=20000",
            f"--print-to-pdf={OUT}", page.as_uri(),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if not OUT.exists():
        sys.exit("build_deck: Chrome did not produce the PDF")
    print(f"deck: {n} pages -> {OUT}")


if __name__ == "__main__":
    build()
