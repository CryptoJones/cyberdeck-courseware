#!/usr/bin/env python3
"""Render a Cyberdeck HTML slide to a PNG via headless Chrome.

    render_slides.py <slide.html> <out.png> [width] [height]

Renders at 2x device scale (so a 1280x720 slide -> 2560x1440 PNG) for a crisp
source that the Ken Burns 5K upscale can push into without softening.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_chrome() -> str:
    """Locate a Chromium-family browser. Override with the CHROME env var."""
    env = os.environ.get("CHROME")
    if env:
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",  # Linux (PATH)
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return shutil.which(c)
    # Fall back to the macOS default; the run will raise a clear error if absent.
    return candidates[0]


CHROME = _find_chrome()


def render(html: Path, out: Path, w: int = 1280, h: int = 720):
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size={w},{h}",
        f"--screenshot={out}",
        html.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not out.exists():
        raise RuntimeError(f"Chrome did not produce {out}")
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    html = Path(sys.argv[1])
    out = Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    print(render(html, out, w, h))


if __name__ == "__main__":
    main()
