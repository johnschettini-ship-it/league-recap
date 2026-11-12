# Weekly Gazette run

Follow these steps exactly. Stop and report if a step fails. Never invent a number.

1. `python test_recap.py` — must pass.
2. For EACH league `id` in `leagues.json`, in order, do steps 3–6. One league failing
   (e.g. Sleeper not ready) must not stop the others; report it and move on.
3. `python recap.py --league=<id>` — builds `posts/<key>.facts.json` and a plain `posts/<key>.txt`.
   If it prints "already generated", skip this league: that week is done.
   If it says Sleeper data is not ready, skip this league and report the error.
4. Open `recap.py`, read the `SYSTEM` prompt (tone: `CFG["tone"]`), and read the new
   `posts/<key>.facts.json`. Following that prompt exactly:
   - overwrite `posts/<key>.txt` with PART 1 (the mobile recap)
   - write PART 2 (every block, in the prompt's order, ending with the `PUNS:` line) to
     `posts/<key>.stories.md`
   Before moving on, reread each story once for flow: every sentence follows from the one
   before it, and every pun passes the prompt's flow test. Cut any pun that fails.
5. `python recap.py --league=<id> --finalize` — checks every number against the facts, the
   `PUNS:` line, pun-names that repeat the real name, and any pun or team-name joke reused from
   an earlier week, then adds the Gazette link. If it fails, fix only what it flags (numbers
   from the facts; fuse repeated pun-names like "Drake London Bridges"; invent a new pun for a
   reused one) and rerun.
   After 2 failures: delete `posts/<key>.stories.md`, run `python recap.py --league=<id> --regen`
   to restore the plain template, and continue.
6. Next league.
6a. Newsreel videos. Follow `.claude/skills/gazette-newsreel/SKILL.md`. In short, from `newsreel/`:
   run `./setup.sh` once per session; then for EACH league that got a new recap, one league after the other:
   - `python3 tools/names.py ../posts/<key>.facts.json <edition>` for this week and the week before
     (`<edition>` is `<league path>_<season>_w<N>`, or `<season>_w<N>` for the league with no path);
   - `python3 tools/brief.py <edition>`; add any new team name to `pronunciations.json`;
   - write `scripts/<edition>.script.json` in the newsreel house voice and run `node tools/check_script.mjs <edition>` until it passes;
     let one independent agent fact-check it against the brief and apply its real findings;
   - `tools/build_edition.sh <edition> build/<edition>.mp4 <site>/<path>`, and look at the review frames;
   - `python3 tools/publish.py <edition> build/<edition>.mp4`. This puts the video in `posts/` and adds the
     "🎬 Watch the newsreel" line to `posts/<key>.txt`, so the chat post has two links.
   A league whose video fails is reported and keeps its text recap; it does not stop the others.
   If `./setup.sh` fails, skip all videos, report why, and continue to step 7. The newsreel never blocks the text recaps.
7. Commit only the `posts/` and `newsreel/scripts/` folders (and `newsreel/pronunciations.json` if it changed) with message `Week <N> recaps` and push directly to `main` (authorized by the owner: the Gazette site deploys only from `main`).
8. Reply with each league's `posts/<key>.txt`, each under a heading with the league name,
   so each can be pasted into its own group chat. List any league that was skipped or fell
   back to the plain template, and why.
