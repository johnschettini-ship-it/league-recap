"""Check the narration with a speech recognizer.

The build machine has no audio output. This check transcribes each spoken sentence with Whisper
and compares it with the text that the speech engine received. It does this two times:
for the clean voice, and for the voice after the old-time treatment.
A difference means "a person must listen to this sentence". The recognizer can also be wrong,
most of all on team names.

Usage: python3 tools/check_voice.py <whisper_dir>
  <whisper_dir> has small.en-encoder.onnx, small.en-decoder.onnx, small.en-tokens.txt
                (sherpa-onnx-whisper-small.en from the sherpa-onnx "asr-models" release)
Exit code: 0 when every sentence matches in both files, 1 when one or more sentences differ.
"""
import json, pathlib, re, sys, wave

import numpy as np
import sherpa_onnx

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from models import whisper  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
wdir = sys.argv[1]
timeline = json.loads((ROOT / "build" / "timeline.json").read_text())
sentences = [s for b in timeline["beats"] for s in b["sentences"]]

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "x x twenty thirty forty fifty sixty seventy eighty ninety".split()
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
# Words that sound the same. The recognizer cannot tell them apart, so they count as equal.
SAME = {"won": "one", "two": "to", "too": "to", "four": "for", "their": "there", "ate": "eight", "night": "knight",
        "hayes": "haze", "bearden": "beer den", "beirden": "beer den", "birden": "beer den", "duke": "dook", "trey": "tray", "seller": "cellar", "jaden": "jayden", "hays": "haze"}
# Ways to write the same spoken thing.
FORMS = [(r"(?<![\w.])-(?=\d)", "minus "), (r"\bjr\b\.?", "junior"), (r"\biii\b", "the third"), (r"double,? 07", "007"), (r"odds maker", "oddsmaker"), (r"(\d)d-m-me", r"\1 dm me"), (r"\bc\. ?j\.", "cj"),
         (r"barnacle (buys|buoys|byes)", "barnacle boys"),     # the recognizer expects "buoys" after "barnacle"; it hears "boys" in other sentences
         (r"double oh seven", "007"), (r"\bd\.? ?m\.?,? me\b", "dm me"), (r"three ninety", "390"), (r"(\d)\s*%", r"\1 percent"),
         (r"\$\s*(\d+)", r"\1 dollars"), (r"\b(\d+)-(\d+)\b", r"\1 and \2"), (r"(\d+)\.(\d+)", r"\1 point \2"), (r"#\s*(\d+)", r"number \1"),
         (r"zero point zero", "0 point 0"), (r"\b(\d+) in (\d+)\b", r"\1 and \2"), (r"goodnight", "good night"),
         (r"muh-homes", "mahomes"), (r"press's", "presses"), (r"\b(dukey|dooky|dukie|duky)\b", "dookie"), (r"\bc ?u\b", "see you")]


def card(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + card(n % 100))
    return card(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + card(n % 1000))


def ordinal(n):
    w = card(n).split()
    last = w[-1]
    w[-1] = ORD.get(last, last[:-1] + "ieth" if last.endswith("y") else last + "th")
    return " ".join(w)


def norm(text):
    t = text.lower().replace("’", "'")
    for pattern, to in FORMS:
        t = re.sub(pattern, to, t)
    t = t.replace("-", " ")
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", lambda m: ordinal(int(m.group(1))), t)
    t = re.sub(r"\d+", lambda m: " " + card(int(m.group(0))) + " ", t)
    t = re.sub(r"[^a-z ]", "", t)
    for a, b in SAME.items():
        t = re.sub(rf"\b{a}\b", b, t)
    return t.split()


def edits(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i in range(1, len(ref) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(hyp) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(hyp)]


_enc, _dec, _tok = whisper(wdir)
recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=_enc, decoder=_dec, tokens=_tok, num_threads=4, language="en", task="transcribe")


def check(name, path):
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    pad = np.zeros(int(0.4 * rate), dtype=np.float32)
    errors = total = 0
    bad = []
    for s in sentences:
        seg = audio[int(s["start"] * rate):int(s["end"] * rate)]
        stream = recognizer.create_stream()
        stream.accept_waveform(rate, np.concatenate([pad, seg, pad]))
        recognizer.decode_stream(stream)
        heard = stream.result.text.strip()
        ref, hyp = norm(s["tts"]), norm(heard)
        e = edits(ref, hyp)
        errors += e
        total += len(ref)
        if e:
            bad.append((s["start"], s["tts"], heard))
    print(f"{name}: {len(sentences)} sentences, {total} words, {errors} word differences ({100 * errors / total:.1f} percent)")
    for start, said, heard in bad:
        print(f"  at {start:6.1f} s  said : {said}\n               heard: {heard}")
    return len(bad)


n = check("clean voice", ROOT / "build" / "narration_clean.wav") + check("old-time voice", ROOT / "build" / "narration_old.wav")
if n:
    print("A person must listen to the sentences above.")
    sys.exit(1)
print("Every sentence matches the script in both files.")
