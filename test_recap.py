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
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nMike by 0.4")
            recap.finalize("L")
            self.assertIn("week-2.html", (d / "L_2026_w2_recap.txt").read_text())
            recap.finalize("L")                                   # idempotent: one link only
            self.assertEqual((d / "L_2026_w2_recap.txt").read_text().count("📰"), 1)
            (d / "L_2026_w2_recap.stories.md").write_text("### Hi\nMike by 9.9")
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
