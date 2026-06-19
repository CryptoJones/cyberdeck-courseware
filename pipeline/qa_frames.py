#!/usr/bin/env python3
"""QA gate — scan rendered frames for content clipped at, or crowding, the frame edge.

This is the pipeline's "no bleed" guarantee: render_section.py runs it on EVERY beat
of EVERY video before stitching, so nothing with content jammed against the frame edge
ever ships. It scans the CLEAN intermediates (slide PNGs and raw Manim clips, which
have no particle overlay), where edge detection is exact and free of false positives.

A "violation" = bright, non-background content inside the outer safe band (a margin of
INSET on every edge). Background (the Cyberdeck near-black + gradient + grid) sits far
below the luminance threshold, so only real text/diagram pixels trip it.

CLI:
    qa_frames.py <file.png|file.mp4> [...]      # exit 1 if any file has edge content
    qa_frames.py --inset 0.025 --every 1 <...>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LUMA_THRESH = 70.0   # background features peak ~30; real content (dim text) ~100+
INSET = 0.025        # safe band = outer 2.5% of each edge
MIN_PIX = 12         # this many bright pixels in a band => content intrusion
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _luma(rgb):  # rgb float32 HxWx3 -> HxW
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def scan_luma(luma, inset=INSET, thresh=LUMA_THRESH, min_pix=MIN_PIX):
    """Return {edge: bright_pixel_count} for any edge whose safe band holds content."""
    h, w = luma.shape
    by = max(1, int(round(h * inset)))
    bx = max(1, int(round(w * inset)))
    bands = {
        "top": luma[:by, :],
        "bottom": luma[h - by:, :],
        "left": luma[:, :bx],
        "right": luma[:, w - bx:],
    }
    hits = {}
    for name, band in bands.items():
        c = int((band > thresh).sum())
        if c >= min_pix:
            hits[name] = c
    return hits


def scan_image(path, **kw):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    return scan_luma(_luma(arr), **kw)


def _dims(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)])
    w, h = out.decode().strip().split("x")
    return int(w), int(h)


def scan_video(path, every=1, **kw):
    """Decode every frame (or every Nth) as rgb24 and return worst {edge: count}."""
    w, h = _dims(path)
    fsize = w * h * 3
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    worst, idx = {}, 0
    try:
        while True:
            raw = proc.stdout.read(fsize)
            if len(raw) < fsize:
                break
            if idx % every == 0:
                arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).astype(np.float32)
                for e, c in scan_luma(_luma(arr), **kw).items():
                    worst[e] = max(worst.get(e, 0), c)
            idx += 1
    finally:
        proc.stdout.close()
        proc.wait()
    return worst


def check(path, every=1, **kw):
    """Scan an image or video; return {} if clean, else {edge: worst_count}."""
    path = Path(path)
    if path.suffix.lower() in IMG_EXT:
        return scan_image(path, **kw)
    return scan_video(path, every=every, **kw)


def main():
    args, inset, every = [], INSET, 1
    it = iter(sys.argv[1:])
    for a in it:
        if a == "--inset":
            inset = float(next(it))
        elif a == "--every":
            every = int(next(it))
        else:
            args.append(a)
    if not args:
        sys.exit(__doc__)
    bad = False
    for a in args:
        hits = check(a, inset=inset, every=every)
        if hits:
            bad = True
            edges = ", ".join(f"{e}:{c}" for e, c in sorted(hits.items()))
            print(f"CLIP  {a}  -> content in edge band [{edges}]")
        else:
            print(f"ok    {a}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
