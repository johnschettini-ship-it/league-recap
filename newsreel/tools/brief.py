#!/usr/bin/env python3
"""Write the brief for the script writers of one edition: the verified facts and the picture plan, as text.

Usage: python3 tools/brief.py <edition>            for example: python3 tools/brief.py 2026_w9
Reads:  data/<edition>.facts.json, data/<edition of the week before>.facts.json (optional), pronunciations.json
Writes: build/<edition>.brief.json  {"facts": text, "segments": text, "names": {team name: spoken words}, ...}

Every line of the facts text is made by code from the facts file. Nothing is typed by hand.
The script panel (workflows/script-panel.js) takes this file as its input.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from plan import plan, surname, verb, result_line, lead_line, upsets_of, same_game, ORDER

ROOT = pathlib.Path(__file__).resolve().parent.parent
edition = sys.argv[1]
F = json.loads((ROOT / "data" / f"{edition}.facts.json").read_text())
F["league"] = F["league"].strip()                       # the gazette writes "Coozeball " with a space at the end
SAY = {k: v for k, v in json.loads((ROOT / "pronunciations.json").read_text()).items() if not k.startswith("_")}
P = plan(F)
WEEK = F["week"]
prefix = edition[: -len(f"{F['season']}_w{WEEK}")]          # "" for Beer Den 3.0, "coozeball_" for Coozeball, ...
prev_path = ROOT / "data" / f"{prefix}{F['season']}_w{WEEK - 1}.facts.json"
PREV = json.loads(prev_path.read_text()) if prev_path.exists() else None

teams = [s["manager"] for s in F["standings"]]
# In a playoff week the gazette's records, ranks and streaks are those of the end of the regular season: it does not count playoff games.
PLAYOFFS = bool(F.get("playoff_week_start")) and WEEK >= F["playoff_week_start"]
unknown = [t for t in teams if t not in SAY]      # a name that is said as it is spelled has an entry equal to the name
if unknown:
    sys.exit("Add the spoken form of these team names to pronunciations.json: " + ", ".join(unknown))
names = {t: len(SAY.get(t, t).split()) for t in teams}

KIND = {"W": ("wins", "won the last game"), "L": ("losses", "lost the last game"), "T": ("ties", "tied the last game")}
STREAK = lambda code: f"{code[1:]} {KIND[code[0]][0]} in a row" if int(code[1:]) > 1 else KIND[code[0]][1]
WAS = lambda s: f"; was {s['prev_rank']}" if s.get("prev_rank") is not None else ""      # the gazette gives no earlier rank in week 1 and after the first playoff week


def game(r):
    return f"{r['winner']} {r['winner_pts']} {verb(r)} {r['loser']} {r['loser_pts']}" + ("" if r.get("tie") else f" (margin {r['margin']})")


def stars(side):
    return ", ".join(f"{p['player']} {p['pts']}" for p in side["stars"]) + f"; lowest starter {side['dud']['player']} {side['dud']['pts']}"


L = [f"League: {F['league']}. Season {F['season']}. Week {WEEK}. {F['teams']} teams. Edition: {F['edition']['label']}."
     + (f" The playoffs take {F['playoff_teams']} teams and start in week {F['playoff_week_start']}." if F.get("playoff_teams") else "")]
g = 0


def G(text):
    global g
    g += 1
    L.append(f"G{g}  {text}")


G(f"Highest score of the week: {P['high']['manager']}, {P['high']['pts']}." + (" It is also the highest score of the season so far." if "season" in P["high_label"] else ""))
G(f"Lowest score of the week: {P['low']['manager']}, {P['low']['pts']}." + (" It is also the lowest score of the season so far." if "season" in P["low_label"] else ""))
G(f"Closest game: {game(F['closest'])}.")
G(f"Biggest win: {game(F['blowout'])}.")
G("Bench crimes: " + " ".join(
    f"{b['manager']} started {b['started']} ({b['started_pts']}) at {b['slot']} and left {b['benched']} ({b['benched_pts']}) on the bench; gap {b['gap']}."
    for b in F["bench_crimes"]))
G("Booms (best single player scores): " + "; ".join(f"{b['player']} scored {b['pts']} for {b['manager']}" for b in F["booms"]) + ".")
G("Busts (worst starters): " + "; ".join(f"{b['player']} scored {b['pts']} for {b['manager']}" for b in F["busts"]) + ".")
ups = upsets_of(F)
G("Upsets (rank before the week): " + ("; ".join(f"#{u['winner_prev_rank']} {u['winner']} beat #{u['loser_prev_rank']} {u['loser']}" for u in ups)
                                        + (". It is the only upset of the week." if len(ups) == 1 else ".") if ups else "none this week."))
if PLAYOFFS:
    G("Standings at the end of the regular season (this is a playoff week; the gazette does not count playoff games in records, ranks and streaks): "
      + "; ".join(f"{s['rank']}. {s['manager']} {s['record']}" for s in F["standings"]) + ".")
else:
    G("Standings after the week: " + "; ".join(
        f"{s['rank']}. {s['manager']} {s['record']} ({STREAK(s['streak'])}{WAS(s)})" for s in F["standings"]) + ".")
cards = []
for c in F["next_week_card"]:
    o = c["odds"]
    cards.append(f"{c['billing']} (week {c['week']}): {c['a']['manager']} (rank {c['a']['rank']}, {c['a']['record']}) against {c['b']['manager']} "
                 f"(rank {c['b']['rank']}, {c['b']['record']}); the favorite is {o['favorite']} at {o['favorite_pct']} percent, the underdog is {o['underdog']} at {o['underdog_pct']} percent")
G("Next week. " + ". ".join(cards) + ".")
G("All results this week, with each team's best two starters: " + " ".join(
    f"{game(r)}; {r['winner']}: {stars(r['winner_lineup'])}; {r['loser']}: {stars(r['loser_lineup'])}." for r in F["results"]))
sp = (F.get("awards") or {}).get("big_spender")
if sp:
    G(f"Biggest waiver spend: {sp['manager']} spent ${sp['faab']} on {sp['player']}.")
if F.get("most_bench_pts"):
    G(f"Most points left on the bench: {F['most_bench_pts']['manager']}, {F['most_bench_pts']['bench_pts']}.")
lore = F.get("lore") or {}
marks = []
if lore.get("season_high"):
    marks.append(f"highest score of the season: {lore['season_high']['manager']}, {lore['season_high']['pts']}, in week {lore['season_high']['week']}")
if lore.get("season_low"):
    marks.append(f"lowest score of the season: {lore['season_low']['manager']}, {lore['season_low']['pts']}, in week {lore['season_low']['week']}")
if lore.get("hot_streak") and not PLAYOFFS:
    marks.append(f"longest winning streak now: {lore['hot_streak']['manager']}, {STREAK(lore['hot_streak']['streak'])}")
if lore.get("cold_streak") and not PLAYOFFS:
    marks.append(f"longest losing streak now: {lore['cold_streak']['manager']}, {STREAK(lore['cold_streak']['streak'])}")
if marks:
    G("Season marks: " + "; ".join(marks) + ".")
pw = P["power"]
st_rank = {s["manager"]: s["rank"] for s in F["standings"]}
G("Power rankings of the gazette. The rank blends the true record (most of the weight), the last three weeks and total points. "
  "The true record is the record of a team against every other team in every week. Each team: power rank, true record, rank in the standings, record"
  + (", power rank last week" if pw[0].get("prev_power_rank") else "") + ". "
  + "; ".join(f"{r['power_rank']}. {r['manager']} (true record {r['all_play']}; standings rank {st_rank[r['manager']]}, {r['record']}"
              + (f"; was {r['prev_power_rank']}" if r.get("prev_power_rank") else "") + ")" for r in pw) + ".")
if lore.get("luckiest") and lore.get("unluckiest"):
    lk, ul = lore["luckiest"], lore["unluckiest"]
    G(f"Luck (the record against the true record). Luckiest team: {lk['manager']}, record {lk['record']} with a true record of {lk['all_play']}. "
      f"Unluckiest team: {ul['manager']}, record {ul['record']} with a true record of {ul['all_play']}.")
if PREV and PREV.get("next_week_card"):
    c = PREV["next_week_card"][0]
    r = next((r for r in F["results"] if {r["winner"], r["loser"]} == {c["a"]["manager"], c["b"]["manager"]}), None)
    if r:
        o = c["odds"]
        G(f"Last week's edition billed {c['a']['manager']} against {c['b']['manager']} as the {c['billing']}, with {o['favorite']} the favorite at {o['favorite_pct']} percent. "
          f"The result: {game(r)}." + (" The game was a tie." if r.get("tie") else (" The favorite won." if r["winner"] == o["favorite"] else " The underdog won.")))
L.append("The team names, spelled exactly: " + ", ".join(teams) + ".")
L.append("NOT facts, never state: why a player scored what he scored; an injury; anything about a manager as a person; a score, rank, record or margin that is not written above; "
         "a sum or a difference that you computed.")
facts = "\n".join(L)

# ---- the picture plan, in words
n3 = P["n3"]
if n3["mode"] == "upsets":
    n3_text = ("UPSETS. Title \"UPSETS!\". " + f"{len(n3['items'])} torn clippings drop in, one for each upset: "
               + "; ".join(f"\"No. {u['winner_prev_rank']} over No. {u['loser_prev_rank']}: {u['winner']} beat {u['loser']}\"" for u in n3["items"])
               + ". A clipping drops in with the sentence that says \"Number\" and the winner's rank. Give each upset its own sentence.")
else:
    fresh = not any(same_game(r, g) for r in n3["items"] for g in (P["lead"], P["crime_game"], P["cellar"]))
    n3_text = (f"SCORES. Title \"SCORES!\". {len(n3['items'])} torn clipping{'s' if len(n3['items']) != 1 else ''} drop in, one for each game"
               + (" that no other segment shows: " if fresh else " (the week has few games, so a game of another segment is here again): ")
               + "; ".join(f"\"{r['winner_pts']} to {r['loser_pts']}: {r['winner']} {'tied' if r['tie'] else 'beat'} {r['loser']}\" (label: {r['tag'].upper()})" for r in n3["items"])
               + ". A clipping drops in with the first sentence that names one of its two teams. Give each game its own sentence, and name one or both of its teams in it.")
c, bc, cg = P["card"], P["crime"], P["crime_game"]


def LINE(r, manager):
    how, other, margin = result_line(r, manager)
    return f"{how} {other}" + (f" by {margin}" if margin is not None else "")


lead_other = P["lead"]["loser"] if P["lead"]["winner"] == P["high"]["manager"] else P["lead"]["winner"]
segments = "\n".join([
    f"THE {len(ORDER)} SEGMENTS (the pictures are fixed; a line must fit its picture; all {len(ORDER)} are mandatory, in this order)",
    f"n1  OPEN. A film leader counts 3, 2, 1. Then the masthead \"The {F['league']} Gazette, Video Edition\" and a stamp \"EXTRA!\". The announcer greets the league and teases the week.",
    f"n2  THE LEAD. A front page spins in: \"{P['high']['manager'].upper()}, {P['high']['pts']}, {P['high_label'].upper()}\". Then a line enters below it: "
    f"\"{' '.join(lead_line(F, P['high'], P['lead']))}, {P['lead']['winner_pts']} to {P['lead']['loser_pts']}\". That line enters with the sentence that names {lead_other}.",
    f"n3  {n3_text}",
    f"n4  THE BENCH CRIME. A \"WANTED\" poster for {bc['manager']}. Two rows slide in: \"LEFT ON THE BENCH: {bc['benched']}, {bc['benched_pts']}\" and "
    f"\"STARTED AT {bc['slot']}: {bc['started']}, {bc['started_pts']}\". Then a line: \"{LINE(cg, bc['manager'])}\". "
    f"Each row enters with the sentence that says the player's last name ({surname(bc['benched'])}, {surname(bc['started'])}). Say the two last names in two different sentences if you can.",
    f"n5  BOOM AND BUST. Two cards: \"BOOM: {P['boom']['player']}, {P['boom']['pts']}, for {P['boom']['manager']}\" and \"BUST: {P['bust']['player']}, {P['bust']['pts']}, for {P['bust']['manager']}\". "
    f"The bust card enters with the sentence that says \"{surname(P['bust']['player'])}\" or \"Bust\".",
    f"n6  THE BASEMENT. A small sad notice under a cobweb: \"{P['low_label'].upper()}: {P['low']['manager']}, {P['low']['pts']}\", "
    f"with the record and the rank of {P['low']['manager']} below it. Then a line: \"{LINE(P['cellar'], P['low']['manager'])}\". "
    f"If a sentence names the other team of that game, the line enters with that sentence. If not, it enters in the middle of the segment.",
    f"n7  THE STANDINGS. The full table of {F['teams']} teams with records" + (", the moves up and down" if F["standings"][0].get("prev_rank") is not None else "")
    + (f", and the playoff line after rank {F['playoff_teams']}" if F.get("playoff_teams") else "") + ".",
    f"n7b POWER RANKINGS. Title \"POWER RANKINGS\". A table of all {F['teams']} teams in the order of the power rank: power rank, team, {'move up or down from last week, ' if pw[0].get('prev_power_rank') else ''}record, and true record. "
    f"The first row is {pw[0]['manager']}, true record {pw[0]['all_play']}. The row of a team gets a tint when a sentence names that team. Name {pw[0]['manager']} in this segment. "
    f"Say \"true record\" for the all-play record; the table has that label.",
    f"n8  NEXT WEEK. A fight poster \"{c['billing'].upper()}, WEEK {c['week']}\": {c['a']['manager']} (No. {c['a']['rank']}, {c['a']['record']}) against {c['b']['manager']} "
    f"(No. {c['b']['rank']}, {c['b']['record']}). Then a line: \"THE ODDS: {c['odds']['favorite']} {c['odds']['favorite_pct']}%\". "
    f"That line enters with the sentence that says the odds; that sentence must have the word \"odds\" or \"percent\".",
    "n9  SIGN-OFF. The masthead, \"THAT'S THE NEWS\", and an end card \"READ THE FULL EDITION\". One last joke, then the last sentence sends the viewer to the full edition. "
    "The last sentence must have the word \"Gazette\" or \"edition\".",
])

hooks = [{"segment": "n2", "any": [lead_other], "picture": "the result line under the front page"}]
if n3["mode"] == "upsets":
    hooks += [{"segment": "n3", "any": [f"Number {u['winner_prev_rank']} "], "picture": f"the clipping of the upset by {u['winner']}", "own_sentence": True} for u in n3["items"]]
else:
    hooks += [{"segment": "n3", "any": [r["winner"], r["loser"]], "picture": f"the clipping of {r['winner']} against {r['loser']}", "own_sentence": True} for r in n3["items"]]
hooks += [
    {"segment": "n4", "any": [surname(bc["benched"])], "picture": "the row of the benched player"},
    {"segment": "n4", "any": [surname(bc["started"])], "picture": "the row of the started player"},
    {"segment": "n5", "any": [surname(P["bust"]["player"]), "Bust"], "picture": "the bust card"},
    {"segment": "n7b", "any": [pw[0]["manager"]], "picture": "the first row of the power rankings"},
    {"segment": "n8", "any": ["odds", "percent"], "picture": "the odds line"},
    {"segment": "n9", "any": ["Gazette", "edition"], "picture": "the end card", "last_sentence": True},
]

out = {"edition": edition, "order": ORDER, "hooks": hooks, "league": F["league"], "season": F["season"], "week": WEEK, "teams": teams, "names": names,
       "spoken": {t: SAY.get(t, t) for t in teams}, "facts": facts, "segments": segments}
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / f"{edition}.brief.json").write_text(json.dumps(out, indent=1))
print(facts)
print()
print(segments)
print()
print("spoken words of each team name:", names)
