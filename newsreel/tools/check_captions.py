#!/usr/bin/env python3
"""Check a rendered video frame by frame: the caption strip must be on screen in each frame of each caption.

Usage: python3 tools/check_captions.py <video.mp4> [chat|social]
Reads:  compositions/captions.html (the caption clips of the build that made the video), the video
The check reads the strip area of each frame. A frame of a caption with no dark pixel in that area has no strip.
Exit code: 0 when no frame of a caption is without the strip, 1 if not.
"""
import pathlib, re, subprocess, sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) < 2:
    sys.exit(__doc__)
video, fmt = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "chat")
top = 1184 - (60 if fmt == "chat" else 0)
clips = [(float(a), float(a) + float(b)) for a, b in re.findall(r'id="cap-\d+" class="clip" data-start="([\d.]+)" data-duration="([\d.]+)"', (ROOT / "compositions" / "captions.html").read_text())]
if not clips:
    sys.exit("compositions/captions.html has no caption clips")
W, H = 94, 12
raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", video, "-vf", f"crop=940:124:70:{top},scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W)
fps = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video],
                           capture_output=True, text=True, check=True).stdout.strip().split("/")[0])
present = frames.min(axis=(1, 2)) < 200            # the rules and the words of the strip are dark; the paper is near 245.
                                                   # 185, not darker: the white flash of a film cut makes the strip lighter for one frame
missing, inside = [], 0
for k in range(len(frames)):
    t = k / fps
    if any(a + 0.02 <= t <= b - 0.02 for a, b in clips):        # 0.02 s: the frame is clearly inside one caption
        inside += 1
        if not present[k]:
            missing.append(round(t, 3))
holes = [(round(b, 4), round(c, 4)) for (a, b), (c, d) in zip(clips, clips[1:]) if 0 < c - b < 0.05]
on_a_frame = [h for h in holes if any(abs(k / fps - (h[0] + h[1]) / 2) <= (h[1] - h[0]) / 2 for k in range(int(h[0] * fps) - 1, int(h[1] * fps) + 2))]
print(f"{len(frames)} frames, {len(clips)} captions; {inside} frames are inside a caption; {len(missing)} of them have no strip" + (f": {missing[:12]}" if missing else ""))
print(f"{len(holes)} short holes between two captions in the build; {len(on_a_frame)} of them have a video frame in the hole" + (f": {[h[0] for h in on_a_frame][:12]}" if on_a_frame else ""))
strip_off_between = sum(1 for h in on_a_frame for k in [round((h[0] + h[1]) / 2 * fps)] if 0 <= k < len(frames) and not present[k])
if on_a_frame:
    print(f"{strip_off_between} of those frames show no strip in the video")
sys.exit(1 if missing or strip_off_between else 0)
