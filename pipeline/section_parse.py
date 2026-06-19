#!/usr/bin/env python3
"""Parse a section script.md into ordered beats.

Format (one beat per '## beat:' heading):

    # Section 1.1 — The Pythagorean Theorem            <- H1 title (ignored for narration)
    <!-- production notes, ignored -->

    ## beat: slide:slides/01-title.html
    > First spoken sentence.
    > Second spoken sentence.

    ## beat: manim:diagrams/hist.py:HistogramBuild
    > Narration spoken over the animation.

Visual specs:
    slide:<path.html>          -> rendered to PNG, Ken Burns motion clip
    manim:<file.py>:<Scene>    -> rendered with manim to an mp4 clip
    clip:<path.mp4>            -> a pre-rendered video clip used as-is

Narration = '> ' blockquote lines within a beat, EXCLUDING '> -' list items
(those are visual/director notes, never spoken).
"""
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Beat:
    visual: str                       # raw spec, e.g. "slide:slides/01.html"
    narration: str = ""
    notes: list = field(default_factory=list)

    @property
    def kind(self):
        return self.visual.split(":", 1)[0]

    @property
    def target(self):
        return self.visual.split(":", 1)[1]


def parse(script_path) -> list:
    text = Path(script_path).read_text(encoding="utf-8")
    beats, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^##\s*beat:\s*(.+?)\s*$", line)
        if m:
            cur = Beat(visual=m.group(1).strip())
            beats.append(cur)
            continue
        if cur is None:
            continue
        q = re.match(r"^>\s?(.*)$", line)
        if q:
            content = q.group(1).rstrip()
            if content.startswith("-"):          # '> -' = director note, not spoken
                cur.notes.append(content[1:].strip())
            elif content:
                cur.narration = (cur.narration + " " + content).strip()
    return beats
