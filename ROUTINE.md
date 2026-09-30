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
   - overwrite `posts/<key>.txt` with PART 1 (the WhatsApp recap)
   - write PART 2 (banner + matchup stories) to `posts/<key>.stories.md`
5. `python recap.py --league=<id> --finalize` — checks every number against the facts and
   pun-names that repeat the real name, then adds the Gazette link. If it fails, fix only what
   it flags (numbers from the facts; fuse repeated pun-names like "Drake London Bridges") and rerun.
   After 2 failures: delete `posts/<key>.stories.md`, run `python recap.py --league=<id> --regen`
   to restore the plain template, and continue.
6. Next league.
7. Commit only the `posts/` folder with message `Week <N> recaps` and push to `main`.
8. Reply with each league's `posts/<key>.txt`, each under a heading with the league name,
   so each can be pasted into its own WhatsApp group.
