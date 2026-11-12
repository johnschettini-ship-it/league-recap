#!/bin/bash
# One-time setup of a session: Python packages and the model files (about 530 MB of downloads, 1 to 2 minutes).
# The files go to ~/.cache/newsreel, outside the repository. A second run skips what is already there.
set -euo pipefail
M="${NEWSREEL_MODELS:-$HOME/.cache/newsreel}"
mkdir -p "$M/kokoro" "$M/whisper"
pip install -q kokoro-onnx sherpa-onnx numpy
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$M/kokoro/$f" ] || curl -fsSL -o "$M/kokoro/$f" "$K/$f"
done
if ! ls "$M/whisper"/*-encoder*.onnx >/dev/null 2>&1; then
  # the speech checker: Whisper base.en; only its int8 files are kept (about 160 MB)
  curl -fsSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2 \
    | tar xjf - -C "$M/whisper" --strip-components=1 --wildcards '*int8.onnx' '*tokens.txt'
fi
command -v ffmpeg >/dev/null || { echo "ffmpeg is missing: install it (apt-get install -y ffmpeg)"; exit 1; }
command -v node >/dev/null || { echo "node is missing: install Node.js 20 or later"; exit 1; }
echo "newsreel setup done: $M"
ls -la "$M/kokoro" "$M/whisper"
