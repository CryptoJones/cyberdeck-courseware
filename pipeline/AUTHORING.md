# Authoring a section (read this fully before writing)

You are authoring one section of a Cyberdeck Courseware video course. The **gold
reference** is the bundled demo — study it before writing anything:

- `course/demo-pythagoras/script.md`
- `course/demo-pythagoras/slides/*.html`
- `course/demo-pythagoras/diagrams/pythagoras.py`

Match its structure, tone, and quality. Each section is a folder under `course/`
with `slides/` and `diagrams/` subfolders and a `script.md`, plus one row in
`course/manifest.tsv` (`slug  chapter  section  title  book_page`).

## Source content (do this first)
Gather the concepts, definitions, worked examples, and data the section needs from
**material you have the right to use**. Teach everything in **original wording** —
do not copy source sentences verbatim. Do not commit copyrighted source files into
a published repo (the `.gitignore` excludes `*.pdf`).

## script.md (the spine — narration + beats)
Format: one beat per `## beat:` heading; narration in `> ` lines (`> -` = director
note, never spoken):

```
# Section N.N — Title
production notes (ignored)

## beat: slide:slides/01-title.html
> Spoken sentence. Another spoken sentence.

## beat: manim:diagrams/<file>.py:<SceneClass>
> Narration spoken over the animation.
```

- **10–14 beats.** Arc: title → objectives → motivation/setup → core concept slides
  interleaved with **animated diagram beats** → worked example → recap → references.
- Narration ~700–900 words total, conversational, in a warm UK-female register
  (Kokoro `bf_emma`). **Write initialisms PLAIN** ("AI" not "A.I.") — TTS spells out
  dotted forms. Avoid symbols TTS mangles (write "minus 3", "times", "the square
  root of", "a squared").
- End every section with a `slides/NN-references.html` beat that credits **your**
  sources honestly (or notes the content is original, as the demo does).

## slides/*.html (Cyberdeck deck)
Copy a demo slide as your starting template. Each slide:
```html
<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="../../../pipeline/slides.css"></head>
<body> ... </body></html>
```
Use the existing classes: `.kicker .callout .badge .formula table .hl .cyan .green
.amber .violet .refs`, `<h1>/<h2>`, `<ul><li>`, `<footer>`. 1280×720, big fonts. Keep
each slide uncluttered (≤ ~5 bullets). Use `.formula` for equations, `table` for data.

**Bleed/safe area:** the render applies a gentle Ken Burns zoom (~2% crop per edge),
so keep content inside the body padding — never push tables or long lines to the very
edge. The CSS padding already reserves the margin; just don't fight it with content
wider than the frame (shorten long table cells rather than letting them overflow).

## diagrams/*.py (animated Manim — the headline feature)
Re-create every diagram as an original animated scene. One `.py` file per section is
fine, with multiple `Scene` classes inside it. Start each file with:
```python
from manim_cyberdeck import *
```
That gives the Cyberdeck config (1280×720, dark bg) + palette (`CYAN GREEN MINT FG DIM
RED AMBER VIOLET`, font `MONO`) + the `CyberScene` base (use `class X(CyberScene)` and
`self.title("...")`) + helpers like `neon_axes(...)`.

**Hard rules (learned the hard way):**
- **Keep diagrams inside the safe area.** The Manim frame is ~14.22 x 8 units; tall
  or wide figures clip at the edge. Build all parts, group them, and call
  `self.safe_fit(VGroup(...))` BEFORE animating — it scales the group into SAFE_W x
  SAFE_H and centres it below the title, keeping arrows attached.
- **No LaTeX required.** A plain Manim install has no LaTeX, so **avoid `MathTex`/`Tex`
  and `NumberLine(include_numbers=True)`** — use `Text(..., font=MONO)` and place tick
  labels manually with `Text(...).next_to(ax.c2p(v, 0), DOWN)`. Unicode like `²` is
  fine in on-screen `Text` (just not in narration).
- **Never call `Axis.add_labels()`** — it rescales/collapses the Axes.
- **Watch the Manim API:** animate a matrix with `mobj.animate.apply_matrix(M)`, not a
  bare `apply_matrix` inside `play()`. Prefer `LaggedStart(*[Anim(x) for x in group])`
  over `LaggedStartMap(lambda …)`, which misbehaves.
- Keep each scene ~6–14 s. Animate the *construction* (Create/Write/GrowFromEdge/
  FadeIn/Transform) so the figure is built, not just shown.

## VERIFY before you finish (required)
Test-render **every** Manim scene you wrote (fast, low quality) and fix any error:
```sh
PYTHONPATH=pipeline python -m manim -ql --media_dir /tmp/verify_<slug> \
  course/<slug>/diagrams/<file>.py <Scene1> <Scene2> ...
```
A scene counts as done only when it renders with no traceback. Don't run the full
`build_section.sh` to check diagrams — that batch render happens later.

**No-bleed QA gate (automatic).** `render_section.py` scans every beat's clean source
(slide PNG / raw Manim clip) with `qa_frames.py` and refuses to stitch if any content
sits in the outer ~2.5% edge band. Run it yourself on anything you render:
`python pipeline/qa_frames.py <file.png|file.mp4>`. If it reports `CLIP`, pull the
offending content inward (slides: stay inside the padding; diagrams: wrap everything
in `self.safe_fit(VGroup(...))`).

## Deliverable
For each section: `script.md`, `slides/NN-*.html` (including references), and
`diagrams/*.py` with all scenes test-rendering clean.
