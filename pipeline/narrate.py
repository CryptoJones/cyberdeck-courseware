#!/usr/bin/env python3
"""Write a teleprompter transcript for a section (all beat narration, in order).

    narrate.py <section-dir>     # reads <dir>/script.md -> <dir>/narration-transcript.txt
"""
import sys
from pathlib import Path

from section_parse import parse


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sec = Path(sys.argv[1])
    beats = parse(sec / "script.md")
    lines = []
    for i, b in enumerate(beats, 1):
        lines.append(f"[beat {i} · {b.visual}]")
        lines.append(b.narration or "(no narration)")
        lines.append("")
    out = sec / "narration-transcript.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    words = sum(len(b.narration.split()) for b in beats)
    print(f"{out}  ({len(beats)} beats, ~{words} words, ~{words/150:.1f} min @150wpm)")


if __name__ == "__main__":
    main()
