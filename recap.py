#!/usr/bin/env python3
"""Sleeper league recap bot. Python 3.9+, standard library only.

  python recap.py            recap last completed week
  python recap.py 3          recap week 3
  python recap.py 3 --regen  ignore saved post and rebuild

Layer 1 (analyze) = deterministic facts. Layer 2 (write) = one LLM call.
Every number in the LLM text is checked against the facts; if any is
unsupported it retries once, then falls back to a no-LLM template.
"""
import json, math, os, re, sys, time, pathlib, urllib.request, datetime
import theme

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
        "next": next_pairings(lid, week + 1),
        "bracket": bracket(lid),
    }


def bracket(lid):
    try:
        return get(f"/league/{lid}/winners_bracket") or []
    except Exception:                                   # not set until the regular season ends
        return []


def next_pairings(lid, week):
    try:
        return get(f"/league/{lid}/matchups/{week}") or []
    except Exception:                                   # season over / not published yet
        return []


# ---------------------------------------------------------------- Layer 1
def r2(x):
    return round(float(x or 0), 2)


def check_complete(raw, week):
    """Refuse to recap partial data. Raises ValueError."""
    rids = {r["roster_id"] for r in raw["rosters"]}
    ps = (raw["league"].get("settings") or {}).get("playoff_week_start") or 99
    for w in range(1, week + 1):
        seen = {m["roster_id"] for m in raw["matchups"].get(w) or [] if m.get("matchup_id") is not None}
        if w >= ps:                                     # playoffs: eliminated teams have no game
            if not any(m.get("points") for m in raw["matchups"].get(w) or [] if m.get("matchup_id") is not None):
                raise ValueError(f"week {w}: no playoff points yet")
            continue
        if seen != rids:
            raise ValueError(f"week {w}: matchups cover {len(seen)} of {len(rids)} rosters")
        if all(not m.get("points") for m in raw["matchups"][w]):
            raise ValueError(f"week {w}: no points yet")


def analyze(raw, P, week, cfg=CFG, aliases=None):
    lg = raw["league"]
    settings = lg.get("settings") or {}
    aliases = aliases or {}                             # privacy: real-looking usernames -> nicknames
    uname = {u["user_id"]: aliases.get(u.get("display_name"), u.get("display_name") or u["user_id"])
             for u in raw["users"]}
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

    ps = settings.get("playoff_week_start") or 99
    reg = lambda upto: max(0, min(upto, ps - 1))        # records/power count regular season only
    now, before = table(reg(week)), (table(reg(week - 1)) if week > 1 and week <= ps else None)

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

    # ---- power rankings: all-play record (vs every team, every week) ----
    def allplay(upto):
        ap = {rid: [0, 0] for rid in owner}
        for w in range(1, upto + 1):
            pts = {m["roster_id"]: m["points"] or 0 for m in raw["matchups"][w] if m.get("matchup_id") is not None}
            for rid, p in pts.items():
                ap[rid][0] += sum(p > q for o, q in pts.items() if o != rid)
                ap[rid][1] += sum(p < q for o, q in pts.items() if o != rid)
        order = sorted(ap, key=lambda i: (-(ap[i][0] / max(1, sum(ap[i]))), -now[i]["pf"]))
        return ap, {rid: n for n, rid in enumerate(order, 1)}
    POWER_W = {"true_record": 0.60, "last3": 0.25, "points": 0.15}   # blend weights

    def power_order(upto):
        """Blend: season all-play % (60%) + last-3-weeks all-play % (25%) + points vs leader (15%)."""
        ap_all, _ = allplay(upto)
        lo = max(1, upto - 2)
        ap3 = {rid: [0, 0] for rid in owner}
        pf = {rid: 0.0 for rid in owner}
        for w in range(1, upto + 1):
            pts = {m["roster_id"]: m["points"] or 0 for m in raw["matchups"][w] if m.get("matchup_id") is not None}
            for rid, p in pts.items():
                pf[rid] += p
                if w >= lo:
                    ap3[rid][0] += sum(p > q for o, q in pts.items() if o != rid)
                    ap3[rid][1] += sum(p < q for o, q in pts.items() if o != rid)
        top = max(pf.values()) or 1
        pct = lambda x: x[0] / max(1, sum(x))
        score = {rid: POWER_W["true_record"] * pct(ap_all[rid]) + POWER_W["last3"] * pct(ap3[rid])
                 + POWER_W["points"] * pf[rid] / top for rid in owner}
        order = sorted(owner, key=lambda i: (-score[i], -pf[i]))
        return ap_all, ap3, score, {rid: n for n, rid in enumerate(order, 1)}

    ap, ap3, pscore, prank = power_order(reg(week))
    prev_prank = power_order(reg(week - 1))[3] if 1 < week <= ps else {}
    pa = {rid: 0.0 for rid in owner}
    for w in range(1, reg(week) + 1):
        for a, b in games(w):
            pa[a["roster_id"]] += b["points"] or 0
            pa[b["roster_id"]] += a["points"] or 0
    power = []
    for rid in sorted(owner, key=lambda i: prank[i]):
        gp = now[rid]["w"] + now[rid]["l"] + now[rid]["t"]
        exp = ap[rid][0] / max(1, sum(ap[rid])) * gp
        row = {"power_rank": prank[rid], "manager": owner[rid], "record": st_by[owner[rid]]["record"],
               "all_play": f"{ap[rid][0]}-{ap[rid][1]}", "last3_all_play": f"{ap3[rid][0]}-{ap3[rid][1]}",
               "power_score": round(pscore[rid] * 100, 1), "pf": r2(now[rid]["pf"]), "pa": r2(pa[rid]),
               "luck": round(now[rid]["w"] - exp, 1)}
        if rid in prev_prank:
            row["prev_power_rank"] = prev_prank[rid]
        power.append(row)

    # ---- next week's card: the top 2 matchups and the bottom one, by standings rank ----
    pairs = {}
    for m in raw.get("next") or []:
        if m.get("matchup_id") is not None and m["roster_id"] in owner:
            pairs.setdefault(m["matchup_id"], []).append(m["roster_id"])
    pairs = [sorted(p, key=lambda rid: now[rid]["rank"]) for p in pairs.values() if len(p) == 2]
    rk = lambda p: now[p[0]]["rank"] + now[p[1]]["rank"]              # low = two good teams
    gap = lambda p: now[p[1]]["rank"] - now[p[0]]["rank"]             # low = evenly matched
    side = lambda rid: {"manager": owner[rid], "record": st_by[owner[rid]]["record"], "rank": now[rid]["rank"],
                        "streak": st_by[owner[rid]]["streak"], "power_rank": prank[rid], "pf": r2(now[rid]["pf"])}

    def h2h(a, b):
        out = []
        for w in range(1, week + 1):
            for x, y in games(w):
                if {x["roster_id"], y["roster_id"]} == {a, b}:
                    win, lose = (x, y) if x["points"] >= y["points"] else (y, x)
                    out.append({"week": w, "winner": owner[win["roster_id"]], "score": f"{r2(win['points'])}-{r2(lose['points'])}"})
        return out
    # odds: each team's scoring average (pulled toward the league average while the sample is
    # small) against how much scores swing week to week. Computed here, never by the writer.
    hist = {rid: [] for rid in owner}
    for w in range(1, reg(week) + 1):
        for m in raw["matchups"][w]:
            if m.get("matchup_id") is not None and m["roster_id"] in hist:
                hist[m["roster_id"]].append(m["points"] or 0)
    avg = {rid: sum(v) / max(1, len(v)) for rid, v in hist.items()}
    lg_avg = sum(avg.values()) / max(1, len(avg))
    dev = [x - avg[rid] for rid, v in hist.items() for x in v]
    dof = len(dev) - len(hist)
    swing = max(10.0, (sum(d * d for d in dev) / dof) ** 0.5) if dof > 0 else 25.0
    trust = reg(week) / (reg(week) + 3)                              # 4 weeks in: 57% team, 43% league
    proj = {rid: lg_avg + trust * (avg[rid] - lg_avg) for rid in owner}

    def odds(a, b):
        diff = proj[a] - proj[b]
        p = min(0.95, max(0.05, 0.5 * (1 + math.erf(diff / (2 * swing)))))
        fav, dog, pf = (a, b, p) if p >= 0.5 else (b, a, 1 - p)
        pct = round(pf * 100)
        return {"favorite": owner[fav], "favorite_pct": pct, "underdog": owner[dog], "underdog_pct": 100 - pct,
                "line": round(abs(diff) * 2) / 2}
    best = sorted(pairs, key=lambda p: rk(p) + 0.5 * gap(p))
    billed = list(zip(("Main Event", "Co-Main Event"), best))
    if best[2:]:
        billed.append(("Basement Bowl", max(best[2:], key=lambda p: (rk(p), -gap(p)))))
    card = [{"billing": bill, "week": week + 1, "a": side(x), "b": side(y), "head_to_head": h2h(x, y), "odds": odds(x, y)}
            for bill, (x, y) in billed] or None
    on_card = [p for _, p in billed]
    others = [{"week": week + 1, "a": side(x), "b": side(y), "odds": odds(x, y)}
              for x, y in best if [x, y] not in on_card] or None

    # ---- weekly awards ----
    awards = {"boom": booms[0] if booms else None, "dud": busts[0] if busts else None,
              "bench_crime": crimes[0] if crimes else None}
    paid = [x for x in adds if x.get("faab")]
    if paid:
        awards["big_spender"] = paid[0]
    elif adds:
        cnt = {}
        for x in adds:
            cnt[x["manager"]] = cnt.get(x["manager"], 0) + 1
        top = max(cnt, key=cnt.get)
        awards["most_active"] = {"manager": top, "moves": cnt[top]}

    # ---- league lore (season to date) ----
    weekly = [(m["points"] or 0, w, m["roster_id"]) for w in range(1, week + 1)
              for m in raw["matchups"][w] if m.get("matchup_id") is not None]
    hi, lo = max(weekly), min(weekly)
    streak_n = lambda s: int(s[1:]) if s[1:].isdigit() else 0
    wst = max(standings, key=lambda s: (s["streak"][:1] == "W", streak_n(s["streak"])))
    lst = max(standings, key=lambda s: (s["streak"][:1] == "L", streak_n(s["streak"])))
    lore = {"season_high": {"manager": owner[hi[2]], "pts": r2(hi[0]), "week": hi[1]},
            "season_low": {"manager": owner[lo[2]], "pts": r2(lo[0]), "week": lo[1]},
            "luckiest": max(power, key=lambda p: p["luck"]), "unluckiest": min(power, key=lambda p: p["luck"]),
            "schedule_victim": max(power, key=lambda p: p["pa"])}
    if wst["streak"].startswith("W") and streak_n(wst["streak"]) >= 2:
        lore["hot_streak"] = {"manager": wst["manager"], "streak": wst["streak"]}
    if lst["streak"].startswith("L") and streak_n(lst["streak"]) >= 2:
        lore["cold_streak"] = {"manager": lst["manager"], "streak": lst["streak"]}

    # ---- playoffs: race, bracket, champion ----
    pteams = settings.get("playoff_teams") or 6
    phase = theme.playoff_phase(week, settings.get("playoff_week_start"), pteams)
    race = None
    if phase and phase["phase"] == "race":
        race = {"weeks_left": phase["weeks_left"], "playoff_teams": pteams,
                "in": [s["manager"] for s in standings[:pteams]],
                "bubble": [{"manager": s["manager"], "record": s["record"], "rank": s["rank"]}
                           for s in standings[max(0, pteams - 2): pteams + 2]]}
    nm = lambda x: owner.get(x) if isinstance(x, int) else None
    bracket_rows = [{"round": b.get("r"), "a": nm(b.get("t1")), "b": nm(b.get("t2")), "winner": nm(b.get("w")),
                     "place": b.get("p")} for b in raw.get("bracket") or []]
    final = next((b for b in bracket_rows if b["place"] == 1 and b["winner"]), None)
    champion = ({"manager": final["winner"], "runner_up": final["b"] if final["winner"] == final["a"] else final["a"]}
                if final and phase and phase["phase"] in ("champion", "offseason") else None)

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
        "power_rankings": power, "next_week_card": card, "next_week_others": others, "awards": awards, "lore": lore,
        "playoff_teams": pteams, "playoff_race": race, "bracket": bracket_rows or None, "champion": champion,
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


QUOTED_NICK = re.compile(r"\b([A-Z][\w'.-]*)\s+[\"“‘]([^\"”’\n]+)[\"”’]\s+([A-Z][\w'.-]*)")


def repeated_pun_names(text):
    """Drake "London Bridges" London -> flagged. Marc "Bagel" Katz -> fine."""
    out = []
    for first, nick, last in QUOTED_NICK.findall(text):
        words = set(re.findall(r"[a-z']+", nick.lower()))
        if first.lower() in words or last.lower() in words:
            out.append(f'{first} "{nick}" {last}')
    return out


def unsupported_numbers(text, facts):
    ok = allowed_numbers(facts)
    return sorted({n for n in NUM.findall(text) if norm(n) not in ok})


# ---------------------------------------------------------------- Layer 2
TONES = {"CLEAN": "Light sports-commentary humor. No insults.",
         "CASUAL": "Friendly group-chat trash talk, slightly sarcastic.",
         "SPICY": "Aggressive fantasy roasting, but only about fantasy performance and league behavior."}

STORY_SPLIT = "===STORIES==="

SYSTEM = """You are the beat writer for a fantasy football league's weekly newspaper.
Using ONLY the JSON facts given, write TWO things separated by a line containing exactly
""" + STORY_SPLIT + """

VOICE (everything you write)
Write like a sharp newspaper sports columnist: plain, confident sentences and dry humor.
- Lead with what happened, then why it happened, then what it means. One idea per sentence.
- Make it flow: each sentence follows from the one before it (because, so, but, meanwhile).
  A story is an argument about why the game went the way it did, not a list of stat lines.
- Use a number only when it explains the result: at most 6 numbers per story, with a
  player's points in parentheses after his name.
- No verse, no rhymes, no mock-epic or theatrical narration ("O Romeo", "Stop the presses",
  "Pity the...", "Behold"), no archaic words, no stage directions.
- Humor is short and comes from the facts: at most one joke per paragraph, and never at the
  cost of the reader understanding what happened.
- The page prints each team's record, rank and streak beside the story, so don't recite
  them. Mention the standings only when that IS the story (first loss, still winless,
  jumped four spots).

NAME PUNS (a few per story, and only where the sentence still reads straight through)
- Every story headline is a pun on a player's or a team's name.
- Players: in a story body, give a pun-name to one to three players, on FIRST mention only;
  after that he is just his last name. Everyone else goes by his real name. Never put two
  pun-names in one sentence, and never open a paragraph with one.
- Teams: the manager names in the facts are the team names. At most once per story, and once
  or twice across LEAD and POWER, play on a team's name with a verb or short aside that fits
  the sentence ("Dumpsterfire007 burned through another week", "nobody could scrape Barnacle
  Boys off the bottom"; examples only, invent your own). Always print the team name itself unchanged, so readers can find
  their team, and add no titles ("dookkk the Great"). Skip any team name that is political
  or about a real person.
- Flow test: delete the pun and reread the sentence. It must still say who did what. If the
  pun needs a setup sentence, an explanation or a detour, cut the pun and keep the sentence.
- A pun-name fuses the joke into the name and keeps the real last name so readers know who
  it is: "Brock Purdy Please", "Drake London Bridges", "Chuba Hubbard Times", "Tee Shirt
  Higgins", "Derrick KING Henry". (Style examples only; invent your own.) Never repeat a
  word of the real name: BAD Drake "London Bridges" London; GOOD Drake London Bridges.
- Never reuse anything listed in used_pun_names (earlier weeks of this league).
- English wordplay on sound or spelling only. Never mock a name as foreign, its origin or
  pronunciation, or anything about the person beyond his fantasy points.

PART 1 — mobile recap for the group chat. 150-350 words. *bold* headers, emoji, short lines.
Sections, in order (skip any with no data): 🏈 WEEK N RECAP, 👑 Top Dog, 💀 Basement,
😬 Heartbreaker (closest), 🔨 Blowout, 🚨 Upset, 🚑 Bench Crime, 💥 Booms & Busts,
💰 FAAB Watch, 🔄 League Activity, 📈 Standings, 🔮 Next Week, 🗣️ Commissioner's Desk.
📈 Standings = every team, one line each, in rank order:
<rank>. <manager> <record> <▲n / ▼n / – from prev_rank> <streak if 2+>
then one line on the top and bottom of the table.
🔮 Next Week = one line on the Main Event in next_week_card, with its odds.
🗣️ Commissioner's Desk = one closing joke drawn from the facts.

PART 2 — the newspaper. Write these blocks in exactly this order.

BANNER: <front-page headline, a name pun, max 8 words>

LEAD:
<120-180 words in 2-3 short paragraphs. Open with the week's biggest story, say what it did
to the standings, then point to two or three of the games below without giving away how the
stories end.>

PREVIEWS:
<Skip if next_week_card is null. One numbered entry per game, in next_week_card order.>
1. <35-55 words: why this game matters, then the odds in plain words using that game's
   "odds" (favorite, favorite_pct, line). Add head_to_head if there is one. State the odds;
   don't predict beyond them.>
2. <same for the Co-Main Event>
3. <the Basement Bowl, the two lowest-ranked teams: keep it light; somebody has to win>

POWER:
<One line per team, in power_rankings order.>
<power_rank>. <manager> — <one dry line, max 15 words, drawn from their facts. all_play versus
record = luck; last3_all_play = current form. Call all_play the "true record".>

Then one story per game in "results", smallest margin first. Each story has exactly this shape:
### <one fitting emoji> <headline, a name pun, max 32 characters>
<Paragraph 1, 40-65 words: who won and why, built on winner_lineup.>

<Paragraph 2, 40-65 words: what went wrong for the loser (loser_lineup, any bench crime),
and what the result means.>
🎤 *Kicker:* <one dry closing line>
The page adds the scorebox, so don't restate the final score line. Icons in the body: at most
🚑 (bench crime), 💸 (FAAB pickup), 🔄 (trade).

STRIP: <comic strip title, a pun>
1. <pose>: <line for Rivet, the Gazette's robot reporter, max 14 words>
2. <pose>: <line>
3. <pose>: <punchline>
Rivet reacts to the week's biggest moment. pose is one of: reading, celebrate, shrug,
facepalm, sweat, bench, trophy, money (bench = bench crime, money = FAAB, trophy = top dog).
Never reuse a strip title from used_pun_names or repeat last_strip_poses in the same order.

PUNS: <every pun-name and team-name play you used this week, exactly as written, separated
by " | " on this one line. For a team-name play log the joke phrase, never the bare team name.>

HARD RULES (both parts)
- Never invent or change scores, players, transactions, FAAB, records, ranks, odds or results.
- Copy every number exactly as written in the facts: no rounding, no new totals or math.
- Only mention players and managers that appear in the facts.
- Report what happened; do not advise anyone what to do.
- Humor targets on-field fantasy performance and league behavior only. Never touch real
  players' or managers' personal lives, family, health, legal matters, appearance, or any
  protected characteristic. A player who scored 0.0 simply scored 0.0; don't guess why.
Edition theme (facts.edition): weave it in lightly: the banner, a joke or two and the comic
strip. Halloween = spooky, Thanksgiving = feast, winter/Christmas/New Year = cold, gifts,
resolutions. Playoff race (playoff_race): who is in, who is on the bubble, weeks left.
Playoffs (bracket): the stakes are elimination. Championship (champion): crown the champion
and go easy on the runner-up.
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
def league_cfg(lid):
    """This league's entry in leagues.json: path ('' = site root) and site URL."""
    f = HERE / "leagues.json"
    for lg in json.loads(f.read_text(encoding="utf-8")) if f.exists() else []:
        if lg["id"] == lid:
            return lg
    return {}


def page_url(site, lid, week):
    lg = league_cfg(lid)
    site, p = lg.get("site") or site, lg.get("path", "")
    return f"{site.rstrip('/')}/{p + '/' if p else ''}week-{week}.html"


PUN_LINE = re.compile(r"^(?:PUNS|EPITHETS):\s*(.*)$", re.M)
STRIP_TITLE = re.compile(r"^STRIP:\s*(.+)$", re.M)
STRIP_POSE = re.compile(r"^\s*[123][.)]\s*([a-z]+)\s*[:—–-]", re.M)


def strip_poses(md):
    m = re.search(r"^STRIP:.*?(?=^(?:PUNS|EPITHETS|###)|\Z)", md, re.M | re.S)
    return [p.lower() for p in STRIP_POSE.findall(m.group(0))][:3] if m else []


def last_strip_poses(lid, week):
    p = next(iter(POSTS.glob(f"{lid}_*_w{week - 1}_recap.stories.md")), None)
    return strip_poses(p.read_text(encoding="utf-8")) if p else []


def used_puns(lid, week):
    """Pun-names/epithets from this league's earlier weeks (logged lines + quoted nicknames)."""
    seen = set()
    for p in POSTS.glob(f"{lid}_*_recap.stories.md"):
        m = re.search(r"_w(\d+)_recap", p.name)
        if not m or int(m.group(1)) >= week:
            continue
        t = p.read_text(encoding="utf-8")
        seen.update(x.strip(' *"“”') for x in STRIP_TITLE.findall(t) if len(x.strip()) >= 6)
        for line in PUN_LINE.findall(t):
            seen.update(x.strip(" *") for x in line.split("|") if len(x.strip(" *")) >= 6)
        seen.update(n.strip() for _, n, _ in QUOTED_NICK.findall(t) if len(n.strip()) >= 6)
    return sorted(seen, key=str.lower)


def reused_puns(text, previous):
    body = PUN_LINE.sub("", text)
    return [p for p in previous if re.search(r"(?<![\w'])" + re.escape(p) + r"(?![\w'])", body, re.I)]


def finalize(lid):
    """Routine mode: Claude wrote the .txt/.stories.md by hand. Check every number
    against the facts, then add the Gazette link. No network. Exit 1 on failure."""
    facts_files = sorted(POSTS.glob(f"{lid}_*_recap.facts.json"),
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
    rep = repeated_pun_names(body + "\n" + stories)
    if rep:
        sys.exit(f"FAIL {txt.name}: pun-names repeat the real name, fuse them instead: {rep}")
    if stories and not re.search(r"^PUNS:", stories, re.M):
        sys.exit(f"FAIL {txt.name}: stories must end with the PUNS: line")
    teams = {s["manager"].lower() for s in facts["standings"]}
    bare = [x.strip() for line in PUN_LINE.findall(stories) for x in line.split("|") if x.strip().lower() in teams]
    if bare:                                          # a logged team name would block that team's name next week
        sys.exit(f"FAIL {txt.name}: PUNS line lists a bare team name {bare}; log the joke phrase instead")
    poses, before = strip_poses(stories), last_strip_poses(lid, facts["week"])
    if poses and poses == before:
        sys.exit(f"FAIL {txt.name}: comic strip repeats last week's poses {poses}; change the gag")
    again = reused_puns(body + "\n" + stories, used_puns(lid, facts["week"]))
    if again:
        sys.exit(f"FAIL {txt.name}: pun-names/epithets already used in earlier weeks, invent new ones: {again}")
    site = league_cfg(lid).get("site") or os.environ.get("GAZETTE_URL")
    if site and stories and link not in text:
        text = text.rstrip() + f"\n\n{link} {page_url(site, lid, facts['week'])}"
        txt.write_text(text, encoding="utf-8")
    print(f"OK {txt.name}: every number verified" + (" + stories" if stories else ""))


def main(argv):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    lid = next((a.split("=", 1)[1] for a in argv if a.startswith("--league=")), CFG["league_id"])
    if "--finalize" in argv:
        return finalize(lid)
    args = [a for a in argv if not a.startswith("--")]
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
        facts = analyze(raw, players_db(), week, aliases=league_cfg(lid).get("aliases"))
        lastp = last_strip_poses(lid, week)
        if lastp:
            facts["last_strip_poses"] = lastp
        facts["edition_date"] = datetime.date.today().isoformat()
        ed = theme.edition(facts)
        facts["edition"] = {"theme": ed["key"], "label": ed["label"], "playoff": ed["playoff"]}
        prior = used_puns(lid, week)
        if prior:
            facts["used_pun_names"] = prior                # the writer must not repeat these
        if league_cfg(lid).get("display_name"):        # masthead override from leagues.json
            facts["league"] = league_cfg(lid)["display_name"]
    except Exception as e:                            # no fabrication on bad data
        with open(POSTS / "errors.log", "a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M')} {key} {e!r}\n")
        sys.exit(f"Sleeper data not ready/usable: {e}. Nothing generated.")

    text, stories, source, usage = write(facts)
    site = league_cfg(lid).get("site") or os.environ.get("GAZETTE_URL")
    if site and stories:                              # appended after validation, by code
        text += f"\n\n📰 Full matchup stories: {page_url(site, lid, week)}"
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
