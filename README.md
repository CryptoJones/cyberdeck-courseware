<p align="center"><em>Proudly Made in Nebraska. Go Big Red! 🌽 <a href="https://xkcd.com/2347/">https://xkcd.com/2347/</a></em></p>

# Cyberdeck Courseware

**Turn a set of lecture notes into a narrated, animated video course — and never ship a frame that bleeds off the edge.**

Cyberdeck Courseware is a small, hackable pipeline that builds slide-based
educational videos in a neon "cyberdeck" visual style. You write three things per
section — a narration script, some HTML slides, and (optionally) animated
[Manim](https://www.manim.community/) diagrams — and the pipeline produces a
single stitched `.mp4` with local neural narration, a gentle Ken Burns push-in,
and a particle overlay.

Its defining feature is a **QA gate baked into the render**: before a section is
stitched, every clean slide frame and raw diagram clip is scanned for bright
content intruding into the outer 2.5% edge band. If anything bleeds, **the build
fails** — so a malformed slide can't silently become a finished video.

> **Want to see it?** A complete worked example ships in
> [`course/demo-pythagoras/`](course/demo-pythagoras/) — an original section on the
> Pythagorean theorem (public-domain math), with slides and three animated Manim
> scenes. Render it in one command (below).

---

## How it works

```
  script.md ─┬─ slide beats  ──▶ headless Chrome ──▶ PNG ─┐
             │                                            ├─▶ QA gate (no-bleed) ─┬─ FAIL ▶ stop the build
             └─ manim beats  ──▶ Manim CE      ──▶ clip ─┘                        │
                                                                                  └─ PASS ▶
   Ken Burns zoompan (5K upscale, center-anchored)  +  neon particle overlay (screen blend)
                                  +  Kokoro neural TTS narration (bf_emma @ 0.88)
                                  ▼
                       ffmpeg xfade-stitch ──▶ course/<section>/out/section.mp4
                                  ▼
                       build_site.py ──▶ a static index site (dist/)
```

Every production tunable (voice, speed, crossfade, zoom, fps, resolution) is an
environment variable with a locked-in default — see the top of
[`pipeline/build_section.sh`](pipeline/build_section.sh).

## Quickstart

**Prerequisites:** Python 3.11+, [FFmpeg](https://ffmpeg.org/), and a
Chromium-family browser (Chrome/Chromium). LaTeX is **not** required — the demo
diagrams use plain text so Manim renders without it.

```sh
# 1. Install Python deps (a venv is recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

# 2. Fetch the Kokoro neural-TTS weights (~337 MB, gitignored)
pipeline/fetch_models.sh

# 3. Point the pipeline at your browser if it isn't auto-detected
export CHROME="/path/to/chrome"     # macOS Chrome is auto-detected; Linux uses $PATH

# 4. Render the demo section  ->  course/demo-pythagoras/out/section.mp4
pipeline/build_section.sh demo-pythagoras

# 5. Or render every section in the manifest, then build the index site
pipeline/render_all.sh
python3 pipeline/build_site.py
```

The QA gate is on by default. To inspect a bleed failure without it stopping the
build, set `QA_STRICT=0`.

## Authoring your own course

A course is just a `course/` directory with a `manifest.tsv` and one folder per
section. Read [`pipeline/AUTHORING.md`](pipeline/AUTHORING.md) for the full spec;
the short version:

```
course/
  manifest.tsv                 # slug  chapter  section  title  book_page
  <section-slug>/
    script.md                  # narration + beat list (the spine)
    slides/*.html              # Cyberdeck HTML slides (link ../../../pipeline/slides.css)
    diagrams/*.py              # animated Manim scenes (from manim_cyberdeck import *)
```

`script.md` is a list of **beats**, each either a slide or a Manim scene, with the
spoken narration in `>` lines:

```
## beat: slide:slides/01-title.html
> The words spoken over this slide.

## beat: manim:diagrams/pythagoras.py:RightTriangle
> The words spoken over this animation.
```

Diagrams subclass `CyberScene` and call `self.safe_fit(group)` to stay inside the
safe area — the same constraint the QA gate enforces on the output. Write math
*plainly* in narration ("a squared", "the square root of") so the TTS speaks it
correctly.

## Repo layout

| Path | What |
|---|---|
| `pipeline/` | The engine: render, QA gate, TTS, particles, Manim helpers, site builder |
| `pipeline/qa_frames.py` | The no-bleed gate (luma threshold, edge inset, min-pixel count) |
| `pipeline/manim_cyberdeck.py` | `CyberScene` base, neon palette, `safe_fit`, `neon_axes` |
| `pipeline/AUTHORING.md` | Full section-authoring guide |
| `course/demo-pythagoras/` | A complete, original worked example |

## Third-party tools & models

This repo contains original pipeline code only. At runtime it uses Manim CE, the
Kokoro ONNX TTS weights (fetched separately), FFmpeg, and a headless Chromium —
see [`NOTICE`](NOTICE) for details and licenses.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). Copyright 2026 Aaron K. Clark.

The bundled demo course is original work on a public-domain topic. **Do not commit
copyrighted source textbooks or course inputs** into a repository you publish; the
`.gitignore` already excludes `*.pdf` for this reason.
