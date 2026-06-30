#!/usr/bin/env bash
# Render one course section to course/<section>/out/section.mp4.
#
#   pipeline/build_section.sh <section-folder-name>
#   pipeline/build_section.sh demo-pythagoras
#
# Locked production tunables (override by exporting before calling):
export VOICE="${VOICE:-bf_emma}"          # Kokoro narration voice
export KOKORO_SPEED="${KOKORO_SPEED:-0.88}"
export FADE="${FADE:-0.45}"               # xfade / acrossfade dissolve seconds
export ZOOM_MAX="${ZOOM_MAX:-1.045}"      # gentle Ken Burns push-in (anti-jitter)
export LEAD="${LEAD:-0.4}"                # silence before narration in each beat
export TAIL="${TAIL:-0.7}"               # silence after narration in each beat
export FPS="${FPS:-30}"
export RES="${RES:-1280x720}"
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
SECTION="${1:?usage: build_section.sh <section-folder-name>}"
SECDIR="$ROOT/course/$SECTION"
PY="$HERE/.venv/bin/python"

[ -d "$SECDIR" ] || { echo "no such section: $SECDIR" >&2; exit 1; }
[ -x "$PY" ]     || { echo "venv missing — run setup (see README)" >&2; exit 1; }

echo "== narration transcript =="
"$PY" "$HERE/narrate.py" "$SECDIR"
echo "== lint diagrams (manim footguns) =="
"$PY" "$HERE/lint_diagrams.py" "$SECDIR/diagrams"
echo "== rendering section: $SECTION =="
"$PY" "$HERE/render_section.py" "$SECDIR"
