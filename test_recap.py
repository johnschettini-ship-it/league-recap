"""Run: python test_recap.py   (no network needed)"""
import unittest
from recap import analyze, check_complete, unsupported_numbers, template

P = {"q1": {"n": "QB One", "pos": ["QB"]}, "q2": {"n": "QB Two", "pos": ["QB"]},
     "r1": {"n": "RB One", "pos": ["RB"]}, "r2": {"n": "RB Two", "pos": ["RB"]},
     "r3": {"n": "RB Bench", "pos": ["RB"]}, "w1": {"n": "WR One", "pos": ["WR"]},
     "w2": {"n": "WR Two", "pos": ["WR"]}, "w9": {"n": "WR Waiver", "pos": ["WR"]}}


def m(rid, mid, starters, spts, bench=(), bpts=()):
    pp = dict(zip(starters, spts)) | dict(zip(bench, bpts))
    return {"roster_id": rid, "matchup_id": mid, "points": sum(spts), "starters": list(starters),
            "starters_points": list(spts), "players": list(starters) + list(bench), "players_points": pp}


def raw(extra_tx=()):
    return {
        "league": {"name": "Test League", "season": "2026", "roster_positions": ["QB", "RB", "FLEX", "BN"],
                   "settings": {"waiver_type": 2, "waiver_budget": 100, "playoff_week_start": 15}},
        "users": [{"user_id": f"u{i}", "display_name": n} for i, n in enumerate(["John", "Mike", "Steve", "Dave"], 1)],
        "rosters": [{"roster_id": i, "owner_id": f"u{i}", "settings": {"waiver_budget_used": 30 if i == 2 else 0}}
                    for i in range(1, 5)],
        "matchups": {
            1: [m(1, 1, ["q1", "r1", "w1"], [20, 20, 20]), m(2, 1, ["q2", "r2", "w2"], [10, 10, 10]),
                m(3, 2, ["q1", "r1", "w1"], [15, 15, 15]), m(4, 2, ["q2", "r2", "w2"], [14, 14, 14])],
            2: [m(1, 1, ["q1", "r1", "w1"], [30, 30, 30.5]),                      # 90.5 high
                m(4, 1, ["q2", "r2", "w2"], [10, 10, 10], ["r3"], [25]),          # bench crime 15
                m(2, 2, ["q1", "r1", "w9"], [20, 20, 20.4]),                      # 60.4 beats Steve by 0.4
                m(3, 2, ["q2", "r2", "w2"], [20, 20, 20])],
        },
        "transactions": [
            {"type": "waiver", "status": "complete", "adds": {"w9": 2}, "drops": {"w2": 2}, "settings": {"waiver_bid": 30}},
            {"type": "trade", "status": "complete", "adds": {"r1": 3, "r2": 1}, "drops": {"r1": 1, "r2": 3},
             "draft_picks": [{"owner_id": 3, "season": "2027", "round": 2}]},
            {"type": "waiver", "status": "failed", "adds": {"q1": 4}, "settings": {"waiver_bid": 99}},
            *extra_tx],
    }


class T(unittest.TestCase):
    def setUp(self):
        self.f = analyze(raw(), P, 2)

    def test_high_low(self):
        self.assertEqual(self.f["high"], {"manager": "John", "pts": 90.5})
        self.assertEqual(self.f["low"], {"manager": "Dave", "pts": 30.0})

    def test_closest_blowout(self):
        self.assertEqual((self.f["closest"]["winner"], self.f["closest"]["margin"]), ("Mike", 0.4))
        self.assertEqual((self.f["blowout"]["winner"], self.f["blowout"]["margin"]), ("John", 60.5))

    def test_bench_crime(self):
        c = self.f["bench_crimes"][0]
        self.assertEqual((c["manager"], c["benched"], c["gap"]), ("Dave", "RB Bench", 15.0))
        self.assertEqual(self.f["most_bench_pts"]["manager"], "Dave")

    def test_transactions(self):
        self.assertEqual(len(self.f["adds"]), 1)                    # failed claim ignored
        a = self.f["adds"][0]
        self.assertEqual((a["faab"], a["faab_left"], a["pts_this_week"]), (30, 70, 20.4))
        self.assertEqual(self.f["drops"], [{"manager": "Mike", "player": "WR Two"}])
        self.assertEqual(self.f["trades"][0]["receives"]["Steve"], ["RB One", "2027 round 2 pick"])

    def test_standings_and_upset(self):
        st = {s["manager"]: s for s in self.f["standings"]}
        self.assertEqual(st["John"]["record"], "2-0")
        self.assertEqual(st["John"]["streak"], "W2")
        self.assertEqual((st["Mike"]["prev_rank"], st["Mike"]["rank"]), (4, 3))   # Steve holds 2nd on PF tiebreak
        self.assertEqual([u["winner"] for u in self.f["upsets"]], [])          # gap 4 not reached (4 teams)

    def test_matchup_records_and_ranks(self):
        g = next(r for r in self.f["results"] if r["winner"] == "Mike")
        self.assertEqual((g["winner_record"], g["winner_rank"], g["winner_prev_rank"]), ("1-1", 3, 4))
        self.assertEqual((g["loser_record"], g["loser_rank"], g["loser_streak"]), ("1-1", 2, "L1"))

    def test_finalize_checks_and_links(self):
        import recap, tempfile, json, os, pathlib
        d = pathlib.Path(tempfile.mkdtemp())
        orig, recap.POSTS = recap.POSTS, d
        os.environ["GAZETTE_URL"] = "https://x.github.io/league-recap/"
        try:
            (d / "L_2026_w2_recap.facts.json").write_text(json.dumps(self.f))
            (d / "L_2026_w2_recap.txt").write_text("John 90.5")
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nMike by 0.4\nPUNS: none yet")
            recap.finalize("L")
            self.assertIn("week-2.html", (d / "L_2026_w2_recap.txt").read_text())
            recap.finalize("L")                                   # idempotent: one link only
            self.assertEqual((d / "L_2026_w2_recap.txt").read_text().count("📰"), 1)
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nMike by 9.9\nPUNS: none yet")
            with self.assertRaises(SystemExit):
                recap.finalize("L")
        finally:
            recap.POSTS = orig
            del os.environ["GAZETTE_URL"]

    def test_aliases_replace_names_everywhere(self):
        import json
        f = analyze(raw(), P, 2, aliases={"Mike": "The Nickname"})
        blob = json.dumps(f)
        self.assertNotIn('"Mike"', blob)
        self.assertIn("The Nickname", blob)

    def test_repeated_pun_names(self):
        from recap import repeated_pun_names as rp
        self.assertEqual(rp('Drake "London Bridges" London caught 28.4'), ['Drake "London Bridges" London'])
        self.assertEqual(rp('Brock “Purdy Please” Purdy'), ['Brock "Purdy Please" Purdy'])
        self.assertEqual(rp('TreVeyon "Muppet Jim" Henderson and Drake London Bridges'), [])
        self.assertEqual(rp('Folding Table Champ "Bagel" Katz'), [])

    def test_power_rankings_all_play(self):
        pr = {p["manager"]: p for p in self.f["power_rankings"]}
        self.assertEqual([p["manager"] for p in self.f["power_rankings"]], ["John", "Steve", "Mike", "Dave"])
        self.assertEqual((pr["John"]["all_play"], pr["Mike"]["all_play"], pr["Dave"]["all_play"]), ("6-0", "2-4", "1-5"))
        self.assertEqual((pr["Mike"]["luck"], pr["Dave"]["luck"]), (0.3, -0.3))

    def test_power_blend_rewards_recent_form(self):
        f = self.f["power_rankings"]
        self.assertTrue(all("power_score" in p and "last3_all_play" in p for p in f))
        self.assertEqual(f[0]["power_score"], 100.0)                 # perfect true record, last 3 and points
        self.assertTrue(f[0]["power_score"] > f[1]["power_score"] > f[3]["power_score"])

    def test_awards_and_lore(self):
        a, l = self.f["awards"], self.f["lore"]
        self.assertEqual((a["boom"]["player"], a["boom"]["pts"]), ("WR One", 30.5))
        self.assertEqual(a["bench_crime"]["manager"], "Dave")
        self.assertEqual((a["big_spender"]["manager"], a["big_spender"]["faab"]), ("Mike", 30))
        self.assertEqual((l["season_high"]["manager"], l["season_high"]["week"]), ("John", 2))
        self.assertEqual((l["hot_streak"]["manager"], l["cold_streak"]["manager"]), ("John", "Dave"))

    def test_next_week_card_top2_and_bottom1(self):
        base = raw()
        base["users"] += [{"user_id": "u5", "display_name": "Evan"}, {"user_id": "u6", "display_name": "Finn"}]
        base["rosters"] += [{"roster_id": 5, "owner_id": "u5", "settings": {}}, {"roster_id": 6, "owner_id": "u6", "settings": {}}]
        for w, (p5, p6) in {1: (12, 4), 2: (11, 3)}.items():                 # Evan beats Finn both weeks: Evan 2-0 (rank 2), Finn 0-2 (rank 6)
            base["matchups"][w] += [m(5, 3, ["q1", "r1", "w1"], [p5, p5, p5]), m(6, 3, ["q2", "r2", "w2"], [p6, p6, p6])]
        base["next"] = [{"roster_id": a, "matchup_id": i} for i, pr in enumerate([(1, 3), (2, 6), (4, 5)], 1) for a in pr]
        card = analyze(base, P, 2)["next_week_card"]
        self.assertEqual([c["billing"] for c in card], ["Main Event", "Co-Main Event", "Basement Bowl"])
        self.assertEqual([(c["a"]["manager"], c["b"]["manager"]) for c in card],
                         [("John", "Steve"), ("Evan", "Dave"), ("Mike", "Finn")])   # ranks 1v3, 2v5, then 4v6
        self.assertEqual([(c["a"]["rank"], c["b"]["rank"]) for c in card], [(1, 3), (2, 5), (4, 6)])
        self.assertEqual(card[0]["week"], 3)
        two = raw(); two["next"] = [{"roster_id": a, "matchup_id": i} for i, pr in enumerate([(1, 2), (3, 4)], 1) for a in pr]
        c2 = analyze(two, P, 2)["next_week_card"]
        self.assertEqual([c["billing"] for c in c2], ["Main Event", "Co-Main Event"])     # too few games for a third
        self.assertEqual(c2[0]["head_to_head"], [{"week": 1, "winner": "John", "score": "60.0-30.0"}])
        self.assertIsNone(self.f["next_week_card"])                                        # no pairings published

    def test_pun_names_never_repeat_across_weeks(self):
        import recap, tempfile, json, pathlib
        d = pathlib.Path(tempfile.mkdtemp())
        orig, recap.POSTS = recap.POSTS, d
        try:
            (d / "L_2026_w1_recap.stories.md").write_text('### Hi\nDrake "London Bridges" London\nPUNS: Brock Purdy Please | Tee Shirt Higgins\nEPITHETS: John the Unbeaten')
            self.assertEqual(recap.used_puns("L", 2), ["Brock Purdy Please", "John the Unbeaten", "London Bridges", "Tee Shirt Higgins"])
            self.assertEqual(recap.used_puns("L", 1), [])                    # only earlier weeks count
            f = dict(self.f); f["week"] = 2
            (d / "L_2026_w2_recap.facts.json").write_text(json.dumps(f))
            (d / "L_2026_w2_recap.txt").write_text("John 90.5")
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nBrock Purdy Please by 0.4\nPUNS: Brock Purdy Please")
            with self.assertRaises(SystemExit):                              # reused -> blocked
                recap.finalize("L")
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nPurdy Pleased As Punch by 0.4")
            with self.assertRaises(SystemExit):                              # missing PUNS line -> blocked
                recap.finalize("L")
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nPurdy Pleased As Punch by 0.4\nPUNS: Purdy Pleased As Punch")
            recap.finalize("L")                                              # fresh -> passes
        finally:
            recap.POSTS = orig

    def test_comic_changes_every_week(self):
        import comic, recap, tempfile, json, pathlib
        looks = [comic.look(w) for w in range(1, 7)]
        self.assertTrue(all(looks[i][0] != looks[i + 1][0] for i in range(5)))       # new costume weekly
        self.assertNotEqual(comic.rivet("reading", 3, 1), comic.rivet("reading", 4, 1))
        d = pathlib.Path(tempfile.mkdtemp())
        orig, recap.POSTS = recap.POSTS, d
        try:
            (d / "L_2026_w1_recap.stories.md").write_text("STRIP: Bench Press\n1. reading: a\n2. bench: b\n3. facepalm: c\nPUNS: x")
            self.assertEqual(recap.last_strip_poses("L", 2), ["reading", "bench", "facepalm"])
            self.assertIn("Bench Press", recap.used_puns("L", 2))
            f = dict(self.f); f["week"] = 2
            (d / "L_2026_w2_recap.facts.json").write_text(json.dumps(f))
            (d / "L_2026_w2_recap.txt").write_text("John 90.5")
            (d / "L_2026_w2_recap.stories.md").write_text("STRIP: Fresh Gag\n1. reading: a\n2. bench: b\n3. facepalm: c\nPUNS: x")
            with self.assertRaises(SystemExit):                                     # same poses -> blocked
                recap.finalize("L")
            (d / "L_2026_w2_recap.stories.md").write_text("STRIP: Bench Press\n1. money: a\n2. sweat: b\n3. trophy: c\nPUNS: x")
            with self.assertRaises(SystemExit):                                     # reused title -> blocked
                recap.finalize("L")
            (d / "L_2026_w2_recap.stories.md").write_text("STRIP: Fresh Gag\n1. money: a\n2. sweat: b\n3. trophy: c\nPUNS: x")
            recap.finalize("L")
        finally:
            recap.POSTS = orig

    def test_theme_calendar(self):
        import theme, datetime as dt
        k = lambda m, d: theme.season(dt.date(2026, m, d))[0]
        self.assertEqual([k(9, 30), k(10, 21), k(10, 28), k(11, 1), k(11, 11), k(11, 25), k(12, 9), k(12, 23), k(12, 30)],
                         ["regular", "regular", "halloween", "halloween", "fall", "thanksgiving", "snow", "christmas", "newyear"])
        self.assertEqual(theme.season(dt.date(2027, 1, 6))[0], "newyear")                 # wraps the year
        self.assertEqual(theme.edition_date({"season": "2026", "week": 3}).isoformat(), "2026-09-30")

    def test_playoff_phases(self):
        from theme import playoff_phase as pp
        self.assertIsNone(pp(10, 15, 6))
        self.assertEqual((pp(11, 15, 6)["phase"], pp(11, 15, 6)["weeks_left"]), ("race", 3))
        self.assertEqual(pp(14, 15, 6)["label"], "Playoff Field Set")
        self.assertEqual((pp(15, 15, 6)["round"], pp(16, 15, 6)["round"]), ("Quarterfinals", "Semifinals"))
        self.assertEqual(pp(17, 15, 6)["phase"], "champion")                             # 6 teams = 3 rounds
        self.assertEqual(pp(16, 15, 4)["phase"], "champion")                             # 4 teams = 2 rounds

    def test_playoff_week_eliminated_teams_ok(self):
        r = raw()
        r["league"]["settings"]["playoff_week_start"] = 2
        r["league"]["settings"]["playoff_teams"] = 2
        r["matchups"][2] = [m(1, 1, ["q1", "r1", "w1"], [30, 30, 30.5]), m(2, 1, ["q1", "r1", "w9"], [20, 20, 20.4]),
                            {"roster_id": 3, "matchup_id": None, "points": 0}, {"roster_id": 4, "matchup_id": None, "points": 0}]
        r["bracket"] = [{"r": 1, "m": 1, "t1": 1, "t2": 2, "w": 1, "l": 2, "p": 1}]
        check_complete(r, 2)                                                           # no error for byes/eliminated
        f = analyze(r, P, 2)
        st = {s["manager"]: s["record"] for s in f["standings"]}
        self.assertEqual(st["John"], "1-0")                                            # playoff game not in record
        self.assertEqual(f["champion"], {"manager": "John", "runner_up": "Mike"})
        self.assertEqual(f["bracket"][0]["winner"], "John")

    def test_incomplete_data_refused(self):
        r = raw()
        r["matchups"][2] = r["matchups"][2][:3]
        with self.assertRaises(ValueError):
            check_complete(r, 2)

    def test_validator(self):
        self.assertEqual(unsupported_numbers("John drops 90.5, wins by 60.5", self.f), [])
        self.assertEqual(unsupported_numbers("John drops 91.2", self.f), ["91.2"])
        self.assertEqual(unsupported_numbers("Mike paid $30", self.f), [])

    def test_template_is_self_consistent(self):
        self.assertEqual(unsupported_numbers(template(self.f), self.f), [])


    def test_lineup_story_material(self):
        g = next(r for r in self.f["results"] if r["winner"] == "Mike")
        self.assertEqual(g["winner_lineup"]["stars"][0], {"player": "WR Waiver", "slot": "FLEX", "pts": 20.4})
        d = next(r for r in self.f["results"] if r["loser"] == "Dave")
        self.assertEqual(d["loser_bench_crime"]["benched"], "RB Bench")

    def test_write_splits_and_validates(self):
        import recap
        good = "recap John 90.5\n===STORIES===\n### Title\nJohn by 60.5"
        bad = "recap John 91\n===STORIES===\n### T\nx"
        for replies, want in (([good], ("llm", True)), ([bad, bad], ("template", False))):
            it = iter(replies)
            orig = recap.llm
            recap.llm = lambda *a, **k: (next(it), {"input_tokens": 1, "output_tokens": 1})
            try:
                r, st, src, _ = recap.write(self.f)
            finally:
                recap.llm = orig
            self.assertEqual((src, bool(st)), want)


if __name__ == "__main__":
    unittest.main()
