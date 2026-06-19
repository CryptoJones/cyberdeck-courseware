#!/usr/bin/env python3
"""Generate the Cyberdeck Courseware landing page.

Reads course/manifest.tsv, groups sections by chapter, links each rendered video.

  pipeline/build_site.py                 # local preview: site/index.html, links ../course/<slug>/out/section.mp4
  pipeline/build_site.py --bundle DIR    # deployable bundle: DIR/index.html + DIR/videos/<slug>.mp4 (relative links)

Configure the page without editing code:
  COURSE_TITLE      page title + H1     (default "Cyberdeck Courseware")
  COURSE_SUBTITLE   the note under H1   (default a generic blurb)
  course/chapters.tsv  optional "chapter<TAB>name" rows for chapter headings

The --bundle output is host-agnostic: index.html links videos/<slug>.mp4 relatively,
so serving DIR at any URL path just works. Videos are hardlinked when on the same
filesystem, else copied.
"""
import csv
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE = os.environ.get("COURSE_TITLE", "Cyberdeck Courseware")
SUBTITLE = os.environ.get(
    "COURSE_SUBTITLE",
    "A free video course. Each section is a narrated lesson with animated diagrams.",
)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#07090f;color:#cfd8e3;font-family:Menlo,Consolas,monospace;
  font-size:18px;line-height:1.5;padding:48px 7vw 80px}
header{border-bottom:2px solid #27d4ff;padding-bottom:22px;margin-bottom:32px}
h1{color:#27d4ff;font-size:40px;text-shadow:0 0 16px #27d4ff66}
.tag{color:#55ff99;letter-spacing:2px;text-transform:uppercase;font-size:14px;margin-bottom:10px}
.note{color:#5a6678;font-size:15px;margin-top:14px;max-width:60ch}
.chap{margin:34px 0 10px;color:#9fffe0;font-size:24px;
  border-left:3px solid #55ff99;padding-left:14px}
a.row{display:flex;gap:16px;align-items:baseline;text-decoration:none;color:#cfd8e3;
  padding:11px 14px;border:1px solid #141a26;border-radius:8px;margin:7px 0;
  background:#0c1320;transition:.15s}
a.row:hover{background:#13233a;border-color:#27d4ff55}
a.row.todo{opacity:.5;cursor:default;pointer-events:none}
.num{color:#27d4ff;font-weight:700;min-width:54px}
.ttl{flex:1}
.badge{font-size:12px;padding:2px 10px;border-radius:12px;border:1px solid #55ff99;
  color:#55ff99}
.badge.todo{border-color:#5a6678;color:#5a6678}
footer{margin-top:48px;color:#5a6678;font-size:14px;border-top:1px solid #141a26;padding-top:18px}
footer em{color:#88aaaa}
"""


def load_chapter_names():
    """Optional course/chapters.tsv: 'chapter<TAB>name' rows. Missing -> empty names."""
    p = ROOT / "course" / "chapters.tsv"
    names = {}
    if p.exists():
        for row in csv.reader(p.open(), delimiter="\t"):
            if len(row) >= 2 and row[0].strip() and not row[0].startswith("#"):
                names[row[0].strip()] = row[1].strip()
    return names


def main():
    rows = list(csv.DictReader((ROOT / "course/manifest.tsv").open(), delimiter="\t"))
    rows.sort(key=lambda r: [int(p) for p in r["section"].split(".")])
    chapter_names = load_chapter_names()

    parts = ["<!doctype html><html><head><meta charset='utf-8'>",
             f"<title>{TITLE}</title>",
             f"<style>{CSS}</style></head><body>",
             "<header><div class='tag'>Cyberdeck Courseware</div>",
             f"<h1>{TITLE}</h1>",
             f"<div class='note'>{SUBTITLE}</div></header>"]

    bundle = None
    if "--bundle" in sys.argv:
        bundle = Path(sys.argv[sys.argv.index("--bundle") + 1]).resolve()
        (bundle / "videos").mkdir(parents=True, exist_ok=True)

    done = 0
    last_ch = None
    for r in rows:
        ch = r["chapter"]
        if ch != last_ch:
            name = chapter_names.get(ch, "")
            label = f"Chapter {ch} · {name}" if name else f"Chapter {ch}"
            parts.append(f"<div class='chap'>{label}</div>")
            last_ch = ch
        mp4 = ROOT / "course" / r["slug"] / "out" / "section.mp4"
        if mp4.exists():
            done += 1
            if bundle:
                dst = bundle / "videos" / f"{r['slug']}.mp4"
                _place(mp4, dst)
                href = f"videos/{r['slug']}.mp4"
            else:
                href = f"../course/{r['slug']}/out/section.mp4"
            parts.append(f"<a class='row' href='{href}'><span class='num'>{r['section']}</span>"
                         f"<span class='ttl'>{r['title']}</span>"
                         f"<span class='badge'>watch ▸</span></a>")
        else:
            parts.append(f"<a class='row todo'><span class='num'>{r['section']}</span>"
                         f"<span class='ttl'>{r['title']}</span>"
                         f"<span class='badge todo'>rendering…</span></a>")

    parts.append(f"<footer>{done} of {len(rows)} sections rendered. "
                 "Built with <em>Cyberdeck Courseware</em>.<br><br>"
                 "<em>Proudly Made in Nebraska. Go Big Red! 🌽 "
                 "https://xkcd.com/2347/</em></footer></body></html>")

    out = (bundle / "index.html") if bundle else (ROOT / "site" / "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    where = f"bundle {bundle}" if bundle else str(out)
    print(f"{where}  ({done}/{len(rows)} videos linked)")


def _place(src: Path, dst: Path):
    """Hardlink src->dst (cheap, same fs) or copy if it already differs/cross-fs."""
    if dst.exists():
        if dst.stat().st_size == src.stat().st_size:
            return  # already placed
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


if __name__ == "__main__":
    main()
