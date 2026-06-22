#!/usr/bin/env python3
"""Generate the Cyberdeck Courseware landing page.

Reads course/manifest.tsv, groups sections by chapter, links each rendered video.

  pipeline/build_site.py                 # local preview: site/index.html, links ../course/<slug>/out/section.mp4
  pipeline/build_site.py --bundle DIR    # deployable bundle: DIR/index.html + DIR/videos/<slug>.mp4 (relative links)

In --bundle mode each video is wrapped in a player page DIR/videos/<slug>.html that
AUTO-ADVANCES to the next section when the video truly ends (real `ended` event, a
sessionStorage flag so the next page auto-plays through autoplay-blocks, and a
remembered "Autoplay next" toggle) — and the index links the player pages, not the
raw mp4s. No wall-clock timers. Pattern from the AKC-Neuromancer listen deck.

Configure at runtime — CLI flag wins, then COURSE_* env, then default — so ONE
build_site.py serves any course with nothing hardcoded:
  --title    / COURSE_TITLE     page title + H1   (default "Cyberdeck Courseware")
  --subtitle / COURSE_SUBTITLE  the note under H1 (default a generic blurb)
  --tag      / COURSE_TAG       header kicker + footer credit (default "Cyberdeck Courseware")
  --accent   / COURSE_ACCENT    monochrome accent hex, e.g. #15d6c0; default keeps
                                the multi-color cyan/green/mint cyberdeck scheme
  course/chapters.tsv  optional "chapter<TAB>name" rows for chapter headings

  pipeline/build_site.py --bundle dist --title "My Course" --accent "#ff6a00"

The --bundle output is host-agnostic: index.html links videos/<slug>.html relatively,
so serving DIR at any URL path just works. Videos are hardlinked when on the same
filesystem, else copied.
"""
import csv
import html
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _arg(flag):
    """Value after a CLI flag (e.g. --accent #15d6c0), or None if absent."""
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


def _cfg(flag, env, default):
    """One config value: CLI flag wins, then env var, then default — so a SINGLE
    build_site.py serves every course with nothing hardcoded. Each course just
    passes its own --title / --subtitle / --accent / --tag (or COURSE_* env)."""
    val = _arg(flag)
    return val if val is not None else os.environ.get(env, default)


# Per-course identity — all runtime parameters, zero hardcoding:
TITLE = _cfg("--title", "COURSE_TITLE", "Cyberdeck Courseware")
SUBTITLE = _cfg("--subtitle", "COURSE_SUBTITLE",
                "A free video course. Each section is a narrated lesson with animated diagrams.")
TAG = _cfg("--tag", "COURSE_TAG", "")  # optional header kicker; omitted when empty

#: The default cyberdeck cyan-scheme. Passing an accent (--accent / COURSE_ACCENT)
#: recolors all three to that one hex (per-course monochrome); default keeps it.
SCHEME = ("#27d4ff", "#55ff99", "#9fffe0")
ACCENT = _cfg("--accent", "COURSE_ACCENT", "")


def _recolor(s):
    """Collapse the cyan-scheme to ACCENT (monochrome), or return s unchanged."""
    if not ACCENT:
        return s
    for hexc in SCHEME:
        s = s.replace(hexc, ACCENT)
    return s

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

PLAYER_PAGE = """<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{course} — {num} {title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#07090f;color:#cfd8e3;font-family:Menlo,Consolas,monospace;
  line-height:1.5;padding:28px 5vw 70px;font-size:17px}}
a{{color:#27d4ff;text-decoration:none}} a:hover{{text-shadow:0 0 10px #27d4ff66}}
.back{{color:#5a6678;font-size:14px;letter-spacing:1px;text-transform:uppercase}}
h1{{color:#27d4ff;font-size:30px;margin:10px 0 22px;text-shadow:0 0 14px #27d4ff55}}
h1 .num{{color:#55ff99;margin-right:12px}}
.stage{{background:#000;border:1px solid #141a26;border-radius:12px;overflow:hidden;
  box-shadow:0 0 40px #27d4ff11}}
video{{display:block;width:100%;max-height:78vh;background:#000}}
.bar{{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-top:18px;
  padding:14px 16px;border:1px solid #141a26;border-radius:10px;background:#0c1320}}
.nav{{padding:8px 16px;border:1px solid #27d4ff44;border-radius:8px;color:#cfd8e3;
  background:#0e1a2c}}
.nav:hover{{border-color:#27d4ff;background:#13233a}}
.nav.disabled{{opacity:.35;pointer-events:none;border-color:#141a26}}
.upnext{{flex:1;color:#9fffe0;font-size:15px;text-align:center;min-width:160px}}
.toggle{{display:flex;align-items:center;gap:8px;color:#55ff99;font-size:14px;
  cursor:pointer;user-select:none}}
.toggle input{{accent-color:#55ff99;width:16px;height:16px;cursor:pointer}}
footer{{margin-top:26px;color:#5a6678;font-size:13px;border-top:1px solid #141a26;
  padding-top:14px}}
</style></head><body>
<a class='back' href='../index.html'>&#9664; {course}</a>
<h1><span class='num'>{num}</span>{title}</h1>
<div class='stage'><video id='v' controls playsinline autoplay preload='auto'
  src='{slug}.mp4'></video></div>
<div class='bar'>
  <a class='nav prev' href='{prev}'>&#9664; Prev</a>
  <label class='toggle'><input type='checkbox' id='auto' checked> Autoplay next</label>
  <span class='upnext'>{upnext}</span>
  <a class='nav next {nextcls}' href='{next}'>Next &#9654;</a>
</div>
<footer>{course} &middot; <em>Made in Nebraska 🌽</em></footer>
<script>
const NEXT={next_js};                         // next player page, or "" at course end
const _v=document.getElementById('v'), _t=document.getElementById('auto');
try{{if(localStorage.getItem('cw_autoplay')==='0')_t.checked=false;}}catch(e){{}}
_t.addEventListener('change',()=>{{try{{localStorage.setItem('cw_autoplay',_t.checked?'1':'0')}}catch(e){{}}}});
try{{sessionStorage.removeItem('cw_autonext');}}catch(e){{}}
_v.play().catch(()=>{{}});  // attempt autoplay every page (browser may block w/ sound until first interaction)
_v.addEventListener('ended',function(){{
  if(!NEXT) return;
  if(_t && !_t.checked) return;
  try{{sessionStorage.setItem('cw_autonext','1')}}catch(e){{}}
  location.href=NEXT;
}});
</script></body></html>"""


def load_chapter_names():
    """Optional course/chapters.tsv: 'chapter<TAB>name' rows. Missing -> empty names."""
    p = ROOT / "course" / "chapters.tsv"
    names = {}
    if p.exists():
        for row in csv.reader(p.open(), delimiter="\t"):
            if len(row) >= 2 and row[0].strip() and not row[0].startswith("#"):
                names[row[0].strip()] = row[1].strip()
    return names


def write_player_pages(bundle, rendered):
    """rendered = [(slug, section, title), ...] in play order. Writes one auto-advancing
    player page per section, chained over THIS list (so next/prev never hit a 404)."""
    vdir = bundle / "videos"
    tmpl = _recolor(PLAYER_PAGE)
    for i, (slug, section, title) in enumerate(rendered):
        last = i == len(rendered) - 1
        nxt = "" if last else rendered[i + 1][0] + ".html"
        prv = "../index.html" if i == 0 else rendered[i - 1][0] + ".html"
        upnext = "Course complete &#10003;" if last else f"Up next: {html.escape(rendered[i + 1][2])}"
        page = tmpl.format(
            course=html.escape(TITLE), num=html.escape(section),
            title=html.escape(title), slug=html.escape(slug),
            prev=prv, next=(nxt or "../index.html"),
            nextcls="disabled" if last else "", upnext=upnext, next_js=json.dumps(nxt))
        (vdir / f"{slug}.html").write_text(page, encoding="utf-8")


def main():
    rows = list(csv.DictReader((ROOT / "course/manifest.tsv").open(), delimiter="\t"))
    rows.sort(key=lambda r: [int(p) for p in r["section"].split(".")])
    chapter_names = load_chapter_names()

    parts = ["<!doctype html><html><head><meta charset='utf-8'>",
             f"<title>{html.escape(TITLE)}</title>",
             f"<style>{_recolor(CSS)}</style></head><body>",
             "<header>" + (f"<div class='tag'>{html.escape(TAG)}</div>" if TAG else ""),
             f"<h1>{html.escape(TITLE)}</h1>",
             f"<div class='note'>{html.escape(SUBTITLE)}</div></header>"]

    bundle = None
    if "--bundle" in sys.argv:
        bundle = Path(sys.argv[sys.argv.index("--bundle") + 1]).resolve()
        (bundle / "videos").mkdir(parents=True, exist_ok=True)

    done = 0
    last_ch = None
    rendered = []  # (slug, section, title) in order, for player-page chain (bundle mode)
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
                rendered.append((r["slug"], r["section"], r["title"]))
                href = f"videos/{r['slug']}.html"   # link the auto-advancing player page
            else:
                href = f"../course/{r['slug']}/out/section.mp4"
            parts.append(f"<a class='row' href='{href}'><span class='num'>{r['section']}</span>"
                         f"<span class='ttl'>{r['title']}</span>"
                         f"<span class='badge'>watch ▸</span></a>")
        else:
            parts.append(f"<a class='row todo'><span class='num'>{r['section']}</span>"
                         f"<span class='ttl'>{r['title']}</span>"
                         f"<span class='badge todo'>rendering…</span></a>")

    parts.append(f"<footer>{done} of {len(rows)} sections rendered.<br><br>"
                 "<em>Proudly Made in Nebraska. Go Big Red! 🌽 "
                 "https://xkcd.com/2347/</em></footer></body></html>")

    out = (bundle / "index.html") if bundle else (ROOT / "site" / "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    if bundle:
        write_player_pages(bundle, rendered)
    where = f"bundle {bundle}" if bundle else str(out)
    extra = f" + {len(rendered)} player pages" if bundle else ""
    print(f"{where}  ({done}/{len(rows)} videos linked{extra})")


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
