# The Beer Den Gazette — Newsreel

> **Home:** this folder is part of the gazette repository. The weekly routine (`ROUTINE.md`, step 6a) and the skill `.claude/skills/gazette-newsreel/SKILL.md` run it: `./setup.sh`, then `tools/names.py`, `tools/brief.py`, the script, `tools/build_edition.sh` and `tools/publish.py`. The videos go to `posts/` and the site; the record below is the history from the first editions, made in another repository.

A video edition of the weekly gazette, in the style of an old newspaper and a 1930s–1940s cinema newsreel.
This is a HyperFrames project. One edition is one league and one week.

## Editions

| Edition | Video | Length | Status |
|---|---|---|---|
| Beer Den 3.0, Week 8, 2026 | `beer-den-gazette-newsreel-2026-w8.mp4` | 86.5 s | Approved by the owner on 11 November 2026 |
| Beer Den 3.0, Week 9, 2026 | `beer-den-gazette-newsreel-2026-w9.mp4` | 89.4 s | Second version, for the owner's review: a newsreel script and power rankings. The owner did not approve the first version (commit `a51c4be`): it felt like a gangster film, and it had no power rankings. |
| Double Fist, Week 9, 2026 | `double-fist-gazette-newsreel-2026-w9.mp4` | 89.4 s | For the owner's review |
| Coozeball, Week 9, 2026 | `coozeball-gazette-newsreel-2026-w9.mp4` | 86.1 s | For the owner's review |
| Uncle Rico's Training Grounds, Week 9, 2026 | `uncle-rico-gazette-newsreel-2026-w9.mp4` | 89.4 s | For the owner's review |

Each video is 1080×1350, 30 fps, and below 16 MB. This project did not send a video to the league.

| Open item | Detail |
|---|---|
| Sound | The owner approved the Week 8 video with voice style 23B. A speech recognizer checks each sentence of each edition. A person has not listened to the Week 9 narration. On 11 November 2026 the owner kept voice 23B for the second Week 9 draft ("voice is fine"); styles 27 and 28 are not used. |
| Week 8 captions | The approved Week 8 file has 12 frames in which the caption strip is off for one frame (a blink between two captions). The tools of today do not have this fault. The file is not changed. |
| Team names in speech | `pronunciations.json` has the spoken form of each team name. The owner gave the forms for `dookkk` ("Dookie") and `CUTHISYR` ("See You This Year"). The other forms follow the spelling. |
| Music | None. No free music source is available without a HeyGen sign-in. |
| Home | This project is in the `Electric-avenue-` repository. It is not in the gazette repository, and the weekly routine does not run it. |
| Leagues | All four leagues have a Week 9 video. An edition name is `<league path>_2026_w9` (Beer Den 3.0 has no path: `2026_w9`). |
| Team names | The gazette names a team by its owner's username. When an owner asks for the team name, `display_names.json` maps it for one league, and `tools/names.py` copies the facts into `data/` with that name. Uncle Rico: Tbonez420 is "The Sackville Bagginses" (the team owner asked for it in the league chat). The owner of the league says both names can be used interchangeably; the video uses the team name. |
| Other leagues | The three scripts were written in the session without the judge panel, checked by the code of the panel and by one independent fact and rules checker (5 corrections). The spoken forms of their team names follow the spelling; the owner has not checked them. The recognizer hears several of these names differently (for example "Gio Meow", "Timoteo", "Sabrinie"), so a person must listen to the names. |

## What is on screen

Ten segments (nine in the Week 8 edition, which has no power rankings). Each name and number comes from the facts file of the gazette (`data/<edition>.facts.json`). Nothing is typed by hand.
`tools/plan.py` selects the facts for each segment. The scene builder and the brief for the writers use the same plan.

| Segment | Picture | Facts used |
|---|---|---|
| n1 Open | Film leader countdown, then the masthead | league, season, week, edition |
| n2 The lead | A front page spins in: the top score. The label is "best score of the season" when the facts say so. | `high`, the result of that game, `lore.season_high` |
| n3 Upsets or Scores | Two or three upsets: one clipping for each upset. Fewer than two upsets: one clipping for each of three games that no other segment shows. | `upsets`, or `results`, `closest`, `blowout` |
| n4 Bench crime | A "WANTED" poster, with the result of that game ("Lost to <team> by <margin>") | `bench_crimes`, the result of that game |
| n5 Boom and bust | Two cards | `booms`, `busts` |
| n6 The basement | A notice with the lowest score and the result of that game. The label is "lowest score of the season" when the facts say so. | `low`, `standings`, `lore.season_low`, the result of that game |
| n7 Standings | The full table, with the playoff line | `standings`, `playoff_teams` |
| n7b Power rankings | The full table in the order of the power rank: move from last week, record, and true record (the record against every team, every week). The row of a team gets a tint when the announcer names that team. | `power_rankings` |
| n8 Next week | A fight poster with the odds | `next_week_card` |
| n9 Sign-off | The masthead and the address of the full edition | — |

- Week 8 had three upsets, so n3 was "Upsets". Week 9 had one upset, which was also the lead story, so n3 is "Scores".
- If the facts have no bench crime, no boom, no bust or no power rankings, the build stops with a message. It does not show a default. A build that stops writes no file, so the last edition stays complete.
- A tied game shows "tied", not "beat". In Week 1 and after the first playoff week the gazette gives no rank of the week before, so the tables show no move marks.
- The robot is Rivet, drawn by `comic.py` of the gazette repository, with the costume of the edition (`theme.py`).

## Colours

The video uses the palette of the gazette site (`site.py`, `:root`), so the two look like one paper.

| Use | Colour | Variable on the site |
|---|---|---|
| Paper | `#fffefb` | `--paper` |
| Ink | `#1c1b19` | `--ink` |
| Cards and the caption strip | `#f5f2ea` | `--soft` |
| Rules | `#2b2925` | `--rule` |
| Accent and the bar at the top | the accent of the edition, `#9a3412` for the Autumn Edition | `--accent` |
| Up and down in the standings | `#2f6b2a`, `#8a2a1c` | `--up`, `--down` |

- The masthead is "The <league> Gazette", as on the site.
- The film overlay (grain, scratches, a faint flicker) is light, so the paper stays white. The first version had a sepia tint and tan paper. That was wrong for this paper.

## Voice

- A local voice model (Kokoro, Apache 2.0 licence as its project states).
- `voice.json` is the voice recipe: the base voice or a blend of voices, the speed, the pitch change, and the audio chain that makes the old sound.
- The recipe in use is style 23B (`alto-23b`): a blend of `af_heart` (80 percent) and `am_fenrir` (20 percent), speed 1.07, no pitch change, about 185 Hz. It is a low woman's voice with a radio band, compression, hiss, and radio crackle (13 clicks per second).
- Styles 23A and 23C are the same voice with less crackle and with more crackle.
- The pitch change keeps the length of the audio, so the captions stay in time.
- `tools/voice_lab.py` builds and tests recipes. It measures the pitch, and a speech recognizer scores how clear the voice is. To change the voice, copy a recipe into `voice.json`.
- `voice-styles.json` lists the 35 styles on the sample reels (1 to 26, 7A to 7F, and 23A to 23C). To use one, copy its `recipe` into `voice.json` and build.
- Each recipe must be an original voice. Do not copy the voice of a real person or of a film.

## Script

`scripts/<edition>.script.json` holds the narration of one edition. A panel of AI agents writes it (`workflows/script-panel.js`):

1. `tools/brief.py` writes the brief from the facts file: the verified facts as text, and the picture plan.
2. Three writers write the script in the house voice, each with a different comic angle.
3. Three judges score the scripts blind: a comedy editor, a league member, and a standards editor.
4. A head writer builds the final script from the winner and the best lines of the others.
5. Code checks the limits, each number, each team name, and the words that bring the pictures in. A fact checker and a rules checker then each try to find a fault. The head writer repairs the script, for a maximum of three rounds.

The house voice is a cinema newsreel announcer of about 1940, who reads the front page to a theater audience: the announcer talks to the audience, calls out each headline, and uses action verbs. The Week 8 script, which the owner approved, is the model.

The first Week 9 script did not have this voice. Its brief asked for "a front-page editor of about 1925" with dry wit, and it did not ask for the newsreel phrases. The result had police and bookmaker words ("Wanted for questioning", "our oddsmaker") and wry asides ("is also present", "is now a fair question"). With the low voice and the radio crackle, the owner heard a gangster film. The panel now forbids that register, and the judges and the rules checker test for it.

The rules for the writers come from the gazette's own writer contract: use only the facts, copy each number exactly, and make jokes about fantasy performance only.

A sentence can have a `tts` form. It is the caption with pause marks (commas) for a line that the voice runs together. The caption on screen does not change.

### Week 8

Three writers wrote in three old-time styles. The front-page editor style won, and it became the house voice.

| Script | Funny | Period voice | Clarity | Total | Ranked first by |
|---|---|---|---|---|---|
| Front-page editor | 9.0 | 8.2 | 7.2 | 8.3 | 3 of 3 judges |
| Newsreel barker | 6.3 | 8.2 | 7.7 | 6.8 | 0 |
| Ringside radio man | 4.2 | 5.2 | 6.7 | 5.2 | 0 |

### Week 9, first script (not approved)

Three writers wrote in the voice of a front-page editor. The banner-headline script won (8.3 of 10, first for 3 of 3 judges). The fact check was clean. The rules check found two faults in round 1 and none after the repair. The owner then said that the video felt like a gangster film. The script is in commit `a51c4be`.

### Week 9, second script (in the video)

Three writers wrote in the voice of a cinema newsreel announcer, with one more segment for the power rankings. The head writer used the headline-call script as the base and took lines from the other two.

| Script | Funny | Period voice | Clarity | Total | Ranked first by |
|---|---|---|---|---|---|
| Headline call | 8.0 | 7.3 | 7.2 | 7.5 | 2 of 3 judges |
| To the crowd | 5.5 | 9.0 | 8.7 | 7.3 | 1 of 3 judges |
| Revision of the first script | 7.0 | 5.8 | 8.0 | 6.5 | 0 |

- Code, the fact checker and the rules checker found no fault in round 1.
- Two lines are kept on purpose, and the head writer named them: "see you next year!" (a joke on the spoken name of CUTHISYR; the facts do not say that the team is out of the playoffs) and "The playoffs take 6." (the one dry aside of the old voice).
- "Folding Table Champ folds" is a new turn on a name that the paper has punned on before.

Scores are from 1 to 10. The judges are AI models, not the league.

## Build

```
pip install kokoro-onnx sherpa-onnx
E=2026_w9                                                     # the edition: season and week
cp /path/to/league-recap/posts/<league id>_${E}_recap.facts.json data/$E.facts.json
python3 tools/brief.py $E                                     # the brief for the writers: build/$E.brief.json
#   run workflows/script-panel.js with the brief, and save the result as scripts/$E.script.json
python3 tools/narrate.py /path/to/kokoro-v1.0.onnx /path/to/voices-v1.0.bin $E
python3 tools/build.py --gazette /path/to/league-recap
python3 tools/check_screen.py
npx hyperframes check
python3 tools/check_voice.py /path/to/sherpa-onnx-whisper-small.en
npx hyperframes render --quality looks -o renders/full.mp4
tools/shrink.sh renders/full.mp4 beer-den-gazette-newsreel-${E/_/-}.mp4
python3 tools/check_captions.py beer-den-gazette-newsreel-${E/_/-}.mp4
```

- The two voice model files are in the `model-files-v1.0` release of the `kokoro-onnx` project.
- `build.py` reads the edition from the narration (`build/timeline.json`). It stops if the facts file is for a different league, season or week.
- `build.py --format social` makes a 1080×1920 frame with the same layout. The lower third stays empty for the buttons of a social platform.
- The full render is about 30 MB. `shrink.sh` makes a copy below 16 MB for a group chat.
- Set `HYPERFRAMES_NO_TELEMETRY=1` to stop the usage reports of the HyperFrames tool.
- `index.html` and `compositions/` are the edition that was built last.

### A new week

1. Copy the new facts file to `data/` with `python3 tools/names.py <facts file> <edition>`, which applies `display_names.json`. Add each new team name to `pronunciations.json`, also a name that is said as it is spelled; `brief.py` stops if a team name is not in that file.
2. Run `brief.py` and the script panel. Save the final script as `scripts/<edition>.script.json` with `league`, `season`, `week` and `beats` (the segment ids of the brief, in order).
3. Run the build steps. `narrate.py` stops if the script is too long for 90 seconds.
4. Run the checks below. If the narration check flags a line, find a clear form with `tools/hear.py`, add it as a `tts` form or to `pronunciations.json`, and build again.

### Checks

| Check | Command | What it proves | What it does not prove |
|---|---|---|---|
| Screen | `python3 tools/check_screen.py` | Each number on screen is a value in the facts file. Each team name has the exact spelling. The captions are the script, word for word. | That a number is next to the correct name. |
| HyperFrames | `npx hyperframes check` | No error in lint, runtime, layout, motion, contrast, craft and audio. | That the video looks good. |
| Captions in the video | `python3 tools/check_captions.py <video.mp4>` | Each video frame of each caption shows the caption strip. | That the words are correct; the screen check does that. |
| Narration | `python3 tools/check_voice.py <whisper_dir>` | A speech recognizer hears the words of each sentence, in the clean voice and in the old-time voice. | That the voice sounds good. A difference means that a person must listen to that sentence. |
| Review panel | `python3 tools/frames.py <dir>`, then `workflows/video-review.js` | AI reviewers look at a frame of each sentence and of each segment: layout, words against pictures, numbers against facts, and the code change. A skeptic checks each finding. | That a person agrees. |

## Files

| File | Purpose |
|---|---|
| `data/<edition>.facts.json` | The facts of the gazette for that league and week. A copy; do not edit it. |
| `scripts/<edition>.script.json` | The narration. Each sentence is a caption. |
| `pronunciations.json` | The spoken form of team names and of hard player names. |
| `voice.json` | The voice recipe in use. |
| `voice-styles.json` | All voice styles that were built and measured, with the number on the sample reels and the recipe. |
| `tools/plan.py` | The picture plan: which facts each segment shows. |
| `tools/brief.py` | Writes the facts and the picture plan as text for the script panel. |
| `workflows/script-panel.js` | The script panel: writers, blind judges, checks. |
| `tools/narrate.py` | Speaks the script with the voice recipe, fits the pauses, writes `build/timeline.json`. |
| `tools/build.py` | Writes `index.html` and `compositions/*.html` from the facts and the timeline. |
| `tools/check_screen.py`, `tools/check_voice.py`, `tools/check_captions.py` | The screen check, the narration check, and the frame-by-frame caption check of a rendered video. |
| `tools/hear.py` | Speaks test lines and prints what the recognizer hears. |
| `tools/names.py`, `display_names.json` | Copies a facts file of the gazette into `data/` with the team names that owners asked for. |
| `tools/check_script.mjs` | The code checks of the script panel on one saved script. |
| `tools/build_edition.sh` | Speaks, builds, checks and renders one edition. |
| `../.claude/skills/gazette-newsreel/SKILL.md` | The skill: the weekly procedure and the owner's decisions. |
| `tools/frames.py`, `workflows/video-review.js` | The review frames and the review panel. |
| `tools/voice_lab.py` | Builds and tests voice recipes. `narrate.py` uses it to apply the recipe. |
| `tools/shrink.sh` | Makes the chat-size copy. |
| `index.html`, `compositions/` | The HyperFrames project. `build.py` writes these files again on each build, so edit `build.py`, not these files. |

## Verification

### Week 9, second version (`beer-den-gazette-newsreel-2026-w9.mp4`)

Done:

- File: 1080×1350, 30 fps, 89.4 seconds, 15.6 MB. It decodes from start to end with no error. Video: 2,682 frames. Audio: AAC.
- Loudness: −13.6 LUFS integrated, −1.8 dBFS peak.
- Screen check: each number on screen is in the facts file, each team name has the exact spelling, and the 59 captions are the script word for word.
- `npx hyperframes check`: no errors and no warnings in lint, runtime, layout, motion, contrast, craft, and audio.
- Narration check: the recognizer agrees with 218 of the 220 words of the old-time voice, which is the voice in the video. The two differences: "romps" is heard as "roms", and "decline to comment" is heard as "declined to comment". On 11 November 2026 the owner listened to these two sentences and said both are fine. An earlier record said "all 220 words": the checker then counted these two pairs as equal, and the code review found that this was wrong.
- For the next build: the spoken form "The standings decline, to comment." gives "decline" in a test. No spoken form corrected "romps".
- The audio of the file is the narration that the recognizer checked: the two loudness curves agree (correlation 0.999).
- Caption check, frame by frame: no frame of a caption is without the caption strip (2,682 frames).
- Four sentences have a `tts` form. Before these forms, the recognizer heard "Favorite" for "Favored", "DME" for "D M Me", and "True records" for "true record".
- Review panel, on 36 frames of the build before the fixes below. A skeptic checked each finding.

| Reviewer | Result |
|---|---|
| Numbers and names | No fault. About 150 values, pairings and labels on screen agree with the facts. |
| Words against pictures | 3 confirmed, 3 refuted. Confirmed: the caption strip was off for one frame between two captions; a caption cut "true record" in two; the robot stands across the borders of the two boom and bust cards. |
| Layout | 3 confirmed, 6 refuted. Confirmed: the same caption fault; the same robot; three labels of 30 px ("PLAYOFF LINE", "REC", "TRUE REC"). |
| Code | 11 confirmed (2 medium, 9 low). None is a fault of the Week 9 pictures. Examples: in a playoff week the brief gave a regular-season streak as a fact of this week; the brief said "beat" for a tied lead game; the narration checker counted two different words as equal; the row tint had the colour of the Autumn Edition in each edition. All 11 are corrected. After the corrections the Week 9 scenes are the same, byte for byte. |

- The caption fault was real: in the first render of this version, 14 frames had no caption strip. The first Week 9 version had 15 such frames, and the approved Week 8 file has 12.
- Fixes after the review: a caption now starts and ends in the middle between two video frames, so each frame shows one caption. "true record" stays in one caption. The labels "REC" and "TRUE REC" are 34 px.
- Not changed, because they are the same in the approved Week 8 video: the robot across the two cards, and the 30 px label "PLAYOFF LINE".
- After the fixes: all checks above ran again on the final file, and 14 frames of the final file were inspected. The review panel did not look at the final frames.

Not done:

- A full listen of the Week 9 narration by the owner is not on record; the owner checked the voice and the two flagged sentences.
- Playback on a phone, and a send in a real group chat.
- The other three leagues of the gazette.

### Week 9, the other three leagues

All three files: 1080×1350, 30 fps, about 15.6 MB. For each: the screen check passes; `npx hyperframes check` has no errors (Coozeball: 1 warning, 3 s with no motion in the Upsets scene, which has two clippings); the caption check finds no frame of a caption without the strip. Frames of each video were inspected.

| League | Narration check (old-time voice) | Note |
|---|---|---|
| Double Fist | 35 word differences of 231 | Most are team names with digits or odd spellings (Nfin3sol, ZZ2zZzZzZz2ZZ, Eman8771, The A-Gap A-Team) |
| Coozeball | 13 of 201 | Names: Coozeball, GioMeow, Timoteo, Perkis System |
| Uncle Rico's Training Grounds | 9 of 205 | Names: Tbonez420, RicoJRoday, Sabrinie |

A first render had two layout faults: a short team name made the lead headline run over the card, and the long site address broke inside a word. Both are corrected, and the three videos were rendered again.

### Week 9, first version (commit `a51c4be`, not approved)

89.4 seconds, 9 segments, no power rankings. The checks of that time passed (screen, HyperFrames, narration). A review panel on 32 frames found no wrong number or name (about 95 values) and confirmed 8 picture and caption findings and 11 code findings. None of the code findings was a fault of the Week 9 pictures; all 11 are corrected (a tied game drawn as a win, a stop in Week 1 and after the first playoff week, a cue word found inside a longer word, and others).

### Week 8 (`beer-den-gazette-newsreel-2026-w8.mp4`)

The owner approved this file. It was built before the tools changed for Week 9, and it was not rendered again.

- `npx hyperframes check`: no errors and no warnings in lint, runtime, layout, motion, contrast, craft, and audio.
- The file decodes from start to end with no error. Video: 2,594 frames. Audio: AAC.
- Loudness: −13.5 LUFS integrated, −1.1 dBFS peak.
- Colour, measured in a frame of the video against a picture of the site: paper (252, 250, 247) against (255, 254, 251); top bar (151, 53, 19) against (154, 52, 18).
- Narration check: the recognizer agrees with all 205 words of the old-time voice, which is the voice in the video. It differs on 1 word of the clean voice ("Champ share" heard as "champs share").
- The approved file is not changed. A new build of Week 8 with the tools of today gives different pictures, by design: the bench-crime line names the other team (n4), the basement notice has the result line and a smaller score (n6), each team with the record of the leader has the accent colour in the standings (n7; the approved file has it on the first team only), and the captions keep names in one piece. The other scenes and the root file are the same, byte for byte, but for one attribute for the layout check in n2.

## Limits

- The speech engine is not deterministic. The length of the narration changes by about 1 second between builds.
- The script panel takes about 50 minutes for one edition, and the review panel also takes time. Both use many AI agents.
- The pictures are fixed for each segment. A line of the script can name a team that is not in the picture; the caption shows the name.
- This voice runs an "s" at the end of a word into an "s" at the start of the next word. A `tts` form with a comma corrects that. The captions show each line.
- A voice model cannot copy a specific actor. Each style is an original voice.
- The recognizer measures words. It does not measure if the voice or the crackle sounds good. A person must listen.
- The large headlines use League Gothic, a condensed face that fits long team names. The site sets its headlines in Old Standard.

## Credits

- Speech: [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) voice model, Apache 2.0.
- Video: [HyperFrames](https://hyperframes.heygen.com), Apache 2.0. The grain overlay is its `grain-overlay` component.
- Sound effects: three effects that the HyperFrames skill bundles, from Pixabay under the Pixabay Content License.
- Fonts: UnifrakturMaguntia and Old Standard TT, from the gazette repository. League Gothic, bundled with HyperFrames.
- Robot: Rivet, from the gazette repository.
