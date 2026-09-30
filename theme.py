"""Edition themes: a seasonal rotation by publish date, plus a playoff layer by league week.
Pure functions, stdlib only. Used by recap.py (tells the writer) and site.py/comic.py (dresses the page)."""
import datetime as dt
import math

# key, (start month, day), (end month, day), label, tagline, sub-line, accent, ornament, costumes, scenes
SEASONS = [
    ("regular", None, None, "Week {week} Edition", "All the Scores That Are Fit to Print",
     "Waivers & wagers within", "#8a2a1c", None, None, None),
    ("halloween", (10, 22), (11, 1), "Halloween Edition", "All the Scares That Are Fit to Print",
     "Tricks, treats & trades within", "#b45309", "pumpkin", ("witch",), ("bats", "night")),
    ("fall", (11, 2), (11, 20), "Autumn Edition", "All the Leaves That Are Fit to Print",
     "Falling leaves & falling teams", "#9a3412", "leaf", ("scarf", "cap"), ("leaves",)),
    ("thanksgiving", (11, 21), (11, 29), "Thanksgiving Edition", "All the Stuffing That's Fit to Print",
     "Gravy, gratitude & garbage time", "#92400e", "turkey", ("pilgrim",), ("leaves", "stands")),
    ("snow", (11, 30), (12, 17), "Winter Edition", "All the Flurries That Are Fit to Print",
     "Cold weather, colder benches", "#1e4e79", "snowflake", ("earmuffs", "scarf"), ("snow",)),
    ("christmas", (12, 18), (12, 28), "Christmas Edition", "All the Cheer That's Fit to Print",
     "Naughty & nice lists within", "#9b1c1c", "holly", ("santa",), ("lights", "snow")),
    ("newyear", (12, 29), (1, 10), "New Year's Edition", "Out With the Old, In With the Bold",
     "Resolutions & recaps within", "#8a6d1f", "star", ("party",), ("fireworks", "confetti")),
]
ROUND_NAMES = {1: "Championship", 2: "Semifinals", 3: "Quarterfinals", 4: "Round of 16"}


def edition_date(f):
    if f.get("edition_date"):
        return dt.date.fromisoformat(f["edition_date"][:10])
    # fallback: Wednesday after week N of an NFL season that opens in early September
    return dt.date(int(f["season"]), 9, 16) + dt.timedelta(weeks=int(f["week"]) - 1)


def _in(d, start, end):
    md = (d.month, d.day)
    return start <= md <= end if start <= end else (md >= start or md <= end)   # wraps New Year


def season(d):
    for s in SEASONS[1:]:
        if _in(d, s[1], s[2]):
            return s
    return SEASONS[0]


def playoff_phase(week, start, teams):
    """None | race | playoffs | champion | offseason, from the league's own playoff settings."""
    if not start:
        return None
    rounds = max(1, math.ceil(math.log2(teams or 6)))
    final = start + rounds - 1
    if week < start - 4:
        return None
    if week < start:
        left = start - 1 - week
        return {"phase": "race", "weeks_left": left, "playoff_teams": teams or 6, "starts": start,
                "label": "Playoff Field Set" if left == 0 else f"Playoff Race: {left} Week{'s' if left > 1 else ''} Left"}
    if week < final:
        name = ROUND_NAMES.get(final - week + 1, f"Round {week - start + 1}")
        nxt = ROUND_NAMES.get(final - week, "Next Round")
        return {"phase": "playoffs", "round": name, "next": nxt, "label": f"Playoff Edition: {name}"}
    if week == final:
        return {"phase": "champion", "label": "Championship Extra!"}
    return {"phase": "offseason", "label": "Season Finale"}


def edition(f):
    """Everything the page, comic and writer need to dress this issue."""
    d = edition_date(f)
    key, _, _, label, tagline, sub, accent, orn, costumes, scenes = season(d)
    p = playoff_phase(int(f["week"]), f.get("playoff_week_start"), f.get("playoff_teams"))
    e = {"key": key, "date": d.isoformat(), "label": label.format(week=f["week"]), "tagline": tagline,
         "sub": sub, "accent": accent, "ornament": orn, "costumes": costumes, "scenes": scenes, "playoff": p}
    if p and p["phase"] in ("playoffs", "champion", "offseason"):
        e["label"] = p["label"]
        e["tagline"] = "Extra! Extra! A Champion Is Crowned" if p["phase"] == "champion" else "Win or Go Home"
        e["sub"] = "Survive & advance" if p["phase"] == "playoffs" else "Glory within"
        e["ornament"] = "trophy" if p["phase"] == "champion" else "football"
        e["costumes"] = ("crown",) if p["phase"] == "champion" else ("helmet",) + (costumes or ())
        e["scenes"] = ("confetti", "stands") if p["phase"] == "champion" else ("stands",) + (scenes or ())
    return e
