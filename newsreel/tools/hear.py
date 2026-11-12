#!/usr/bin/env python3
"""Speak test lines with the voice recipe in use, and print what a speech recognizer hears.

Use it to find a clear spoken form of a name or a line before it goes into pronunciations.json or into a "tts" form.

Usage: python3 tools/hear.py <kokoro.onnx> <voices.bin> <whisper_dir> "line one" "line two" ...
The lines are spoken as written. The tool prints the result for the clean voice and for the old-time voice.
"""
import json, pathlib, sys, tempfile

import numpy as np
import sherpa_onnx

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from models import whisper  # noqa: E402
from kokoro_onnx import Kokoro

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import voice_lab

ROOT = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) < 5:
    sys.exit(__doc__)
model, voices, wdir, lines = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
recipe = json.loads((ROOT / "voice.json").read_text())
kokoro = Kokoro(model, voices)
style = voice_lab.style_of(kokoro, recipe)
_enc, _dec, _tok = whisper(wdir)
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=_enc, decoder=_dec, tokens=_tok, num_threads=4, language="en", task="transcribe")


def hear(x, rate):
    pad = np.zeros(int(0.4 * rate), dtype=np.float32)
    stream = rec.create_stream()
    stream.accept_waveform(rate, np.concatenate([pad, np.asarray(x, dtype=np.float32).reshape(-1), pad]))
    rec.decode_stream(stream)
    return stream.result.text.strip()


with tempfile.TemporaryDirectory() as tmp:
    for i, text in enumerate(lines):
        x, rate = kokoro.create(text, voice=style, speed=float(recipe.get("speed", 1.0)), lang="en-us")
        clean, old = pathlib.Path(tmp) / f"{i}_clean.wav", pathlib.Path(tmp) / f"{i}_old.wav"
        voice_lab.write_wav(clean, np.asarray(x, dtype=np.float32).reshape(-1), rate)
        voice_lab.treat(clean, old, recipe)
        y, rate2 = voice_lab.read_wav(old)
        print(f"said : {text}\n  clean: {hear(x, rate)}\n  old  : {hear(y, rate2)}   ({len(x) / rate:.1f} s)")
