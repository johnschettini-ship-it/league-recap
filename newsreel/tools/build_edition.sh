#!/bin/bash
# Speak, build, check and render one edition. Run the editions one after the other: they share build/, compositions/ and index.html.
# Usage: tools/build_edition.sh <edition> <output.mp4> <site address>
#   for example: tools/build_edition.sh coozeball_2026_w9 coozeball-gazette-newsreel-2026-w9.mp4 johnschettini-ship-it.github.io/league-recap/coozeball
# Run setup.sh first. KOKORO_DIR, WHISPER_DIR, GAZETTE and FRAMES_DIR have defaults: the setup folder, the gazette above this folder, build/frames.
set -u
E=$1; OUT=$2; SITE=$3
M="${NEWSREEL_MODELS:-$HOME/.cache/newsreel}"            # setup.sh puts the models here
KOKORO_DIR="${KOKORO_DIR:-$M/kokoro}"; WHISPER_DIR="${WHISPER_DIR:-$M/whisper}"
GAZETTE="${GAZETTE:-$(cd "$(dirname "$0")/../.." && pwd)}"; FRAMES_DIR="${FRAMES_DIR:-build/frames}"
export HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1
cd "$(dirname "$0")/.."
python3 tools/narrate.py "$KOKORO_DIR/kokoro-v1.0.onnx" "$KOKORO_DIR/voices-v1.0.bin" "$E" 2>&1 | grep -vE "^\s*$" | tail -1
python3 tools/check_voice.py "$WHISPER_DIR" 2>/dev/null > "build/$E.voice.txt"; echo "narration check exit $? (details: build/$E.voice.txt)"; grep -E "voice:" "build/$E.voice.txt"
python3 tools/build.py --gazette "$GAZETTE" --site "$SITE" || exit 1
python3 tools/check_screen.py | tail -1
npx --yes hyperframes check --json > "build/$E.hf.json" 2>/dev/null; python3 -c "
import json; d=json.load(open('build/$E.hf.json')); print('hyperframes ok', d['ok'], {k:(v['errorCount'],v['warningCount']) for k,v in d.items() if isinstance(v,dict) and 'errorCount' in v})
[print('  ', k, f.get('severity'), f.get('code'), str(f.get('message'))[:200]) for k,v in d.items() if isinstance(v,dict) for f in v.get('findings',[]) if f.get('severity')!='info']"
npx --yes hyperframes render --quality looks -o "renders/full_$E.mp4" --quiet > /dev/null 2>&1 || { echo "render failed"; exit 1; }
tools/shrink.sh "renders/full_$E.mp4" "$OUT" 10 | tail -1          # 10 MB: the site keeps several weeks
python3 tools/check_captions.py "$OUT" | tail -2
python3 tools/frames.py "$FRAMES_DIR/$E" > /dev/null 2>&1; echo "review frames: $FRAMES_DIR/$E"
