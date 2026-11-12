---
name: gazette-newsreel
description: Make the weekly old-time newsreel video edition of the gazette (the league-recap repository) for one or all four fantasy leagues - facts to script to narration to HyperFrames video, with fact, screen, narration and caption checks. Use for "make the week N video", "newsreel for Coozeball", "video edition of the gazette", "fix a team name in the video", or any change to the gazette-newsreel project.
---

# Gazette newsreel

The project is `newsreel/` in this repository (the gazette). Its README is the full record: read it before a change. The weekly routine (`ROUTINE.md`, step 6a) runs it after the text recaps.
One video = one league and one week = one **edition**, named `<league path>_<season>_w<week>`.
Beer Den 3.0 has no league path, so its edition is `2026_w9`; the others are `double-fist_2026_w9`, `coozeball_2026_w9`, `uncle-rico_2026_w9`.
The league path comes from `leagues.json`.

## Fixed decisions of the owner (do not change without the owner)

- **Voice:** style 23B in `voice.json` (an alto blend with radio crackle). The owner approved it two times.
- **House voice of the script:** a cinema newsreel announcer of about 1940 who reads the front page to a theater crowd. Use action verbs, call each headline, address the crowd ("folks", "ladies and gentlemen"), and keep it cheerful.
  - Never use the crime-film, police or bookmaker register: no "wanted for questioning", "oddsmaker", "the cellar", and no wry asides with verbs of state. The owner rejected one script because it "feels like a gangster film".
  - The single word "Wanted" on the WANTED poster is the one exception.
- **Segments:** n1 open, n2 lead, n3 upsets or scores, n4 bench crime, n5 boom and bust, n6 basement, n7 standings, **n7b power rankings** (the owner asked for them), n8 next week, n9 sign-off.
- **Length:** at most 90 seconds. Format: 1080×1350, below 16 MB, for a group chat.
- **Team names:** the gazette uses owners' usernames. When an owner asks for their team name, add it to `display_names.json`.
  - Uncle Rico: Tbonez420 is "The Sackville Bagginses". The owner says both names are interchangeable; the video uses the team name.
- **Spoken forms the owner gave:** `dookkk` is "Dookie" and `CUTHISYR` is "See You This Year". All other spoken forms follow the spelling and are not checked by the owner.

## Hard rules

- The newsreel never changes the gazette's facts, recaps or stories. It adds a video and one link line to `posts/` (through `tools/publish.py`).
- Every name and number on screen and in the script comes from the facts file. No computed sums, no guesses about why a player scored, and jokes about fantasy performance only.
- Do not repeat the username table (`aliases`) of `leagues.json` anywhere.
- Set `HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` for every HyperFrames command. The voice models are local (Kokoro, Apache 2.0); do not use paid voice services, and never copy a real person's or a film's voice.
- Builds share `build/`, `compositions/` and `index.html`: build editions **one after the other**, never in parallel.
- Never report a check as passed without its output. A person must listen to any sentence that the narration check flags.

## Setup in a new session

Run `./setup.sh` in `newsreel/` once per session. It installs the Python packages and downloads the voice model and a small speech checker to `~/.cache/newsreel` (about 530 MB, under 1 minute).
If HyperFrames cannot find a browser, set `HYPERFRAMES_BROWSER_PATH` to the Chromium headless shell of the container.

## Weekly steps (run from `newsreel/`)

1. **Facts.** Pull the gazette. For each league, copy the week and the week before:
   `python3 tools/names.py ../posts/<league id>_<season>_w<N>_recap.facts.json <edition>`. This applies `display_names.json`.
2. **Names.** Run `python3 tools/brief.py <edition>`. It stops for each team name that is not in `pronunciations.json`.
   Add the missing names, then test hard names with `python3 tools/hear.py ~/.cache/newsreel/kokoro/kokoro-v1.0.onnx ~/.cache/newsreel/kokoro/voices-v1.0.bin ~/.cache/newsreel/whisper "line" ...`.
3. **Script.** Write `scripts/<edition>.script.json` with `league`, `season`, `week` and `beats` (the segment ids of the brief, in order). Use one of two ways:
   - **Panel** (only when the user asks for it or opts in to multi-agent work): run `workflows/script-panel.js` with the content of `build/<edition>.brief.json` as args. It runs three writers, blind judges and fact and rules checkers. It takes about 50 minutes for each league.
   - **Direct** (the default): write the script from the brief in the house voice. Run `node tools/check_script.mjs <edition>` until it reports no problem. Then let one independent agent fact-check and rules-check the script against the brief and the facts file, and apply its real findings.
   - Limits that the check enforces:
     - 212 to 236 spoken words.
     - At most 28 sentences, 18 team-name mentions, 10 decimal numbers (each said only once) and 8 exclamation marks.
     - A picture-cue word in each segment that has one. No `used_pun_names` copy.
     - No word ending in "s" directly before a team name that starts with "s".
4. **Build** each edition, one after the other:
   `tools/build_edition.sh <edition> build/<edition>.mp4 johnschettini-ship-it.github.io/league-recap/<league path>`.
   - It speaks, runs the narration check, builds, runs the screen check and the HyperFrames check, renders, makes the chat-size copy, runs the caption check and takes the review frames.
5. **Narration flags.** Look at `build/<edition>.voice.txt`.
   - For a flagged common word, add a `tts` form (usually a comma, or the word in a new position), then build again.
   - Flagged team names are mostly the recognizer's spelling. List them for the owner to listen to.
6. **Look at the frames** (the contact sheets in `$FRAMES_DIR/<edition>`) before you deliver. Check:
   - no text over a card edge, no word broken inside;
   - the numbers and names next to the right teams;
   - each picture on the sentence that names it.
7. **Publish.** `python3 tools/publish.py <edition> build/<edition>.mp4` copies the video to `posts/<key>.newsreel.mp4` and adds the line "🎬 Watch the newsreel: <link>" to `posts/<key>.txt`.
   - The chat post then has two links: the stories and the video. People do not click twice.
   - `site.py` copies the videos of the newest 3 weeks of each league to the site (the site has a size limit). Older video links stop working.
   - Commit `posts/` and `newsreel/scripts/` with the recaps (ROUTINE.md step 7).

## Known faults and their causes (do not bring them back)

- A hole of 0.01 s between captions made the strip blink. Captions now start and end between video frames.
- The white flash at a scene cut lightens the strip for one frame. That is by design; the caption check allows it.
- A short team name made the lead headline too large (now at most 140 px). A long site address now breaks at a slash.
- A cue word matched inside a longer word ("odds" in "oddsmaker"). Cues are whole words now.
- In a playoff week, the gazette's records and streaks are from the end of the regular season. The brief says so.
- The speech engine runs a final "s" into a following "s" ("meets stufflydogs"). Add a comma in a `tts` form.
- The approved Week 8 Beer Den file has 12 one-frame caption blinks. The owner chose not to rebuild it.
- The speech checker here is Whisper base (small download). It flags more names than the small model did; most flags are the recognizer's spelling of a team name.
