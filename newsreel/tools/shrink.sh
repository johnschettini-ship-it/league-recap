#!/usr/bin/env bash
# Make a copy of a render that is small enough for a group chat (below 16 MB).
# The film grain makes the full-quality render large, so this step sets a fixed bit rate in two passes.
# Usage: tools/shrink.sh <in.mp4> <out.mp4> [megabytes]
set -euo pipefail
IN="${1:?input}"; OUT="${2:?output}"; MB="${3:-15.3}"
SIZE_MB=$(python3 -c "import os; print(os.path.getsize('$IN') / 1048576)")
if python3 -c "import sys; sys.exit(0 if $SIZE_MB <= $MB else 1)"; then
  # The render is small enough already: copy it and put the index at the start of the file.
  ffmpeg -nostdin -y -loglevel error -i "$IN" -c copy -movflags +faststart "$OUT"
  echo "wrote $OUT: $(du -h "$OUT" | cut -f1), a copy of the render"
  exit 0
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
VIDEO_K=$(python3 -c "print(int($MB * 8192 / $DUR - 128 - 12))")      # total bit rate, less the audio and the container
LOG=$(mktemp -d)
ffmpeg -nostdin -y -loglevel error -i "$IN" -c:v libx264 -preset slow -b:v "${VIDEO_K}k" -pass 1 -passlogfile "$LOG/p" -an -f mp4 /dev/null
ffmpeg -nostdin -y -loglevel error -i "$IN" -c:v libx264 -preset slow -b:v "${VIDEO_K}k" -pass 2 -passlogfile "$LOG/p" -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart "$OUT"
rm -rf "$LOG"
echo "wrote $OUT: $(du -h "$OUT" | cut -f1), video ${VIDEO_K} kbit/s"
