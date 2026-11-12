#!/usr/bin/env python3
"""Put a finished video next to the league's recap, and add the video link to the chat post.

Usage: python3 tools/publish.py <edition> <video.mp4>
Writes: ../posts/<league id>_<season>_w<week>_recap.newsreel.mp4 (site.py copies it to the site)
        a last line in ../posts/<...>_recap.txt:  "🎬 Watch the newsreel: <site>/<path>/newsreel-week-<week>.mp4"
The chat post then has two links: the full stories and the video. A second run replaces the line; it does not add a second one.
"""
import json, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAZETTE = ROOT.parent
edition, video = sys.argv[1], pathlib.Path(sys.argv[2])
season, week = edition.rsplit("_", 2)[-2], int(edition.rsplit("_", 1)[-1].lstrip("w"))
path = edition[: -len(f"{season}_w{week}")].rstrip("_")
league = next((lg for lg in json.loads((GAZETTE / "leagues.json").read_text()) if lg.get("path", "") == path), None)
if league is None:
    sys.exit(f"No league with path {path!r} in leagues.json")
key = f"{league['id']}_{season}_w{week}_recap"
txt = GAZETTE / "posts" / f"{key}.txt"
if not txt.exists():
    sys.exit(f"{txt.name} does not exist. Run the recap first.")
shutil.copyfile(video, GAZETTE / "posts" / f"{key}.newsreel.mp4")
url = f"{league['site'].rstrip('/')}/{path + '/' if path else ''}newsreel-week-{week}.mp4"
lines = [l for l in txt.read_text(encoding="utf-8").rstrip("\n").splitlines() if not l.startswith("🎬")]
txt.write_text("\n".join(lines) + f"\n🎬 Watch the newsreel: {url}\n", encoding="utf-8")
print(f"posts/{key}.newsreel.mp4 and the link {url}")
