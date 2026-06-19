#!/usr/bin/env python3
"""Generate the ambient neon-particle overlay loop (Cyberdeck).

    particles.py [out.mp4] [seconds]

Black background with slowly drifting cyan/green/mint dots + soft glow. Meant to
be composited over slides/diagrams with ffmpeg `blend=all_mode=screen` (black
reads as transparent under screen blend). Loops seamlessly: each dot's position
is periodic over the clip length.
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
W, H, FPS = 1280, 720, 30
N = 90
NEON = [(39, 212, 255), (85, 255, 153), (159, 255, 224)]  # cyan, green, mint


def build(out: Path, seconds: float = 10.0):
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)  # fixed seed -> deterministic loop
    px = rng.uniform(0, W, N)
    py = rng.uniform(0, H, N)
    # integer cycle counts so motion is periodic over the loop (seamless)
    cyc_x = rng.integers(1, 3, N)
    cyc_y = rng.integers(1, 3, N)
    amp_x = rng.uniform(8, 40, N)
    amp_y = rng.uniform(8, 40, N)
    phase = rng.uniform(0, 2 * math.pi, N)
    radius = rng.uniform(1.5, 3.5, N)
    colors = [NEON[i % len(NEON)] for i in range(N)]
    alpha = rng.uniform(0.25, 0.8, N)

    frames = int(seconds * FPS)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for f in range(frames):
        t = f / frames  # 0..1
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(N):
            x = px[i] + amp_x[i] * math.sin(2 * math.pi * cyc_x[i] * t + phase[i])
            y = py[i] + amp_y[i] * math.cos(2 * math.pi * cyc_y[i] * t + phase[i])
            c = tuple(int(v * alpha[i]) for v in colors[i])
            r = radius[i]
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        img = img.filter(ImageFilter.GaussianBlur(1.4))
        proc.stdin.write(np.asarray(img, dtype="uint8").tobytes())
    proc.stdin.close()
    proc.wait()
    return out


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "assets" / "particles.mp4"
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    print(build(out, seconds))


if __name__ == "__main__":
    main()
