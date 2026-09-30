#!/usr/bin/env python3
"""Sleeper league recap bot. Python 3.9+, standard library only.

  python recap.py            recap last completed week
  python recap.py 3          recap week 3
  python recap.py 3 --regen  ignore saved post and rebuild

Layer 1 (analyze) = deterministic facts. Layer 2 (write) = one LLM call.
Every number in the LLM text is checked against the facts; if any is
unsupported it retries once, then falls back to a no-LLM template.
"""
import json, os, re, sys, time, pathlib, urllib.request

CFG = {
    "league_id": os.environ.get("SLEEPER_LEAGUE_ID", "1313254837680357376"),
    "tone": os.environ.get("RECAP_TONE", "CASUAL"),          # CLEAN | CASUAL | SPICY
    "model": os.environ.get("RECAP_MODEL", "claude-haiku-4-5-20251001"),
    "usd_per_mtok_in": 1.0, "usd_per_mtok_out": 5.0,          # update if pricing changes
    "bench_crime_min": 10.0,   # bench player beat an eligible starter by this much
    "upset_rank_gap": 4,       # winner ranked this many spots below loser
    "mover_min": 2,            # standings jump worth mentioning
}
HERE = pathlib.Path(__file__).resolve().parent
CACHE, POSTS = HERE / "cache", HERE / "posts"
API = "https://api.sleeper.app/v1"
FLEX = {"FLEX": {"RB", "WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
        "REC_FLEX": {"WR", "TE"}, "WRRB_FLEX": {"RB", "WR"}}
BENCH_SLOTS = {"BN", "IR", "TAXI"}


# ---------------------------------------------------------------- Sleeper
def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "league-recap/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def players_db():
    """Sleeper asks for /players/nfl (~5MB) at most once a day, so cache a slim copy."""
    f = CACHE / "players.json"
    if not f.exists() or time.time() - f.stat().st_mtime > 86400:
        CACHE.mkdir(exist_ok=True)
        slim = {}
        for pid, p in get("/players/nfl").items():
            name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            slim[pid] = {"n": name or pid, "pos": p.get("fantasy_positions") or [p.get("position")]}
        f.write_text(json.dumps(slim), encoding="utf-8")
    return json.loads(f.read_text(encoding="utf-8"))


def fetch(lid, week):
    return {
        "league": get(f"/league/{lid}"),
        "users": get(f"/league/{lid}/users"),
        "rosters": get(f"/league/{lid}/rosters"),
        "matchups": {w: get(f"/league/{lid}/matchups/{w}") for w in range(1, week + 1)},
        "transactions": get(f"/league/{lid}/transactions/{week}"),
    }


# ---------------------------------------------------------------- Layer 1
def r2(x):
    return round(float(x or 0), 2)


def check_complete(raw, week):
    """Refuse to recap partial data. Raises ValueError."""
    rids = {r["roster_id"] for r in raw["rosters"]}
    for w in range(1, week + 1):
        seen = {m["roster_id"] for m in raw["matchups"].get(w) or [] if m.get("matchup_id") is not None}
        if seen != rids:
            raise ValueError(f"week {w}: matchups cover {len(seen)} of {len(rids)} rosters")
        if all(not m.get("points") for m in raw["matchups"][w]):
            raise ValueError(f"week {w}: no points yet")


def analyze(raw, P, week, cfg=CFG):
    lg = raw["league"]
    settings = lg.get("settings") or {}
    uname = {u["user_id"]: u.get("display_name") or u["user_id"] for u in raw["users"]}
    owner = {r["roster_id"]: uname.get(r.get("owner_id"), f"Team {r['roster_id']}") for r in raw["rosters"]}
    slots = [s for s in lg["roster_positions"] if s not in BENCH_SLOTS]
    pname = lambda pid: "Empty slot" if pid in (None, "0") else P.get(pid, {}).get("n", pid)
    ppos = lambda pid: set(P.get(pid, {}).get("pos") or [])

    def games(w):
        by = {}
        for m in raw["matchups"][w]:
            if m.get("matchup_id") is not None:
                by.setdefault(m["matchup_id"], []).append(m)
        return [g for g in by.values() if len(g) == 2]

    def table(upto):
        rec = {rid: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "res": []} for rid in owner}
        for w in range(1, upto + 1):
            pts = {m["roster_id"]: m["points"] or 0 for m in raw["matchups"][w] if m.get("matchup_id") is not None}
            for a, b in games(w):
                for x, y in ((a, b), (b, a)):
                    k = "w" if x["points"] > y["points"] else "l" if x["points"] < y["points"] else "t"
                    rec[x["roster_id"]][k] += 1
                    rec[x["roster_id"]]["res"].append(k)
            for rid, p in pts.items():
                rec[rid]["pf"] += p
            if settings.get("league_average_match") and pts:   # median-game leagues
                med = sorted(pts.values())[len(pts) // 2 - 1: len(pts) // 2 + 1]
                med = sum(med) / len(med)
                for rid, p in pts.items():
                    rec[rid]["w" if p > med else "l"] += 1
        order = sorted(rec, key=lambda i: (-(rec[i]["w"] + rec[i]["t"] / 2), -rec[i]["pf"]))
        for n, rid in enumerate(order, 1):
            rec[rid]["rank"] = n
        return rec

    now, before = table(week), (table(week - 1) if week > 1 else None)

    def lineup(m):
        """Top 2 starters + worst skill starter: story material, kept small."""
        rows = [{"player": pname(s), "slot": slot, "pts": r2(p)}
                for slot, s, p in zip(slots, m.get("starters") or [], m.get("starters_points") or [])
                if s not in (None, "0")]
        rows.sort(key=lambda x: -x["pts"])
        skill = [x for x in rows if x["slot"] not in ("K", "DEF")]
        return {"stars": rows[:2], "dud": skill[-1] if skill else None}

    # results
    results = []
    for a, b in games(week):
        w, l = (a, b) if a["points"] >= b["points"] else (b, a)
        results.append({"winner": owner[w["roster_id"]], "winner_pts": r2(w["points"]),
                        "loser": owner[l["roster_id"]], "loser_pts": r2(l["points"]),
                        "margin": r2(w["points"] - l["points"]), "tie": a["points"] == b["points"],
                        "winner_lineup": lineup(w), "loser_lineup": lineup(l),
                        "_w": w["roster_id"], "_l": l["roster_id"]})
    teams = [m for m in raw["matchups"][week] if m.get("matchup_id") is not None]
    ranked = sorted(teams, key=lambda m: -(m["points"] or 0))

    # bench + individual players
    crimes, bench_totals, empty, starters_all = [], [], [], []
    for m in teams:
        pp, st, sp = m.get("players_points") or {}, m.get("starters") or [], m.get("starters_points") or []
        bench = [p for p in m.get("players") or [] if p not in st]
        bench_totals.append({"manager": owner[m["roster_id"]], "bench_pts": r2(sum(pp.get(p, 0) for p in bench))})
        worst = None
        for slot, s, spts in zip(slots, st, sp):
            if s in (None, "0"):
                empty.append({"manager": owner[m["roster_id"]], "slot": slot})
            else:
                starters_all.append((spts, s, m["roster_id"], slot))
            for b in bench:
                gap = pp.get(b, 0) - (spts or 0)
                if ppos(b) & FLEX.get(slot, {slot}) and gap >= cfg["bench_crime_min"] and (not worst or gap > worst["gap"]):
                    worst = {"manager": owner[m["roster_id"]], "benched": pname(b), "benched_pts": r2(pp.get(b)),
                             "started": pname(s), "started_pts": r2(spts), "slot": slot, "gap": r2(gap)}
        if worst:
            crimes.append(worst)
    crimes.sort(key=lambda c: -c["gap"])
    starters_all.sort(key=lambda x: -x[0])
    booms = [{"player": pname(p), "pts": r2(v), "manager": owner[rid]} for v, p, rid, _ in starters_all[:3]]
    skill = [x for x in starters_all if x[3] not in ("K", "DEF")]
    busts = [{"player": pname(p), "pts": r2(v), "manager": owner[rid]} for v, p, rid, _ in skill[::-1][:3]]

    # transactions (completed only)
    week_pts = {m["roster_id"]: m.get("players_points") or {} for m in teams}
    adds, drops, trades = [], [], []
    budget = settings.get("waiver_budget") if settings.get("waiver_type") == 2 else None
    used = {r["roster_id"]: (r.get("settings") or {}).get("waiver_budget_used", 0) for r in raw["rosters"]}
    for t in raw["transactions"]:
        if t.get("status") != "complete":
            continue
        a, d = t.get("adds") or {}, t.get("drops") or {}
        if t["type"] == "trade":
            side = {}
            for pid, rid in a.items():
                side.setdefault(owner[rid], []).append(pname(pid))
            for pk in t.get("draft_picks") or []:
                side.setdefault(owner.get(pk["owner_id"], "?"), []).append(f"{pk['season']} round {pk['round']} pick")
            trades.append({"receives": side})
            continue
        bid = (t.get("settings") or {}).get("waiver_bid")
        for pid, rid in a.items():
            row = {"manager": owner[rid], "player": pname(pid), "via": t["type"]}
            if budget is not None and t["type"] == "waiver":
                row["faab"] = bid or 0
                row["faab_left"] = budget - used.get(rid, 0)
            if pid in week_pts.get(rid, {}):
                row["pts_this_week"] = r2(week_pts[rid][pid])
            adds.append(row)
        for pid, rid in d.items():
            drops.append({"manager": owner[rid], "player": pname(pid)})
    adds.sort(key=lambda x: -x.get("faab", -1))

    # standings
    def streak(res):
        if not res:
            return ""
        n = len(res) - len(res.rstrip(res[-1])) if isinstance(res, str) else 0
        return f"{res[-1].upper()}{n}"
    standings = []
    for rid, r in sorted(now.items(), key=lambda kv: kv[1]["rank"]):
        row = {"rank": r["rank"], "manager": owner[rid], "record": f"{r['w']}-{r['l']}" + (f"-{r['t']}" if r["t"] else ""),
               "pf": r2(r["pf"]), "streak": streak("".join(r["res"]))}
        if before:
            row["prev_rank"] = before[rid]["rank"]
        standings.append(row)
    movers = [s for s in standings if "prev_rank" in s and abs(s["prev_rank"] - s["rank"]) >= cfg["mover_min"]]
    upsets = []
    if before:
        for g in results:
            gap = before[g["_w"]]["rank"] - before[g["_l"]]["rank"]
            if gap >= cfg["upset_rank_gap"]:
                upsets.append({"winner": g["winner"], "winner_prev_rank": before[g["_w"]]["rank"],
                               "loser": g["loser"], "loser_prev_rank": before[g["_l"]]["rank"]})
    crime_by = {c["manager"]: c for c in crimes}
    st_by = {s["manager"]: s for s in standings}
    for g in results:
        for side in ("winner", "loser"):                 # record + rank for each side
            s = st_by[g[side]]
            g[f"{side}_record"], g[f"{side}_rank"], g[f"{side}_streak"] = s["record"], s["rank"], s["streak"]
            if "prev_rank" in s:
                g[f"{side}_prev_rank"] = s["prev_rank"]
    for g in results:
        del g["_w"], g["_l"]
        for side in ("winner", "loser"):
            if g[side] in crime_by:
                g[f"{side}_bench_crime"] = crime_by[g[side]]

    by_margin = sorted(results, key=lambda g: g["margin"])
    return {
        "league": lg["name"], "season": lg["season"], "week": week, "teams": len(owner),
        "playoff_week_start": settings.get("playoff_week_start"),
        "results": results,
        "high": {"manager": owner[ranked[0]["roster_id"]], "pts": r2(ranked[0]["points"])},
        "low": {"manager": owner[ranked[-1]["roster_id"]], "pts": r2(ranked[-1]["points"])},
        "closest": by_margin[0], "blowout": by_margin[-1],
        "bench_crimes": crimes[:3], "most_bench_pts": max(bench_totals, key=lambda b: b["bench_pts"]),
        "empty_slots": empty, "booms": booms, "busts": busts,
        "adds": adds, "drops": drops, "trades": trades,
        "faab_budget": budget,
        "standings": standings, "movers": movers, "upsets": upsets,
    }


# ---------------------------------------------------------------- validator
NUM = re.compile(r"\d+(?:\.\d+)?")


def norm(x):
    return f"{float(x):.2f}".rstrip("0").rstrip(".")


def allowed_numbers(facts):
    ok = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            ok.add(norm(x))
        elif isinstance(x, str):
            ok.update(norm(n) for n in NUM.findall(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            ok.add(norm(len(x)))          # "3 trades went down"
            for v in x:
                walk(v)
    walk(facts)
    return ok


def unsupported_numbers(text, facts):
    ok = allowed_numbers(facts)
    return sorted({n for n in NUM.findall(text) if norm(n) not in ok})


# ---------------------------------------------------------------- Layer 2
TONES = {"CLEAN": "Light sports-commentary humor. No insults.",
         "CASUAL": "Friendly group-chat trash talk, slightly sarcastic.",
         "SPICY": "Aggressive fantasy roasting, but only about fantasy performance and league behavior."}

STORY_SPLIT = "===STORIES==="

SYSTEM = """You are the unofficial reporter for a fantasy football league.
Using ONLY the JSON facts given, write TWO things separated by a line containing exactly
""" + STORY_SPLIT + """

PART 1 — WhatsApp recap. 150-350 words. WhatsApp formatting: *bold* headers, emoji, short lines.
Sections, in order (skip if no data): 🏈 WEEK N RECAP, 👑 Top Dog, 💀 Basement,
😬 Heartbreaker (closest), 🔨 Blowout, 🚨 Upset, 🚑 Bench Crime, 💥 Booms & Busts,
💰 FAAB Watch, 🔄 League Activity, 📈 Standings, 🗣️ Commissioner's Desk
(one closing joke drawn from the facts).
📈 Standings = every team, one line each, in rank order:
<rank>. <manager> <record> <▲n / ▼n / – from prev_rank> <streak if 2+>
Then one line on the top and bottom of the table.

PART 2 — Matchup stories for the league newspaper. One per game in "results", biggest
margin last. For each, exactly this shape:
### <one fitting emoji> <punny headline>
<80-140 word story, in 1-2 short paragraphs; the page adds a scorebox, so don't restate the score line>
🎭 <rhyming couplet, line 1>
<couplet line 2>
🎤 *Kicker:* <one line>
Icons in the story body: at most 🚑 (bench crime), 💸 (FAAB pickup), 🔄 (trade). No others.
Style: mock-epic satire, like a 1900s newspaper war correspondent covering a backyard
game. Build the story around the players in winner_lineup / loser_lineup / bench crimes.

NAME PUNS ARE THE HEART OF IT. Bend the player's name itself into a word or phrase:
Purdy -> "Purdy please", Bijan -> "Bijan-gone", Tuten -> "rootin' Tuten",
Gibbs -> "Gibbs and takes", Kittle -> "a Kittle bit of magic", Achane -> "a chain of events",
Bucky -> "kicked the Bucky", Love -> "Love hurts". (Style examples only; invent your own.)
- Every story headline MUST be a pun on a player's (or manager's) name.
- Every story body needs at least 3 more name puns, each on a different player.
- The couplet should land a name pun too.
- In PART 1, pun on a name in at least half the lines.
- Pun on the sound or spelling as English wordplay only. Never mock a name as foreign,
  its origin or pronunciation, or anything about the person beyond their fantasy points.
Work each side's record, rank move (prev_rank -> rank) and streak into the story.
Poetic rhythm welcome.

Hard rules (both parts):
- Never invent or change scores, players, transactions, FAAB, records, ranks or results.
- Copy every number exactly as written in the facts: no rounding, no new totals or math.
- Only mention players and managers that appear in the facts.
- Report what happened; do not advise anyone what to do.
- Satire targets on-field fantasy performance and league behavior only. Never touch real
  players' or managers' personal lives, family, health, legal matters, appearance, or any
  protected characteristic.
Tone: {tone}"""


def llm(system, user, cfg=CFG):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, None
    body = json.dumps({"model": cfg["model"], "max_tokens": 3000, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.load(r)
    return "".join(c.get("text", "") for c in out["content"]), out["usage"]


def template(f):
    """Zero-LLM fallback. Plain facts, one canned line each."""
    L = [f"🏈 *WEEK {f['week']} RECAP* — {f['league']}", "",
         f"👑 *Top Dog*: {f['high']['manager']} — {f['high']['pts']}",
         f"💀 *Basement*: {f['low']['manager']} — {f['low']['pts']}. Front office declined comment.",
         f"😬 *Heartbreaker*: {f['closest']['winner']} {f['closest']['winner_pts']}–{f['closest']['loser_pts']} {f['closest']['loser']}",
         f"🔨 *Blowout*: {f['blowout']['winner']} over {f['blowout']['loser']} by {f['blowout']['margin']}"]
    for u in f["upsets"]:
        L.append(f"🚨 *Upset*: #{u['winner_prev_rank']} {u['winner']} beat #{u['loser_prev_rank']} {u['loser']}")
    for c in f["bench_crimes"][:1]:
        L.append(f"🚑 *Bench Crime*: {c['manager']} benched {c['benched']} ({c['benched_pts']}) for {c['started']} ({c['started_pts']}).")
    paid = [a for a in f["adds"] if a.get("faab")]
    if paid:
        a = paid[0]
        L.append(f"💰 *FAAB Watch*: {a['manager']} spent ${a['faab']} on {a['player']}.")
    if f["trades"] or f["adds"]:
        L.append("🔄 *League Activity*")
        for t in f["trades"]:
            L.append("• Trade: " + " | ".join(f"{m} gets {', '.join(p)}" for m, p in t["receives"].items()))
        for a in f["adds"][:6]:
            L.append(f"• {a['manager']} added {a['player']}")
    L.append("📈 *Standings*")
    for s in f["standings"]:
        d = s.get("prev_rank", s["rank"]) - s["rank"]
        L.append(f"{s['rank']}. {s['manager']} {s['record']} " + (f"▲{d}" if d > 0 else f"▼{-d}" if d < 0 else "–"))
    return "\n".join(L)


def write(facts, cfg=CFG):
    """Returns (recap, stories_or_empty, source, usage_list)."""
    user = json.dumps(facts, separators=(",", ":"), ensure_ascii=False)
    system = SYSTEM.format(tone=TONES.get(cfg["tone"], TONES["CASUAL"]))
    usage = []
    for attempt in range(2):
        text, u = llm(system, user, cfg)
        if text is None:
            break
        usage.append(u)
        recap, _, stories = text.partition(STORY_SPLIT)
        bad = unsupported_numbers(text, facts)
        if not bad and recap.strip():
            return recap.strip(), stories.strip(), "llm", usage
        print(f"[validator] attempt {attempt + 1} had unsupported numbers: {bad}", file=sys.stderr)
        user += f"\n\nYour last draft used numbers not in the facts: {bad}. Use only numbers from the facts."
    return template(facts), "", "template", usage


# ---------------------------------------------------------------- main
def finalize():
    """Routine mode: Claude wrote the .txt/.stories.md by hand. Check every number
    against the facts, then add the Gazette link. No network. Exit 1 on failure."""
    facts_files = sorted(POSTS.glob("*_recap.facts.json"),
                         key=lambda p: [int(n) for n in re.findall(r"_(\d{4})_w(\d+)_", p.name)[0]])
    if not facts_files:
        sys.exit("No facts file found. Run recap.py first.")
    fj = facts_files[-1]
    facts = json.loads(fj.read_text(encoding="utf-8"))
    txt = fj.with_name(fj.name.replace(".facts.json", ".txt"))
    st = fj.with_name(fj.name.replace(".facts.json", ".stories.md"))
    text = txt.read_text(encoding="utf-8")
    stories = st.read_text(encoding="utf-8") if st.exists() else ""
    link = "📰 Full matchup stories:"
    body = "\n".join(l for l in text.splitlines() if not l.startswith(link))
    bad = unsupported_numbers(body + "\n" + stories, facts)
    if bad:
        sys.exit(f"FAIL {txt.name}: numbers not in facts: {bad}")
    site = os.environ.get("GAZETTE_URL")
    if site and stories and link not in text:
        text = text.rstrip() + f"\n\n{link} {site.rstrip('/')}/week-{facts['week']}.html"
        txt.write_text(text, encoding="utf-8")
    print(f"OK {txt.name}: every number verified" + (" + stories" if stories else ""))


def main(argv):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    if "--finalize" in argv:
        return finalize()
    args = [a for a in argv if not a.startswith("--")]
    lid = CFG["league_id"]
    state = get("/state/nfl")
    week = int(args[0]) if args else state["week"] - 1
    if week < 1:
        sys.exit("No completed week yet.")
    if state["season_type"] == "regular" and week >= state["week"]:
        print(f"WARNING: week {week} may still be in progress (Sleeper is on week {state['week']}).", file=sys.stderr)

    POSTS.mkdir(exist_ok=True)
    key = f"{lid}_{state['league_season']}_w{week}_recap"
    out = POSTS / f"{key}.txt"
    if out.exists() and "--regen" not in argv:       # idempotency: never make a second recap
        print(out.read_text(encoding="utf-8"))
        print(f"\n(already generated: {out.name} — use --regen to rebuild)", file=sys.stderr)
        return

    try:
        raw = fetch(lid, week)
        check_complete(raw, week)
        facts = analyze(raw, players_db(), week)
    except Exception as e:                            # no fabrication on bad data
        with open(POSTS / "errors.log", "a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M')} {key} {e!r}\n")
        sys.exit(f"Sleeper data not ready/usable: {e}. Nothing generated.")

    text, stories, source, usage = write(facts)
    site = os.environ.get("GAZETTE_URL")
    if site and stories:                              # appended after validation, by code
        text += f"\n\n📰 Full matchup stories: {site.rstrip('/')}/week-{week}.html"
    (POSTS / f"{key}.facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding="utf-8")
    if stories:
        (POSTS / f"{key}.stories.md").write_text(stories, encoding="utf-8")
    out.write_text(text, encoding="utf-8")
    tin = sum(u["input_tokens"] for u in usage)
    tout = sum(u["output_tokens"] for u in usage)
    cost = tin / 1e6 * CFG["usd_per_mtok_in"] + tout / 1e6 * CFG["usd_per_mtok_out"]
    with open(POSTS / "usage.csv", "a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M')},{key},{source},{len(usage)},{tin},{tout},{cost:.5f}\n")
    print(text)
    print(f"\n[{source} | calls {len(usage)} | tokens {tin}+{tout} | ~${cost:.4f} | saved {out.name}]", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
