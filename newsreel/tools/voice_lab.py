"""Voice lab: make and test announcer voice styles from recipes.

A recipe is one JSON object:
  id         short name, letters, digits and hyphens
  label      a title for the sample card, up to 22 characters
  note       one short line for the sample card, up to 34 characters
  voices     the base voice, or a blend: {"am_eric": 0.65, "bm_fable": 0.35}. The weights are normalized.
  speed      0.8 to 1.4
  semitones  how far to raise (or lower) the pitch after synthesis, -4 to 7
  formant    "preserved" (same vocal tract) or "shifted" (a smaller or larger speaker)
  chain      an ffmpeg audio filter chain for the "old sound". Only the filters in ALLOWED can be used.
  hiss_db    level of the hiss, -60 (none audible) to -36
  crackle_db level of the crackle, -60 to -20
  crackle_rate  pops in each second, 1 to 40. The default is 7.

Usage:
  python3 voice_lab.py voices <kokoro.onnx> <voices.bin>
  python3 voice_lab.py run <kokoro.onnx> <voices.bin> <whisper_dir> <recipes.json> <out_dir>
  python3 voice_lab.py reel <out_dir> <out.mp4> <id,id,...> [first_number | tag,tag,...]

"run" writes <out_dir>/<id>.wav and <out_dir>/results.json. For each recipe it reports the length, the pitch,
and how many words of the test lines a speech recognizer heard correctly.
The recipes must describe original voices. They must not copy the voice of a real person or of a film.
"""
import json, pathlib, re, subprocess, sys, wave

import numpy as np

TEXT = ["Extra, extra, ladies and gentlemen of the Beer Den!",
        "Week 8 brings mayhem, and one mislaid quarterback.",
        "Stop the presses! Top score topples leader!"]
ALLOWED = {"highpass", "lowpass", "bandpass", "equalizer", "treble", "bass", "acompressor", "alimiter", "asoftclip", "compand",
           "volume", "aecho", "tremolo", "acrusher", "aphaser", "chorus", "flanger", "agate", "dynaudnorm", "aresample"}
DEFAULT_CHAIN = ("highpass=f=250,lowpass=f=3600,equalizer=f=1700:t=q:w=1.0:g=6,"
                 "acompressor=threshold=-22dB:ratio=5:attack=4:release=80:makeup=4,asoftclip=type=tanh")


def check_recipe(r):
    """Return a list of problems. An empty list means that the recipe is usable."""
    bad = []
    if not re.fullmatch(r"[a-z0-9-]{2,40}", str(r.get("id", ""))):
        bad.append("id must be 2-40 characters: lower-case letters, digits, hyphens")
    v = r.get("voices")
    if isinstance(v, str):
        v = {v: 1.0}
    if not isinstance(v, dict) or not v or any(not isinstance(w, (int, float)) or w <= 0 for w in v.values()):
        bad.append("voices must be a voice name or a map of voice name to positive weight")
    if not 0.8 <= float(r.get("speed", 1.0)) <= 1.4:
        bad.append("speed must be 0.8 to 1.4")
    if not -4 <= float(r.get("semitones", 0)) <= 7:
        bad.append("semitones must be -4 to 7")
    if not -60 <= float(r.get("hiss_db", -44)) <= -30 or not -60 <= float(r.get("crackle_db", -31)) <= -20:
        bad.append("hiss_db must be -60 to -30 and crackle_db must be -60 to -20")
    if not 1 <= float(r.get("crackle_rate", 7)) <= 40:
        bad.append("crackle_rate must be 1 to 40")
    if r.get("formant", "preserved") not in ("preserved", "shifted"):
        bad.append('formant must be "preserved" or "shifted"')
    for part in str(r.get("chain") or DEFAULT_CHAIN).split(","):
        name = part.split("=")[0].strip()
        if name not in ALLOWED:
            bad.append(f"filter {name!r} is not in the allowed list")
    return bad


def noise_bed(n, rate, hiss_db, crackle_db, crackle_rate=7.0, seed=1938):
    rng = np.random.default_rng(seed)
    hiss = np.convolve(rng.standard_normal(n), np.ones(4) / 4, mode="same")
    hiss *= 10 ** (hiss_db / 20) / (np.sqrt(np.mean(hiss ** 2)) + 1e-9)
    crackle = np.zeros(n)
    count = int(n / rate * crackle_rate)
    pos = rng.integers(0, max(1, n - 200), count)
    amp = rng.uniform(0.2, 1.0, count) * rng.choice([-1, 1], count)
    decay = np.exp(-np.arange(120) / 14.0)
    for p, a in zip(pos, amp):
        crackle[p:p + 120] += a * decay[:max(0, min(120, n - p))]
    crackle *= 10 ** (crackle_db / 20) / (np.abs(crackle).max() + 1e-9)
    return (hiss + crackle).astype(np.float32)


def read_wav(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768, w.getframerate()


def write_wav(path, x, rate):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def style_of(kokoro, recipe):
    """The voice of a recipe: a name, or a weighted blend of the style vectors of several voices."""
    v = recipe["voices"]
    if isinstance(v, str):
        return v
    if len(v) == 1:
        return next(iter(v))
    total = sum(v.values())
    return sum(kokoro.get_voice_style(name) * (w / total) for name, w in v.items())


def treat(clean_path, out_path, recipe):
    """Apply the pitch change and the old-sound chain of a recipe to a clean voice file. The length does not change."""
    chain = str(recipe.get("chain") or DEFAULT_CHAIN)
    st = float(recipe.get("semitones", 0))
    if st:
        chain = f"rubberband=pitch={2 ** (st / 12):.5f}:formant={recipe.get('formant', 'preserved')}:pitchq=quality," + chain
    tmp = str(out_path) + ".tmp.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(clean_path), "-af", chain + ",aresample=44100", "-ac", "1", tmp], check=True)
    x, rate = read_wav(tmp)
    y = x + noise_bed(len(x), rate, float(recipe.get("hiss_db", -44)), float(recipe.get("crackle_db", -31)), float(recipe.get("crackle_rate", 7)))
    y *= 0.89 / max(1e-9, float(np.abs(y).max()))
    write_wav(out_path, y, rate)
    pathlib.Path(tmp).unlink()


def pitch_of(x, sr):
    n, hop, lo, hi = int(0.04 * sr), int(0.01 * sr), int(sr / 420), int(sr / 65)
    gate, out = 0.1 * np.sqrt(np.mean(x ** 2)), []
    for i in range(0, len(x) - n, hop):
        fr = x[i:i + n] - np.mean(x[i:i + n])
        if np.sqrt(np.mean(fr ** 2)) < gate:
            continue
        ac = np.correlate(fr, fr, "full")[n - 1:]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.5:
            out.append(sr / lag)
    return float(np.median(out)) if out else float("nan")


def words(text):
    t = text.lower().replace("bearden", "beer den").replace("beirden", "beer den").replace("8", " eight ")
    return re.sub(r"[^a-z ]", "", t).split()


def edits(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i in range(1, len(ref) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(hyp) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(hyp)]


def run(model, voices_bin, whisper_dir, recipes_path, out_dir):
    import sherpa_onnx
    from kokoro_onnx import Kokoro
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    recipes = json.loads(pathlib.Path(recipes_path).read_text())
    kokoro = Kokoro(model, voices_bin)
    known = set(kokoro.get_voices())
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{whisper_dir}/small.en-encoder.onnx", decoder=f"{whisper_dir}/small.en-decoder.onnx",
        tokens=f"{whisper_dir}/small.en-tokens.txt", num_threads=4, language="en", task="transcribe")
    ref = [w for t in TEXT for w in words(t)]
    results = []
    for r in recipes:
        problems = check_recipe(r)
        v = r.get("voices")
        names = [v] if isinstance(v, str) else list(v or {})
        problems += [f"unknown voice {n!r}" for n in names if n not in known]
        if problems:
            results.append({"id": r.get("id"), "ok": False, "problems": problems})
            print(f"{r.get('id')}: NOT RUN: {'; '.join(problems)}", flush=True)
            continue
        try:
            parts = []
            for t in TEXT:
                x, sr = kokoro.create(t, voice=style_of(kokoro, r), speed=float(r.get("speed", 1.0)), lang="en-us")
                parts += [np.asarray(x, dtype=np.float32).reshape(-1), np.zeros(int(0.22 * sr), dtype=np.float32)]
            clean = out / f"{r['id']}.clean.wav"
            write_wav(clean, np.concatenate(parts), sr)
            treat(clean, out / f"{r['id']}.wav", r)
            clean.unlink()
            y, sr2 = read_wav(out / f"{r['id']}.wav")
            stream = rec.create_stream(); stream.accept_waveform(sr2, y); rec.decode_stream(stream)
            heard = stream.result.text.strip()
            wrong = edits(ref, words(heard))
            pitch = pitch_of(y, sr2)                # NaN when the pitch cannot be measured, for example with a strong warble
            row = {"id": r["id"], "ok": True, "label": r.get("label", r["id"]), "note": r.get("note", ""), "seconds": round(len(y) / sr2, 1),
                   "pitch_hz": round(pitch) if pitch == pitch else None, "words_right_pct": round(100 * (1 - wrong / len(ref))), "heard": heard, "recipe": r}
        except Exception as e:                      # a bad filter chain or blend: report it, and continue with the next recipe
            row = {"id": r.get("id"), "ok": False, "problems": [f"{type(e).__name__}: {str(e)[:200]}"]}
        results.append(row)
        print({k: row[k] for k in row if k not in ("recipe", "heard", "label", "note")}, flush=True)
        (out / "results.json").write_text(json.dumps(results, indent=1))
    (out / "results.json").write_text(json.dumps(results, indent=1))
    good = [x for x in results if x.get("ok")]
    print(f"DONE: {len(good)} of {len(results)} recipes made a voice; {sum(x['words_right_pct'] >= 95 for x in good)} are clear (95 percent or more)")


def reel(out_dir, out_mp4, ids, first=1, tags=None):
    """One labelled video with the chosen samples, at equal loudness, in the colours of the gazette."""
    out = pathlib.Path(out_dir)
    rows = {r["id"]: r for r in json.loads((out / "results.json").read_text()) if r.get("ok")}
    font = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Serif:bold"], capture_output=True, text=True, check=True).stdout
    safe = lambda s: re.sub(r"[^A-Za-z0-9 .,+%-]", "", str(s))
    segs = []
    for n, rid in enumerate(ids):
        r = rows[rid]
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out / f"{rid}.wav")],
                                   capture_output=True, text=True, check=True).stdout) + 0.5
        clear = "clear" if r["words_right_pct"] >= 95 else f"{r['words_right_pct']} percent clear"
        vf = (f"drawbox=x=0:y=0:w=720:h=12:color=0x9a3412:t=fill,"
              f"drawtext=fontfile={font}:text='STYLE {safe(tags[n]) if tags else first + n}':fontcolor=0x9a3412:fontsize=64:x=(w-text_w)/2:y=230,"
              f"drawtext=fontfile={font}:text='{safe(r['label']).upper()[:22]}':fontcolor=0x1c1b19:fontsize=50:x=(w-text_w)/2:y=350,"
              f"drawtext=fontfile={font}:text='{safe(r['note'])[:34]}':fontcolor=0x57524a:fontsize=34:x=(w-text_w)/2:y=450,"
              f"drawtext=fontfile={font}:text='{str(r['pitch_hz']) + ' Hz, ' if r['pitch_hz'] else ''}{clear}':fontcolor=0x57524a:fontsize=34:x=(w-text_w)/2:y=520")
        seg = out / f"seg_{rid}.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0xfffefb:s=720x900:r=30", "-i", str(out / f"{rid}.wav"),
                        "-af", "apad=pad_dur=0.5,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=44100", "-vf", vf, "-t", f"{dur:.2f}",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(seg)], check=True)
        segs.append(seg)
    lst = out / "reel_list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out_mp4)], check=True)
    for s in segs:
        s.unlink()
    lst.unlink()
    print(f"wrote {out_mp4} with {len(ids)} styles: " + (", ".join(tags) if tags else f"numbers {first} to {first + len(ids) - 1}"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "voices":
        from kokoro_onnx import Kokoro
        print(" ".join(sorted(Kokoro(sys.argv[2], sys.argv[3]).get_voices())))
    elif cmd == "run":
        run(*sys.argv[2:7])
    elif cmd == "reel":
        extra = sys.argv[5] if len(sys.argv) > 5 else "1"
        if extra.isdigit():
            reel(sys.argv[2], sys.argv[3], sys.argv[4].split(","), int(extra))
        else:
            reel(sys.argv[2], sys.argv[3], sys.argv[4].split(","), tags=extra.split(","))
    else:
        sys.exit(__doc__)
