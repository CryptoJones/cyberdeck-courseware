#!/usr/bin/env python3
"""Kokoro neural-TTS one-shot synth.

    tts.py <voice> <out.wav> "text to speak..."
    tts.py <voice> <out.wav> --file script.txt

Voice + speed defaults match the locked narration choice (bf_emma @ 0.88).
Speed override via env KOKORO_SPEED. Long text is split on sentence boundaries
to stay under the model's token limit and concatenated with short gaps.
"""
import os
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
MODEL = HERE / "models" / "kokoro-v1.0.onnx"
VOICES = HERE / "models" / "voices-v1.0.bin"

SPEED = float(os.environ.get("KOKORO_SPEED", "0.88"))
# bf_emma is British English; use the matching phoneme language.
LANG = os.environ.get("KOKORO_LANG", "en-gb")
GAP = 0.28  # seconds of silence between sentences


def split_sentences(text: str):
    text = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def synth(text: str, voice: str):
    kokoro = Kokoro(str(MODEL), str(VOICES))
    chunks = []
    sr = 24000
    for sent in split_sentences(text):
        samples, sr = kokoro.create(sent, voice=voice, speed=SPEED, lang=LANG)
        chunks.append(samples)
        chunks.append(np.zeros(int(sr * GAP), dtype=samples.dtype))
    if not chunks:
        return np.zeros(1, dtype="float32"), sr
    return np.concatenate(chunks), sr


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    voice, out = sys.argv[1], sys.argv[2]
    if sys.argv[3] == "--file":
        text = Path(sys.argv[4]).read_text(encoding="utf-8")
    else:
        text = " ".join(sys.argv[3:])
    samples, sr = synth(text, voice)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, samples, sr)
    print(f"{out}  ({len(samples)/sr:.2f}s @ {sr}Hz, voice={voice}, speed={SPEED})")


if __name__ == "__main__":
    main()
