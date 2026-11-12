"""The picture plan of one edition: which facts each of the nine segments shows.

build.py draws the plan. brief.py describes the plan to the script writers.
There is one plan, so the words and the pictures agree.

A segment that has no fact to show stops the build with a message. It does not show a default.
"""


def game_of(F, manager):
    for r in F["results"]:
        if manager in (r["winner"], r["loser"]):
            return r
    raise SystemExit(f"The facts have no result for {manager!r}")


def same_game(a, b):
    return a["winner"] == b["winner"] and a["loser"] == b["loser"]


def verb(r):
    """The word between the two teams of a result. The gazette writes a tie with a "winner" and a "loser" and the flag "tie"."""
    return "tied" if r.get("tie") else "beat"


def result_line(r, manager):
    """The result of a game from the side of one team: "Lost to X by 4.14", "Beat X by 4.14" or "Tied with X"."""
    other = r["loser"] if r["winner"] == manager else r["winner"]
    if r.get("tie"):
        return "Tied with", other, None
    return ("Beat" if r["winner"] == manager else "Lost to"), other, r["margin"]


def lead_line(F, high, lead):
    """The words of the result line of the lead: the top scorer, then "beat", "lost to" or "tied", then the other team."""
    won = lead["winner"] == high["manager"]
    other = lead["loser"] if won else lead["winner"]
    return high["manager"], ("tied" if lead.get("tie") else ("beat" if won else "lost to")), other


def upsets_of(F):
    """The upsets of the facts without a tied game. The gazette can list a tie as an upset, with the first team as the "winner"."""
    tied = {(r["winner"], r["loser"]) for r in F["results"] if r.get("tie")}
    return [u for u in F.get("upsets") or [] if (u["winner"], u["loser"]) not in tied]


def cue_pattern(word):
    """A regular expression for a cue word as a whole word: "odds" is not in "oddsmaker", and 0.0 is not in 30.0."""
    import re
    w = re.escape(str(word).strip())
    if re.fullmatch(r"-?\d+(\.\d+)?", str(word).strip()):
        return rf"(?<![\d.]){w}(?!\d|\.\d)"
    return rf"(?<![A-Za-z0-9]){w}(?![A-Za-z0-9])"


def need(F, key, segment):
    if not F.get(key):
        raise SystemExit(f"The facts have no {key!r}. Segment {segment} needs a different picture for this week.")
    return F[key]


def surname(player):
    """The word of a player's name that the announcer says: "Mike Washington Jr." gives "Washington"."""
    words = [w for w in player.split() if w.strip(".").lower() not in ("jr", "sr", "ii", "iii", "iv", "v")]
    return words[-1] if words else player


def tag_of(F, r):
    if any(u["winner"] == r["winner"] and u["loser"] == r["loser"] for u in upsets_of(F)):
        return "Upset"
    if F.get("closest") and same_game(r, F["closest"]):
        return "Closest game"
    if F.get("blowout") and same_game(r, F["blowout"]):
        return "Biggest win"
    return "Final"


def season_mark(F, key, row):
    """True when this week's high or low is also the season mark in the facts (lore.season_high, lore.season_low)."""
    m = (F.get("lore") or {}).get(key) or {}
    return m.get("week") == F["week"] and m.get("manager") == row["manager"] and m.get("pts") == row["pts"]


def plan(F):
    high, low = need(F, "high", "n2"), need(F, "low", "n6")
    lead, cellar = game_of(F, high["manager"]), game_of(F, low["manager"])
    crime = need(F, "bench_crimes", "n4")[0]
    crime_game = game_of(F, crime["manager"])
    ups = upsets_of(F)
    if len(ups) >= 2:
        # Two or three upsets fill the segment: one clipping for each upset.
        n3 = {"mode": "upsets", "title": "Upsets!", "items": ups[:3]}
    else:
        # Fewer than two upsets: the segment shows the games that no other segment shows.
        shown = [lead, crime_game, cellar]
        rest = [r for r in F["results"] if not any(same_game(r, g) for g in shown)]
        rest += [r for r in F["results"] if not any(same_game(r, g) for g in rest)]      # fill from the other games when fewer than three remain
        n3 = {"mode": "scores", "title": "Scores!",
              "items": [{"winner": r["winner"], "winner_pts": r["winner_pts"], "loser": r["loser"], "loser_pts": r["loser_pts"],
                         "margin": r["margin"], "tie": bool(r.get("tie")), "tag": "Tie" if r.get("tie") else tag_of(F, r)} for r in rest[:3]]}
    return {
        "high": high, "lead": lead, "high_label": "Best score of the season" if season_mark(F, "season_high", high) else "Best score of the week",
        "n3": n3,
        "crime": crime, "crime_game": crime_game,
        "boom": need(F, "booms", "n5")[0], "bust": need(F, "busts", "n5")[0],
        "low": low, "cellar": cellar, "low_label": "Lowest score of the season" if season_mark(F, "season_low", low) else "Lowest score of the week",
        "card": need(F, "next_week_card", "n8")[0],
        "power": need(F, "power_rankings", "n7b"),
    }


# The segments in the order of the video. "n7b" is the power rankings; the Week 8 edition was made before that segment.
ORDER = ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n7b", "n8", "n9"]
