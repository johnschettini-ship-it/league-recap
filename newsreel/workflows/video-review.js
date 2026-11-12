export const meta = {
  name: 'gazette-newsreel-review',
  description: 'Review one built edition of the Gazette newsreel before the final render: frames, words against pictures, numbers against facts, and the code change',
  whenToUse: 'After tools/build.py and the HyperFrames check. Run tools/frames.py, then pass {review_file: "<project>/build/<edition>.review.json", project_dir, diff_command}.',
  phases: [
    { title: 'Review', detail: 'four reviewers, each with a different lens' },
    { title: 'Verify', detail: 'one skeptic for each reviewer tries to refute each finding' },
  ],
}

const A = args || {}
if (!A.review_file || !A.project_dir || !A.diff_command) return { error: 'Pass review_file, project_dir and diff_command in args' }

const CONTEXT = `THE VIDEO
An old-time newsreel video, 1080 x 1350 px, for a phone, about 85 seconds. It is the video edition of a weekly fantasy football newspaper.
Code builds every picture from a facts file. A script panel wrote the narration. The caption strip near the bottom shows the words as the announcer says them.
The project is at ${A.project_dir}. You may read any file there. Do not change any file. Do not run a build, a render or a git command that changes the repository.

YOUR INPUT FILE: ${A.review_file}
Read it first, all of it. It is one JSON object with these keys:
  "segments"  the picture plan: what each of the nine segments shows, and which word brings each picture in
  "script"    the narration, one line for each segment, sentences divided by " | "
  "facts"     the verified facts: the only source of names, scores, ranks, records and odds
  "frames"    the review frames, in time order. Each has "path" (a PNG file; open it with the Read tool), "t" (seconds), "segment", "kind" and, for a sentence frame, "sentence".
A frame of kind "end of segment" shows the segment with all its pictures in place, in the pause after the last sentence, so it has no caption.
A frame of kind "middle of sentence" shows the picture while that sentence is spoken, with its caption.`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    frames_read: { type: 'number', description: 'How many frame files you opened' },
    findings: { type: 'array', items: { type: 'object', properties: {
      where: { type: 'string', description: 'The frame file name and time, or the file and line of code' },
      severity: { type: 'string', enum: ['high', 'medium', 'low'], description: 'high: a wrong fact on screen, unreadable text, or a build that fails. medium: a clear flaw that a viewer sees. low: polish.' },
      problem: { type: 'string' },
      evidence: { type: 'string', description: 'What you saw, exactly: the text, the position, the values' },
      fix: { type: 'string' },
    }, required: ['where', 'severity', 'problem', 'evidence', 'fix'] } },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      index: { type: 'number', description: 'The number of the finding, from 0' },
      real: { type: 'boolean', description: 'true only when you reproduced the problem yourself' },
      reason: { type: 'string', description: 'What you checked and what you saw' },
    }, required: ['index', 'real', 'reason'] } },
  },
  required: ['verdicts'],
}

const LENSES = [
  { key: 'layout', frames: true, effort: 'medium', text: `You are a layout reviewer for video. Open EVERY frame. In each one look for: text that overlaps other text or a drawing; text cut off by a box or by the frame edge; a line that wraps in an ugly place; ` +
      `text too small to read on a phone (below about 34 px in the 1080 px frame); a box that is empty or far too large for its content; elements that are not aligned with the others; ` +
      `a caption strip that covers a picture; a segment that differs in style from the others (font, colour, rule weight, spacing). Report only what you can see in a frame. Give the frame and the position.` },
  { key: 'words-and-pictures', frames: true, effort: 'medium', text: `You are a continuity reviewer. Open EVERY frame marked "middle of sentence". For each one check: (1) the caption is a part of that sentence, word for word; ` +
      `(2) the picture that the sentence talks about is on screen at that moment (a name or a number that the announcer says must be visible, or must have been visible earlier in the same segment); ` +
      `(3) nothing is on screen that the announcer has not reached yet and that spoils a later line of the same segment. Then open each "end of segment" frame and check that every picture of the plan is there. ` +
      `Report each mismatch with the frame, the sentence, and what is on screen.` },
  { key: 'numbers-and-names', frames: true, effort: 'medium', text: `You are a fact checker for the PICTURES, not for the narration. Open EVERY frame marked "end of segment", and any other frame you need. ` +
      `Read every name, score, rank, record, label and percent on screen, and compare each one with the verified facts: the value, and also the PAIRING (this score belongs to this team, this player belongs to this team, ` +
      `this rank is the rank before or after the week as the label says, the winner is on the winner's side). Check each label too ("closest game", "lowest score of the season", "final", "up 2", "the odds"). ` +
      `You may open the facts file in data/ of the project. Report every value or pairing that the facts do not support. If all are correct, return no findings and say how many values you checked.` },
  { key: 'code', frames: false, text: `You are a code reviewer. The tools of this project changed so that they build a new edition each week from a facts file. Read the change: run \`${A.diff_command}\` (read only), ` +
      `and read tools/plan.py, tools/brief.py, tools/build.py, tools/narrate.py, tools/check_voice.py, tools/check_screen.py and workflows/script-panel.js in full where you need context. ` +
      `Find correctness bugs: a wrong value on screen for some week's facts; a crash on a normal week (a tie, no upset, three upsets, an empty list, a team name with a regex character, a negative or a 0.0 score, ` +
      `a record with two digits, a playoff week); a regression for the edition that was built before (data/2026_w8.facts.json with scripts/2026_w8.script.json); a check that passes when it must fail; ` +
      `a silent default where the tools must stop. For each bug give the file, the line, the input that triggers it and the wrong result. Do not report style. Do not report a problem that you did not trace in the code.` },
]

const results = await pipeline(
  LENSES,
  l => agent(
    `${l.text}\n\n${CONTEXT}\n\nBe exact and skeptical of your own findings: report a problem only when you can state the evidence. An empty list is a valid result.`,
    { label: 'review:' + l.key, phase: 'Review', schema: FINDINGS_SCHEMA, ...(l.effort ? { effort: l.effort } : {}) }),
  (review, l) => {
    if (!review) return { lens: l.key, error: 'The reviewer returned no result', findings: [] }
    if (!review.findings.length) return { lens: l.key, summary: review.summary, frames_read: review.frames_read, findings: [] }
    return agent(
      `You are a skeptic. A reviewer (${l.key}) reported the problems below in a video project. Your job is to REFUTE each one. For each finding, open the frame or the code that it names and check the evidence yourself. ` +
      `Mark a finding real only when you reproduced it. If the evidence is not there, or the "problem" is the intended design described in the picture plan, mark it not real and say why.\n\n${CONTEXT}\n\n` +
      `FINDINGS\n${review.findings.map((f, i) => `${i}. [${f.severity}] ${f.where}: ${f.problem}\n   evidence: ${f.evidence}\n   proposed fix: ${f.fix}`).join('\n')}`,
      { label: 'verify:' + l.key, phase: 'Verify', schema: VERDICT_SCHEMA, ...(l.effort ? { effort: l.effort } : {}) })
      .then(v => ({
        lens: l.key, summary: review.summary, frames_read: review.frames_read,
        findings: review.findings.map((f, i) => {
          const verdict = v && (v.verdicts || []).find(x => x.index === i)
          return { ...f, verdict: verdict ? (verdict.real ? 'CONFIRMED' : 'REFUTED') : 'NOT VERIFIED', verify_reason: verdict ? verdict.reason : 'The skeptic returned no verdict for this finding' }
        }),
      }))
  })

const all = results.filter(Boolean)
const confirmed = all.flatMap(r => r.findings.filter(f => f.verdict === 'CONFIRMED').map(f => ({ lens: r.lens, ...f })))
const open = all.flatMap(r => r.findings.filter(f => f.verdict === 'NOT VERIFIED').map(f => ({ lens: r.lens, ...f })))
log(`${confirmed.length} confirmed, ${open.length} not verified, ${all.flatMap(r => r.findings).length - confirmed.length - open.length} refuted`)
return { confirmed, not_verified: open, by_lens: all, lenses_missing: LENSES.length - all.length }
