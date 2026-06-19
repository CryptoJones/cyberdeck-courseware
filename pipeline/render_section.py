#!/usr/bin/env python3
"""Render one course section to out/section.mp4.

    render_section.py <section-dir>

Pipeline (reuses the approved math-for-ML recipe):
  per beat -> Kokoro bf_emma narration; visual = Cyberdeck slide (Ken Burns push-in
  on a 5K upscale + neon particle overlay) OR an animated Manim diagram clip; mux
  audio under video. Then stitch beats with xfade dissolves + acrossfade audio,
  fading in/out from black at the ends.

Tunables via env (see build_section.sh): VOICE, KOKORO_SPEED, FADE, ZOOM_MAX,
LEAD, TAIL, FPS, RES.
"""
import os
import subprocess
import sys
from pathlib import Path

import soundfile as sf

import tts
import qa_frames
from section_parse import parse

HERE = Path(__file__).resolve().parent
W, H = (int(x) for x in os.environ.get("RES", "1280x720").split("x"))
FPS = int(os.environ.get("FPS", "30"))
VOICE = os.environ.get("VOICE", "bf_emma")
FADE = float(os.environ.get("FADE", "0.45"))
ZOOM_MAX = float(os.environ.get("ZOOM_MAX", "1.045"))
LEAD = float(os.environ.get("LEAD", "0.4"))
TAIL = float(os.environ.get("TAIL", "0.7"))
MIN_BEAT = 2.0
QA_STRICT = os.environ.get("QA_STRICT", "1") != "0"  # fail the build on edge-bleed
PARTICLES = HERE / "assets" / "particles.mp4"


def run(cmd, **kw):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.STDOUT, **kw)


def probe(path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(out.strip())


def ensure_particles():
    if not PARTICLES.exists():
        import particles
        particles.build(PARTICLES, 12.0)


def synth_beat(text, wav: Path) -> float:
    samples, sr = tts.synth(text, VOICE)
    wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav), samples, sr)
    return len(samples) / sr


def render_manim(py: Path, scene: str, media: Path) -> Path:
    media.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(HERE))
    run([sys.executable, "-m", "manim", "-qm", "--fps", str(FPS), "-r", f"{W},{H}",
         "--media_dir", str(media), "-o", scene, str(py), scene], env=env)
    hits = list(media.glob(f"videos/**/{scene}.mp4"))
    if not hits:
        raise RuntimeError(f"manim produced no clip for {scene}")
    return max(hits, key=lambda p: p.stat().st_mtime)


def slide_clip(png: Path, D: float, out: Path):
    frames = max(1, int(round(D * FPS)))
    zinc = (ZOOM_MAX - 1.0) / frames
    fc = (
        f"[0:v]scale=5120:-2,zoompan=z='min(zoom+{zinc:.6f}\\,{ZOOM_MAX})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},trim=duration={D},setsar=1,format=gbrp[bg];"
        f"[1:v]scale={W}:{H},setsar=1,format=gbrp[pa];"
        f"[bg][pa]blend=all_mode=screen,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(png),
         "-stream_loop", "-1", "-i", str(PARTICLES),
         "-filter_complex", fc, "-map", "[v]", "-t", f"{D}",
         "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         str(out)])


def diagram_clip(raw: Path, D: float, out: Path):
    cd = probe(raw)
    pad = max(0.0, D - cd)
    fc = (
        f"[0:v]scale={W}:{H},setsar=1,fps={FPS},"
        f"tpad=stop_mode=clone:stop_duration={pad},format=gbrp[base];"
        f"[1:v]scale={W}:{H},setsar=1,format=gbrp[pa];"
        f"[base][pa]blend=all_mode=screen,trim=duration={D},format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-i", str(raw),
         "-stream_loop", "-1", "-i", str(PARTICLES),
         "-filter_complex", fc, "-map", "[v]", "-t", f"{D}",
         "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         str(out)])


def beat_audio(wav: Path, D: float, out: Path):
    lead_ms = int(LEAD * 1000)
    run(["ffmpeg", "-y", "-i", str(wav),
         "-af", f"adelay={lead_ms}:all=1,apad",
         "-t", f"{D}", "-ar", "48000", "-ac", "2", str(out)])


def mux(video: Path, audio: Path, out: Path):
    run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def stitch(clips, out: Path):
    durs = [probe(c) for c in clips]
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    if n == 1:
        total = durs[0]
        fc = (f"[0:v]fade=t=in:st=0:d={FADE},"
              f"fade=t=out:st={total-FADE}:d={FADE}[v];"
              f"[0:a]afade=t=in:st=0:d={FADE},"
              f"afade=t=out:st={total-FADE}:d={FADE}[a]")
    else:
        parts, vlab, alab = [], "[0:v]", "[0:a]"
        offset = durs[0] - FADE
        for i in range(1, n):
            nv, na = f"[v{i}]", f"[a{i}]"
            parts.append(f"{vlab}[{i}:v]xfade=transition=fade:duration={FADE}:"
                         f"offset={offset:.3f}{nv}")
            parts.append(f"{alab}[{i}:a]acrossfade=d={FADE}{na}")
            vlab, alab = nv, na
            offset += durs[i] - FADE
        total = sum(durs) - FADE * (n - 1)
        parts.append(f"{vlab}fade=t=in:st=0:d={FADE},"
                     f"fade=t=out:st={total-FADE:.3f}:d={FADE}[v]")
        parts.append(f"{alab}afade=t=in:st=0:d={FADE},"
                     f"afade=t=out:st={total-FADE:.3f}:d={FADE}[a]")
        fc = ";".join(parts)
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sec = Path(sys.argv[1]).resolve()
    beats = parse(sec / "script.md")
    out = sec / "out"
    (out / "clips").mkdir(parents=True, exist_ok=True)
    (out / "audio").mkdir(parents=True, exist_ok=True)
    ensure_particles()

    av_clips = []
    qa_violations = []
    for i, b in enumerate(beats, 1):
        print(f"  beat {i}/{len(beats)}: {b.visual}")
        wav = out / "audio" / f"beat{i}.wav"
        d_aud = synth_beat(b.narration, wav) if b.narration.strip() else 0.0
        D = max(MIN_BEAT, LEAD + d_aud + TAIL)

        vid = out / "clips" / f"beat{i}_v.mp4"
        qa_src = None  # clean intermediate (no particle overlay) to QA-scan
        if b.kind == "slide":
            import render_slides
            png = out / "clips" / f"beat{i}.png"
            render_slides.render(sec / b.target, png, W, H)
            qa_src = png
            slide_clip(png, D, vid)
        elif b.kind == "manim":
            py_rel, scene = b.target.rsplit(":", 1)
            raw = render_manim(sec / py_rel, scene, out / "manim")
            qa_src = raw
            diagram_clip(raw, D, vid)
        elif b.kind == "clip":
            qa_src = sec / b.target
            diagram_clip(qa_src, D, vid)
        else:
            raise SystemExit(f"unknown visual kind: {b.visual}")

        # No-bleed gate: every frame of the clean source must stay out of the edge band.
        hits = qa_frames.check(qa_src)
        if hits:
            edges = ", ".join(f"{e}:{c}" for e, c in sorted(hits.items()))
            print(f"    QA CLIP  beat {i} ({b.visual}) -> edge band [{edges}]")
            qa_violations.append((i, b.visual, edges))

        apad = out / "audio" / f"beat{i}_pad.wav"
        beat_audio(wav if d_aud else _silence(out, D), D, apad)
        av = out / "clips" / f"beat{i}_av.mp4"
        mux(vid, apad, av)
        av_clips.append(av)

    if qa_violations:
        print(f"\n  QA: {len(qa_violations)} beat(s) have content crowding the frame edge:")
        for i, vis, edges in qa_violations:
            print(f"    - beat {i}: {vis}  [{edges}]")
        if QA_STRICT:
            sys.exit("  QA FAILED — fix the bleed (slides: stay inside the padding; "
                     "diagrams: self.safe_fit). Re-run, or QA_STRICT=0 to override.")
        print("  QA_STRICT=0 — continuing despite bleed.")

    final = out / "section.mp4"
    print(f"  stitching {len(av_clips)} beats -> {final}")
    stitch(av_clips, final)
    print(f"DONE  {final}  ({probe(final):.1f}s)")


def _silence(out: Path, D: float) -> Path:
    s = out / "audio" / "silence.wav"
    if not s.exists():
        run(["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"anullsrc=r=24000:cl=mono", "-t", "1", str(s)])
    return s


if __name__ == "__main__":
    main()
