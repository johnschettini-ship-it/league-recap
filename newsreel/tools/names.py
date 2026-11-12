#!/usr/bin/env python3
"""Copy a facts file of the gazette into data/ and apply the display names of display_names.json.

Usage: python3 tools/names.py <gazette facts file> <edition>      for example: ... posts/<id>_2026_w9_recap.facts.json uncle-rico_2026_w9
The gazette names a team by its owner's username. When an owner asks for the team name, display_names.json maps the username
to that name for one league (the key is the league path, the first part of the edition name). Every string in the facts that is
equal to the username, or that contains it as a word, gets the team name.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src, edition = pathlib.Path(sys.argv[1]), sys.argv[2]
league = edition.rsplit("_", 2)[0] if edition.count("_") >= 2 else ""
names = json.loads((ROOT / "display_names.json").read_text()).get(league, {})
F = json.loads(src.read_text())
count = 0


def fix(x):
    global count
    if isinstance(x, dict):
        return {k: fix(v) for k, v in x.items()}
    if isinstance(x, list):
        return [fix(v) for v in x]
    if isinstance(x, str):
        for old, new in names.items():
            y = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])", new, x)
            if y != x:
                count += 1
                x = y
    return x


out = ROOT / "data" / f"{edition}.facts.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(fix(F), indent=1, ensure_ascii=False))
print(f"wrote {out.relative_to(ROOT)}; {count} strings renamed with {len(names)} display name(s)")
