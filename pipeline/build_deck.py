#!/usr/bin/env python3
"""Build a course's slide deck as a TYPESET-TEXT study-guide PDF.

One page per script beat, in lesson order: the slide's heading + bullets (or, for a
diagram beat, the diagram's title), the beat's NARRATION, the source citation, and a
ruled Notes area to write in while the video plays beside it. Real text — tiny,
vector-crisp, selectable — not slide screenshots.

    build_deck.py [--out dist/slides.pdf] [--only <slug>]

Run from the course ROOT (the dir with course/ and pipeline/). Parses course/
manifest.tsv for section order + titles, each section's script.md for beats +
narration, and each slide's HTML for its text, then Chrome-prints the assembled
handout. No image rasterizing, no ghostscript — output is a few hundred KB.
"""
import csv
import html as _html
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import render_slides  # noqa: E402  (Chrome locator)


def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


OUT = Path(_arg("--out", str(ROOT / "dist" / "slides.pdf"))).resolve()
ONLY = _arg("--only")


class _Slide(HTMLParser):
    """Pull kicker / heading / bullet items / footer-citation text from a slide."""

    def __init__(self):
        super().__init__()
        self.head, self.kick, self.lis, self.foot = [], [], [], []
        self.cur, self._buf = None, None

    def handle_starttag(self, t, attrs):
        d = dict(attrs)
        if t == "div" and "kicker" in d.get("class", ""):
            self.cur = "kick"
        elif t in ("h1", "h2"):
            self.cur = "head"
        elif t == "li":
            self.cur, self._buf = "li", []
        elif t == "footer":
            self.cur = "foot"

    def handle_endtag(self, t):
        if t == "li" and self._buf is not None:
            self.lis.append("".join(self._buf).strip())
            self._buf, self.cur = None, None
        elif t in ("div", "h1", "h2", "footer"):
            self.cur = None

    def handle_data(self, data):
        bucket = {"kick": self.kick, "head": self.head, "foot": self.foot}.get(self.cur)
        if bucket is not None:
            bucket.append(data)
        elif self.cur == "li" and self._buf is not None:
            self._buf.append(data)


def _norm(parts):
    return " ".join("".join(parts).split())


def _beats(slug):
    """[(kind, target, narration), ...] from a section's script.md, in order.
    kind is 'slide' or 'manim'; target is the slide path or the Scene name."""
    md = (ROOT / "course" / slug / "script.md").read_text(encoding="utf-8")
    out, spec, narr = [], None, []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("## beat:"):
            if spec:
                out.append((*spec, " ".join(narr).strip()))
            body = s.split("beat:", 1)[1].strip()
            if body.startswith("slide:"):
                spec, narr = ("slide", body[len("slide:"):].strip()), []
            elif body.startswith("manim:"):
                spec, narr = ("manim", body.split(":")[-1].strip()), []
            else:
                spec, narr = ("slide", body), []
        elif s.startswith(">"):
            narr.append(s[1:].strip())
    if spec:
        out.append((*spec, " ".join(narr).strip()))
    return out


def _humanize(scene):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", scene)  # CamelCase -> spaced


CSS = """
@page { size: Letter portrait; margin: 0.6in; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: Georgia,'Times New Roman',serif; color:#1a1a1a; }
.beat { page-break-after: always; }
.beat:last-child { page-break-after: auto; }
.sec { font-family:Arial,sans-serif; font-size:9pt; letter-spacing:.06em; color:#9a6a2f;
  border-bottom:1px solid #e2e2e6; padding-bottom:4px; margin-bottom:10px; }
.kicker { font-family:Arial,sans-serif; font-size:9.5pt; letter-spacing:.12em;
  text-transform:uppercase; color:#777; margin-bottom:2px; }
h2 { font-family:Arial,sans-serif; font-size:17pt; color:#111; margin-bottom:11px; }
ul { margin:0 0 12px 22px; } li { margin:6px 0; font-size:11.5pt; line-height:1.4; }
.narr { font-size:11.5pt; line-height:1.55; color:#222; border-left:3px solid #c9c9d0;
  padding-left:13px; margin:10px 0; }
.cite { font-family:Arial,sans-serif; font-size:8.5pt; color:#aaa; }
.nlabel { font-family:Arial,sans-serif; font-size:9pt; text-transform:uppercase;
  letter-spacing:.1em; color:#aaa; margin-top:14px; margin-bottom:4px; }
.notes { height:1.9in; background-image:repeating-linear-gradient(#fff 0 30px,#dcdce2 30px 32px); }
"""


def build():
    blocks, n = [], 0
    with open(ROOT / "course" / "manifest.tsv", encoding="utf-8") as f:
        sections = [(r["slug"], r.get("section", ""), r.get("title", ""))
                    for r in csv.DictReader(f, delimiter="\t")
                    if not ONLY or r["slug"] == ONLY]
    for slug, sec, title in sections:
        runhdr = _html.escape(f"§{sec} · {title}" if sec else title)
        for kind, target, narr in _beats(slug):
            kick = head = cite = lis = ""
            if kind == "slide":
                sp = ROOT / "course" / slug / target
                if sp.exists():
                    p = _Slide()
                    p.feed(sp.read_text(encoding="utf-8"))
                    kick, head, cite = _html.escape(_norm(p.kick)), _html.escape(_norm(p.head)), _html.escape(_norm(p.foot))
                    lis = "".join(f"<li>{_html.escape(' '.join(x.split()))}</li>"
                                  for x in p.lis if x.strip())
            else:  # manim diagram beat — no slide HTML, label by the scene
                kick, head = "Diagram", _html.escape(_humanize(target))
            blocks.append(
                '<div class="beat">'
                + f'<div class="sec">{runhdr}</div>'
                + (f'<div class="kicker">{kick}</div>' if kick else "")
                + (f"<h2>{head}</h2>" if head else "")
                + (f"<ul>{lis}</ul>" if lis else "")
                + (f'<div class="narr">{_html.escape(narr)}</div>' if narr else "")
                + (f'<div class="cite">{cite}</div>' if cite else "")
                + '<div class="nlabel">Notes</div><div class="notes"></div></div>'
            )
            n += 1
    if not blocks:
        sys.exit("build_deck: no beats found")
    tmp = Path(tempfile.mkdtemp(prefix="deck-"))
    page = tmp / "handout.html"
    page.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style>"
                    f"</head><body>{''.join(blocks)}</body></html>", encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([render_slides.CHROME, "--headless=new", "--disable-gpu",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000",
                    f"--print-to-pdf={OUT}", page.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not OUT.exists():
        sys.exit("build_deck: Chrome did not produce the PDF")
    print(f"deck: {n} pages -> {OUT}  ({OUT.stat().st_size / 1048576:.2f} MB)")


if __name__ == "__main__":
    build()
