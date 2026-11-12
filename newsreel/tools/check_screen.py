#!/usr/bin/env python3
"""Check the text on screen against the facts file.

Usage: python3 tools/check_screen.py
Reads:  build/timeline.json, the facts file of that edition, compositions/n1.html ... n9.html, compositions/captions.html

It checks three things:
  1. Each number on screen is a value in the facts file. The report gives the place of each number in the facts.
  2. Each team name on screen is a team of the league, with the exact spelling.
  3. Each caption is a part of a sentence of the script, word for word.
A number that is in the facts can still be next to the wrong name. This check does not see that. A person or a reviewer must look at the frames.
Exit code: 0 when all three checks pass, 1 when one or more fail.
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "build" / "timeline.json").read_text())
F = json.loads((ROOT / "data" / f"{TL['edition']}.facts.json").read_text())
F["league"] = F["league"].strip()
NUM = r"-?\d+(?:\.\d+)?"


def walk(node, path=""):
    """Each number in the facts, with its place. A record such as 6-2 and a streak such as W3 give their parts too."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(node, bool) or node is None:
        return
    elif isinstance(node, (int, float)):
        yield str(node), path
    elif isinstance(node, str):
        for m in re.findall(r"\d+(?:\.\d+)?", node):
            yield m, path


where = {}
for value, path in walk(F):
    where.setdefault(value, []).append(path)
teams = [s["manager"] for s in F["standings"]]


def visible(path):
    t = path.read_text()
    t = re.sub(r"<style>.*?</style>|<script>.*?</script>|<svg.*?</svg>", " ", t, flags=re.S)     # the robot and the film leader are drawings
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


bad = 0
print(f"Edition {TL['edition']}: {F['league']}, season {F['season']}, week {F['week']}")
for sid in [b["id"] for b in TL["beats"]]:
    text = visible(ROOT / "compositions" / f"{sid}.html")
    rows = []
    lower = text.lower()
    for t in teams:                       # a team name with a different spelling (upper case is the headline style)
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])", lower):       # a whole word: "john" is not in a web address
            shown = text[m.start():m.end()]
            if shown not in (t, t.upper()):
                bad += 1
                rows.append(f'team name "{shown}" is not spelled "{t}"')
    # Digits that are a part of a name are not scores: the team names, the league name, and the "30" end mark of a newspaper story.
    for name in sorted(teams + [F["league"]], key=len, reverse=True):
        text = re.sub(re.escape(name), " ", text, flags=re.I)
    text = text.replace("\u2014 30 \u2014", " ")
    whole = 0
    for m in re.finditer(NUM, text):
        n = m.group(0)
        if n.startswith("-") and m.start() > 0 and text[m.start() - 1].isdigit():      # a record such as 6-2: the hyphen is not a minus sign
            n = n[1:]
        places = where.get(n)
        if not places:
            bad += 1
            rows.append(f"{n}: NOT IN THE FACTS")
        elif "." in n:
            rows.append(f"{n} ({places[0]})")
        else:
            whole += 1
    print(f"{sid}: " + "; ".join(dict.fromkeys(rows)) + ("; " if rows else "") + f"{whole} whole numbers, all in the facts")

caps = re.findall(r'<div class="cap"[^>]*><span>(.*?)</span>', (ROOT / "compositions" / "captions.html").read_text(), flags=re.S)
script = " ".join(s["cap"] for b in TL["beats"] for s in b["sentences"])
joined = " ".join(html.unescape(c) for c in caps)
if joined != script:
    bad += 1
    print("captions: the captions in order are NOT the script word for word")
else:
    print(f"captions: {len(caps)} captions; in order they are the script word for word")
if bad:
    print(f"{bad} problem(s). Do not publish this video.")
    sys.exit(1)
print("All numbers on screen are in the facts, and all team names have the exact spelling.")
