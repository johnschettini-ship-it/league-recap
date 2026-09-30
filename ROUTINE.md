# Weekly Gazette run

Follow these steps exactly. Stop and report if any step fails. Never invent a number.

1. `python test_recap.py` — must pass.
2. `python recap.py` — builds `posts/<key>.facts.json` and a plain `posts/<key>.txt`.
   If it prints "already generated", stop: this week is done.
   If it says Sleeper data is not ready, stop and report the error. Publish nothing.
3. Open `recap.py`, read the `SYSTEM` prompt (tone: `CFG["tone"]`), and read the new
   `posts/<key>.facts.json`. Following that prompt exactly:
   - overwrite `posts/<key>.txt` with PART 1 (the WhatsApp recap)
   - write PART 2 (the matchup stories) to `posts/<key>.stories.md`
4. `python recap.py --finalize` — checks every number against the facts and adds the
   Gazette link. If it fails, fix only the flagged numbers from the facts and rerun.
   After 2 failures: delete `posts/<key>.stories.md`, run `python recap.py --regen`
   to restore the plain template, and continue.
5. Commit only the `posts/` folder with message `Week <N> recap` and push to `main`.
6. Reply with the full contents of `posts/<key>.txt` so it can be pasted into WhatsApp.
