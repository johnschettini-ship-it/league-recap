"""Speak the newsreel script, fit the pauses to the length goal, and apply the old sound of the voice recipe.

Usage: python3 tools/narrate.py <kokoro.onnx> <voices.bin> <edition>        for example: ... 2026_w9, or coozeball_2026_w9
Reads:  scripts/<edition>.script.json, pronunciations.json, voice.json (one recipe of tools/voice_lab.py)
Writes: assets/audio/narration.mp3 (treated), build/narration_clean.wav, build/narration_old.wav, build/timeline.json

Fails with a non-zero exit and writes nothing when a sentence produces no audio,
or when the script is too long for the goal even with the shortest pauses.
"""
import json, math, pathlib, re, subprocess, sys, wave

import numpy as np
from kokoro_onnx import Kokoro

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import voice_lab

ROOT = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) != 4:
    sys.exit(__doc__)
model, voices, edition = sys.argv[1], sys.argv[2], sys.argv[3]
script = json.loads((ROOT / "scripts" / f"{edition}.script.json").read_text())
missing = [k for k in ("league", "season", "week", "beats") if k not in script]
if missing:
    sys.exit(f"scripts/{edition}.script.json has no {', '.join(missing)}. The file needs league, season, week and beats. Stopped; no file was written.")
if edition.rsplit("_", 2)[-2:] != [str(script['season']), f"w{script['week']}"]:
    sys.exit(f"scripts/{edition}.script.json is for season {script['season']}, week {script['week']}. Stopped.")
SAY = {k: v for k, v in json.loads((ROOT / "pronunciations.json").read_text()).items() if not k.startswith("_")}

# The voice is one recipe of the voice lab. To change the voice, put a different recipe in voice.json.
VOICE = json.loads((ROOT / "voice.json").read_text())
if voice_lab.check_recipe(VOICE):
    sys.exit("voice.json: " + "; ".join(voice_lab.check_recipe(VOICE)))
LANG = "en-us"
TARGET, HARD_LIMIT = 89.4, 90.0                 # seconds. The goal is a 90 second video.
LEAD_IN, TAIL = 2.7, 3.0                        # the film leader runs before the first word; the end card holds after the last word
SENTENCE_GAP, BEAT_GAP = 0.35, 0.85             # nominal pauses, in seconds
MIN_SCALE, MAX_SCALE = 0.65, 1.30               # the pauses can shrink or stretch by this factor


def spoken(cap):
    """The text for the speech engine: team names as they are said, and symbols in words."""
    t = cap
    held = sorted(SAY, key=len, reverse=True)
    for i, name in enumerate(held):                           # hold each name of the table, so that no other rule changes it
        t = t.replace(name, f"\x00{i}\x00")
    t = re.sub(r"(?<=[A-Za-z])-(?=[a-z])", " ", t)            # "Last-place" is clearer as "Last place"
    t = re.sub(r"\x00(\d+)\x00", lambda m: SAY[held[int(m.group(1))]], t)
    t = re.sub(r"\b(Jr|Sr)\.(\s*$)?", lambda m: {"Jr": "Junior", "Sr": "Senior"}[m.group(1)] + ("." if m.group(2) is not None else ""), t)
    t = re.sub(r"(?<=[a-z])(?<!Week) III\b", " the Third", t)             # the engine says "Roman 3" for III
    t = re.sub(r"(?<=[a-z]) II\b", " the Second", t)
    t = t.replace("\u2212", "-")                                # a typographic minus sign
    t = re.sub(r"(?<![\w.])-(?=\d)", "minus ", t)               # a negative score: -0.3 is said "minus 0.3"
    t = re.sub(r"#\s*(\d+)", r"number \1", t)
    t = re.sub(r"\$(\d+)", r"\1 dollars", t)
    t = re.sub(r"\b(\d+)-(\d+)-(\d+)\b", r"\1, \2 and \3", t)      # a record with ties: 3-5-1 is said "3, 5 and 1"
    t = re.sub(r"\b(\d+)-(\d+)\b", r"\1 and \2", t)      # a record: 6-2 is said "6 and 2"
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(r"(?<![\d.])0\.0(?!\d)", "zero point zero", t)   # only the score 0.0, not a part of a number such as 100.04
    t = re.sub(r"^(\w+):\s", r"\1! ", t)                     # a one-word label ("Boom:") is clearer as "Boom!"
    return t


kokoro = Kokoro(model, voices)
names = [VOICE["voices"]] if isinstance(VOICE["voices"], str) else list(VOICE["voices"])
missing = [n for n in names if n not in kokoro.get_voices()]
if missing:
    sys.exit(f"voice.json: these voices are not in {voices}: {', '.join(missing)}")
STYLE = voice_lab.style_of(kokoro, VOICE)      # one voice, or a blend of several

# 1. Speak every sentence.
rate, clips, texts = None, [], []
for beat in script["beats"]:
    row, trow = [], []
    for s in beat["sentences"]:
        tts = spoken(s.get("tts") or s["cap"])     # "tts" is the caption with pause marks, for a line that the voice runs together
        x, sr = kokoro.create(tts, voice=STYLE, speed=float(VOICE.get("speed", 1.0)), lang=LANG)
        rate = rate or sr
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        if sr != rate or len(x) / rate < 0.2 or float(np.abs(x).max()) < 0.01:
            sys.exit(f"No usable audio for sentence: {tts!r}")
        row.append(x); trow.append(tts)
    clips.append(row); texts.append(trow)

# 2. Fit the pauses.
speech = sum(len(c) for r in clips for c in r) / rate
n_words = sum(len(t.split()) for r in texts for t in r)
nominal = SENTENCE_GAP * sum(len(r) - 1 for r in clips) + BEAT_GAP * (len(clips) - 1)
scale = min(MAX_SCALE, max(MIN_SCALE, (TARGET - LEAD_IN - TAIL - speech) / nominal))
total = LEAD_IN + speech + scale * nominal + TAIL
if total > HARD_LIMIT:
    cut = math.ceil((total - TARGET) / (speech / n_words))
    sys.exit(f"Too long: {total:.1f} s with the shortest pauses; the limit is {HARD_LIMIT:.0f} s. Cut about {cut} spoken words from script.json.")
sgap, bgap = SENTENCE_GAP * scale, BEAT_GAP * scale
silence = lambda sec: np.zeros(int(round(rate * sec)), dtype=np.float32)

# 3. Lay out the audio and record the time of each sentence.
chunks, t, beats = [silence(LEAD_IN)], LEAD_IN, []
for bi, beat in enumerate(script["beats"]):
    entry = {"id": beat["id"], "sentences": []}
    for si, s in enumerate(beat["sentences"]):
        dur = len(clips[bi][si]) / rate
        entry["sentences"].append({"cap": s["cap"], "tts": texts[bi][si], "start": round(t, 3), "end": round(t + dur, 3)})
        chunks.append(clips[bi][si]); t += dur
        last = si == len(beat["sentences"]) - 1
        if not (last and bi == len(clips) - 1):
            gap = bgap if last else sgap
            chunks.append(silence(gap)); t += gap
    beats.append(entry)
chunks.append(silence(TAIL))
audio = np.concatenate(chunks)
t = len(audio) / rate
for i, b in enumerate(beats):          # a segment is on screen from just before its first word until the next segment starts
    b["start"] = 0.0 if i == 0 else round(b["sentences"][0]["start"] - 0.35, 3)
for i, b in enumerate(beats):
    b["end"] = round(t, 3) if i == len(beats) - 1 else beats[i + 1]["start"]

(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "assets" / "audio").mkdir(parents=True, exist_ok=True)
clean = ROOT / "build" / "narration_clean.wav"
with wave.open(str(clean), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
old = ROOT / "build" / "narration_old.wav"
voice_lab.treat(clean, old, VOICE)             # the pitch change keeps the length, so the sentence times stay correct
# The project keeps an MP3: a 90 second WAV is about 8 MB, the MP3 about 1.4 MB.
# Loudness: about -16 LUFS, which is the usual level for a video on a phone.
subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(old), "-af", "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100",
                "-c:a", "libmp3lame", "-b:a", "128k", "-ac", "1",
                str(ROOT / "assets" / "audio" / "narration.mp3")], check=True)
timeline = {"edition": edition, "duration": round(t, 3), "voice": VOICE["id"], "voice_recipe": VOICE, "lead_in": LEAD_IN, "beats": beats,
            "league": script["league"], "season": script["season"], "week": script["week"]}
(ROOT / "build" / "timeline.json").write_text(json.dumps(timeline, indent=1))
print(f"duration {t:.1f}s (target {TARGET}), {n_words} spoken words at {n_words / speech * 60:.0f} per minute, "
      f"{sum(len(r) for r in clips)} sentences, voice {VOICE['id']}, pauses {sgap:.2f}s / {bgap:.2f}s (scale {scale:.2f})")
