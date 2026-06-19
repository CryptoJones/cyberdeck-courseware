#!/usr/bin/env bash
# Batch-render every authored section (any course/<slug>/ that has a script.md).
# Sequential (manim+ffmpeg are CPU-bound); logs to course/render.log; skips
# already-rendered sections unless FORCE=1; continues past failures.
#
#   pipeline/render_all.sh
#   FORCE=1 pipeline/render_all.sh        # re-render even if out/section.mp4 exists
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
LOG="$ROOT/course/render.log"
: > "$LOG"
ok=0; fail=0; skip=0
for slug in $(tail -n +2 "$ROOT/course/manifest.tsv" | cut -f1); do
  dir="$ROOT/course/$slug"
  [ -f "$dir/script.md" ] || { echo "SKIP (no script) $slug" | tee -a "$LOG"; continue; }
  if [ -z "${FORCE:-}" ] && [ -f "$dir/out/section.mp4" ]; then
    echo "SKIP (done) $slug" | tee -a "$LOG"; skip=$((skip+1)); continue
  fi
  echo "=== RENDER $slug @ $(date +%H:%M:%S) ===" | tee -a "$LOG"
  if "$HERE/build_section.sh" "$slug" >>"$LOG" 2>&1; then
    echo "OK   $slug" | tee -a "$LOG"; ok=$((ok+1))
  else
    echo "FAIL $slug (see $LOG)" | tee -a "$LOG"; fail=$((fail+1))
  fi
done
echo "=== DONE: $ok rendered, $skip skipped, $fail failed ===" | tee -a "$LOG"
