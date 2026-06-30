#!/usr/bin/env python3
"""Pre-render lint for course manim diagrams — catches known manim-0.20 footguns
so a bad arrow animation fails in SECONDS instead of hanging the render ~20 min.

Known crash: LaggedStartMap(GrowArrow, <arrows>) / LaggedStartMap(Create, <arrows>)
on manim 0.20 raises "ArrowTriangleFilledTip has no attribute hex" mid-render and
produces NO output clip (render deadlocks). Fix: animate arrows with FadeIn, or call
GrowArrow(a) per arrow as separate .play() args.
"""
import re, sys, pathlib
BAD = re.compile(r"LaggedStartMap\(\s*GrowArrow\b")
SUSPECT = re.compile(r"LaggedStartMap\(\s*Create\b")
root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "diagrams")
errs, warns = [], []
for f in sorted(root.glob("*.py")):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        s = line.strip()
        if BAD.search(line):
            errs.append(f"{f.name}:{i}: LaggedStartMap(GrowArrow,...) is the manim-0.20 arrow-tip crash (no clip, render hangs). Use LaggedStartMap(FadeIn,...) or GrowArrow(a) per arrow.  [{s}]")
        elif SUSPECT.search(line):
            warns.append(f"{f.name}:{i}: LaggedStartMap(Create,...) is safe for Text/rectangles; if these mobjects are Arrow/tipped, switch to FadeIn.  [{s}]")
for w in warns: print("DIAGRAM-LINT WARN: " + w, file=sys.stderr)
for e in errs: print("DIAGRAM-LINT ERROR: " + e, file=sys.stderr)
sys.exit(1 if errs else 0)
