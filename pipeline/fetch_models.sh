#!/usr/bin/env bash
# Download the Kokoro neural-TTS model files into pipeline/models/.
# (Gitignored — ~337MB total. Source: github.com/thewh1teagle/kokoro-onnx)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS="$HERE/models"
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
mkdir -p "$MODELS"
[ -f "$MODELS/kokoro-v1.0.onnx" ] || curl -L -o "$MODELS/kokoro-v1.0.onnx" "$BASE/kokoro-v1.0.onnx"
[ -f "$MODELS/voices-v1.0.bin" ]  || curl -L -o "$MODELS/voices-v1.0.bin"  "$BASE/voices-v1.0.bin"
ls -lh "$MODELS"
