#!/usr/bin/env python3
"""Take the review frames of the built edition, and write the input of the review panel (workflows/video-review.js).

Usage: python3 tools/frames.py <out_dir> [git diff command for the code reviewer]
Reads:  build/timeline.json, build/<edition>.brief.json (from tools/brief.py)
Writes: <out_dir>/*.png (one frame at the end of each segment, one in each sentence), build/<edition>.review.json

Set HYPERFRAMES_BROWSER_PATH and HYPERFRAMES_NO_TELEMETRY=1 before the call, as for the other HyperFrames commands.
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) < 2:
    sys.exit(__doc__)
out = pathlib.Path(sys.argv[1]).resolve()
diff = sys.argv[2] if len(sys.argv) > 2 else "git -C " + str(ROOT.parent) + " diff HEAD~1 -- gazette-newsreel/tools gazette-newsreel/workflows"
TL = json.loads((ROOT / "build" / "timeline.json").read_text())
brief = json.loads((ROOT / "build" / f"{TL['edition']}.brief.json").read_text())

shots = [{"t": 1.2, "segment": TL["beats"][0]["id"], "kind": "film leader (the count 3, 2, 1 before the first sentence)"}]
for b in TL["beats"]:
    for s in b["sentences"]:
        shots.append({"t": round(s["start"] + 0.6 * (s["end"] - s["start"]), 2), "segment": b["id"], "kind": "middle of sentence", "sentence": s["cap"]})
    shots.append({"t": round(max(b["end"] - 0.3, min(b["end"] - 0.06, b["sentences"][-1]["end"] + 0.32)), 2), "segment": b["id"], "kind": "end of segment"})      # after the last caption goes
shots.sort(key=lambda x: x["t"])
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("*.png"):
    old.unlink()
subprocess.run(["npx", "--yes", "hyperframes", "snapshot", "--at", ",".join(str(s["t"]) for s in shots), "--no-end", "-o", str(out)],
               cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
files = sorted(out.glob("frame-*.png"), key=lambda p: int(re.match(r"frame-(\d+)", p.name).group(1)))
if len(files) != len(shots):
    sys.exit(f"{len(shots)} frames were asked for and {len(files)} were written. Stopped.")
for s, f in zip(shots, files):
    s["path"] = str(f)
args = {"edition": TL["edition"], "project_dir": str(ROOT), "frames": shots, "facts": brief["facts"], "segments": brief["segments"],
        "script": "\n".join(b["id"] + ":  " + "  |  ".join(s["cap"] for s in b["sentences"]) for b in TL["beats"]), "diff_command": diff}
(ROOT / "build" / f"{TL['edition']}.review.json").write_text(json.dumps(args))
print(f"{len(files)} frames in {out}; wrote build/{TL['edition']}.review.json")
