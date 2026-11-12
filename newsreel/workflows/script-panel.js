export const meta = {
  name: 'gazette-newsreel-script',
  description: 'Write the newsreel narration for one edition of the Gazette video, judge it blind, and check it against the facts',
  whenToUse: 'Each week, after tools/brief.py. Pass the content of build/<edition>.brief.json as args, plus house_script, printed_lines, facts_file and reference_files.',
  phases: [
    { title: 'Write', detail: 'three writers in the house voice, each with a different comic angle' },
    { title: 'Judge', detail: 'three blind judges: comedy and period voice, a league member, standards' },
    { title: 'Synthesize', detail: 'build the final script from the winner and the best lines' },
    { title: 'Verify', detail: 'checks by code, a fact check and a rules check, with a repair loop' },
  ],
}

// ---------- input: the brief of the edition (tools/brief.py), plus the house style ----------
const A = args || {}
if (!A.facts || !A.segments || !A.names || !A.hooks || !Array.isArray(A.order)) return { error: 'Pass the content of build/<edition>.brief.json as args (facts, segments, names, hooks, order)' }
const NAMES = A.names                       // team name -> number of spoken words
const SPOKEN = A.spoken || {}
const WPM = A.words_per_minute || 194       // measured with the approved voice: formula words per minute
const MIN_W = A.min_words || 205, MAX_W = A.max_words || 228
const MAX_NAMES = A.max_name_mentions || 15, MAX_DEC = A.max_decimals || 10, MAX_SENT = A.max_sentences || 27, MAX_BANG = 8, MAX_SECONDS = A.max_seconds || 88.5
const ORDER = A.order                         // the segments of the edition, from tools/brief.py

const HOUSE = A.house_voice || `THE HOUSE VOICE (fixed): a CINEMA NEWSREEL ANNOUNCER of about 1940, who reads the front page of the paper to a theater audience.
The announcer talks TO the audience ("ladies and gentlemen", "folks"), calls out each headline, and uses action verbs in the present tense ("storms", "topples", "bags", "blazes").
Bright, brisk, upbeat, a little pompous, never mean. Each story is an ANNOUNCEMENT: first the headline, then the fact, then one dry quip at most. The quip is the second beat, not the story.
Newsreel and newsroom idiom is welcome: "Extra, extra", "Flash!", "stop the presses", "hot off the wire", "hold the phone", "what a week", "and how", "takes it on the chin", "by a whisker",
"regrets to announce", "in lieu of flowers". Modern slang is not. Never use a period term that is offensive today.
NOT THE VOICE: a crime film, a police report, a bookmaker or a hard-boiled narrator. Do not use "wanted for questioning", "oddsmaker", "bookie", "the outfit", "the racket", "the cellar" for the last place,
or other underworld, police or speakeasy words. Do not narrate in wry asides with verbs of state ("is also present", "has not moved", "is now a fair question"): announce what happened.
The one "WANTED" poster is a fixed picture: announce it as a newsreel item, with the word "Wanted" one time and no other police word.`

const SHOW = `THE PRODUCT
"The ${A.league} Gazette" is a weekly newspaper for a ${A.teams.length}-team fantasy football league of friends. This is its VIDEO EDITION for Week ${A.week}: a newsreel of about 85 seconds,
shown in the league's group chat on phones. It looks like an old newspaper and a 1930s-1940s cinema newsreel.
${HOUSE}
The viewers are the league's own managers. They hear each line ONE time with a caption on screen. They want to hear their team named, and they enjoy a fair roast of a bad week.
THE MODEL: the script of an earlier edition, which the owner approved. Match its voice, its pace and its sentence length. Do not reuse its jokes:
${A.house_script || '(not supplied)'}
You may keep ONE line of the model as a running gag of the series, word for word or adapted. Every other joke must be new.${A.replace_script ? `
THE SCRIPT TO REPLACE (the same week and the same facts). ${A.replace_reason || ''}
${A.replace_script}
Its facts and its picture cues are correct. You may keep a joke of this script when the joke fits the house voice.` : ''}
${(A.printed_lines || []).length ? 'The Gazette printed these lines in its text edition of this week. You may reuse or adapt at most one:\n' + A.printed_lines.map(l => '  "' + l + '"').join('\n') : ''}
${(A.reference_files || []).length ? 'For reference only (tone, and what the paper printed this week): ' + A.reference_files.join(' and ') + '.' : ''}
${A.facts_file ? 'The complete facts file is ' + A.facts_file + '.' : ''} You may read these files. Do not change any file.`

const SEGMENTS = A.segments
const FACTS = 'VERIFIED FACTS (the ONLY permitted source of scores, names, ranks, records and odds; copy every number exactly; no rounding and no new math)\n' + A.facts +
  '\nA streak is given in words in the facts. Say it in words; never print a code such as W3.'

const RULES = `HARD RULES (from the Gazette's own writer contract, plus the video's needs)
R1  Never invent or change scores, players, transactions, records, ranks, odds or results.
R2  Copy every number exactly as written in the facts: no rounding, no new totals or math. You may put two facts side by side and let the listener compare them.
R3  Only mention players and teams that appear in the facts. In the caption, spell each team name and each player name exactly as in the facts.
R4  Report what happened; do not advise anyone what to do.
R5  Humor targets fantasy performance and league behavior only. Never touch a real player's or a manager's personal life, family, health, legal matters, appearance,
    or any protected characteristic. A player who scored 0.0 simply scored 0.0; do not guess why.
R6  Every line must be understood on one hearing. No sentence over 18 words. No profanity.
R7  A pun must work when heard, not only when read, and the sentence must still make sense to a listener who misses the pun.
R8  The facts file has a list "used_pun_names": the puns that the paper printed in earlier weeks. Do not copy one of them. A new turn on a team name is permitted.`

const SPEECH = `SPEECH LIMITS (the narration is spoken by a speech engine)
P1  Team names are spoken like this, so a name costs time. Use at most ${MAX_NAMES} team-name mentions in the whole script:
      ${Object.keys(NAMES).map(n => n + (SPOKEN[n] && SPOKEN[n] !== n ? ' = "' + SPOKEN[n] + '"' : '') + ' (' + NAMES[n] + ')').join('   ')}
    The number in brackets is the count of spoken words.
P2  A decimal score is hard to hear. Use at most ${MAX_DEC} numbers with a decimal point in the whole script, and say each one only once.
P3  Write a record as it is in the facts, for example 6-2 or 67-32. It is spoken "six and two", "sixty-seven and thirty-two".
P4  Do not use the words "winless" or "as is custom". Do not write a three-word sentence of the form "<Name> then <verb>." The engine slurs them.
P5  Do not write a one-word sentence.
P6  Write a negative score as it is in the facts, for example -0.3. It is spoken "minus zero point three".
P7  Do not put a word that ends in "s" directly before a team name that starts with "s". The engine runs the two together.`

const LIMITS = `LENGTH LIMITS (the goal is a video of 84 to 90 seconds; the pace is brisk)
L1  ${MIN_W} to ${MAX_W} SPOKEN words. Count a team name by its spoken words (rule P1), a decimal number as 5 words, a negative decimal number as 6 words,
    a whole number as 2 words, a record such as 6-2 as 3 words, a record such as 67-32 as 5 words.
L2  At most ${MAX_SENT} sentences in total. Each segment has 1 to 4 sentences.
L3  All ${ORDER.length} segments, in this order: ${ORDER.join(', ')}. No other segment.
L4  At most ${MAX_BANG} exclamation marks in the whole script.
L5  The pictures enter on words. Each segment text above says which word a sentence must have. Code checks this.
Return each sentence in "cap", the on-screen caption, with team names, player names and numbers exactly as in the facts. Code makes the spoken text from the caption.`

const NUM = /\d+(?:\.\d+)?/g
// The numbers that a script can use: the numbers of the facts, without the numbers of the labels G1, G2, ...
const ALLOWED = new Set((A.facts.replace(/^G\d+\s/gm, '').match(NUM) || []))
const NEGATIVE = new Set((A.facts.match(/(?:^|[\s(])-\d+(?:\.\d+)?/g) || []).map(x => x.replace(/^[\s(]*-/, '')))

// ---------- deterministic helpers ----------
const namesLongFirst = Object.keys(NAMES).sort((a, b) => b.length - a.length)
function spokenWords(cap) {
  let t = ' ' + String(cap || '') + ' ', n = 0
  for (const name of namesLongFirst) {
    const parts = t.split(name)
    if (parts.length > 1) { n += (parts.length - 1) * NAMES[name]; t = parts.join(' ') }
  }
  const said = x => (Number(x) <= 20 || Number(x) % 10 === 0) ? 1 : 2      // "seven" is one word, "sixty-seven" is two
  t = t.replace(/\b(\d+)-(\d+)\b/g, (m, a, b) => { n += 1 + said(a) + said(b); return ' ' })
  t = t.replace(/-\d+\.\d+/g, () => { n += 6; return ' ' })
  t = t.replace(/\d+\.\d+/g, () => { n += 5; return ' ' })
  t = t.replace(/\d+/g, () => { n += 2; return ' ' })
  return n + t.trim().split(/\s+/).filter(w => /[A-Za-z]/.test(w)).length
}
function nameMentions(cap) {
  let t = String(cap || ''), n = 0
  for (const name of namesLongFirst) { const parts = t.split(name); n += parts.length - 1; t = parts.join(' ') }
  return n
}
function stats(script) {
  const B = script.beats.length
  let S = 0, W = 0, names = 0, decimals = 0, bangs = 0
  for (const b of script.beats) for (const s of b.sentences) {
    S++; W += spokenWords(s.cap); names += nameMentions(s.cap)
    decimals += (String(s.cap).match(/\d+\.\d+/g) || []).length; bangs += (String(s.cap).match(/!/g) || []).length
  }
  // 2.7 s film leader + 3.0 s end card; the measured rate of the approved voice; 0.35 s between sentences; 0.85 s between segments
  const seconds = 5.7 + W * 60 / WPM + 0.35 * (S - B) + 0.85 * (B - 1)
  return { beats: B, sentences: S, spoken_words: W, name_mentions: names, decimal_numbers: decimals, exclamations: bangs, seconds: Math.round(seconds * 10) / 10 }
}
// A cue word is a whole word: "odds" is not in "oddsmaker", and 0.0 is not in 30.0. The same rule is in tools/plan.py (cue_pattern).
const esc = s => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const has = (cap, word) => {
  const w = String(word).trim()
  const re = /^-?\d+(\.\d+)?$/.test(w) ? new RegExp('(?<![\\d.])' + esc(w) + '(?!\\d|\\.\\d)') : new RegExp('(?<![A-Za-z0-9])' + esc(w) + '(?![A-Za-z0-9])', 'i')
  return re.test(String(cap))
}
function hookProblems(script) {
  const v = []
  const firstSentence = {}
  for (const h of A.hooks) {
    const beat = script.beats.find(b => b.id === h.segment)
    if (!beat) { v.push('Segment ' + h.segment + ' is not in the script; it has the cue for ' + h.picture); continue }
    const sents = beat.sentences || []
    const pool = h.last_sentence ? sents.slice(-1) : sents
    const i = pool.findIndex(s => h.any.some(w => has(s.cap, w)))
    if (i < 0) {
      v.push('Picture cue missing in ' + h.segment + ': ' + (h.last_sentence ? 'the last sentence' : 'one sentence') + ' must have ' + h.any.map(w => '"' + w.trim() + '"').join(' or ') + ', to bring in ' + h.picture)
    } else if (h.own_sentence) {
      const key = h.segment + ':' + i
      if (firstSentence[key]) v.push('Two pictures enter on the same sentence in ' + h.segment + ' (' + firstSentence[key] + ' and ' + h.picture + '): give each its own sentence, and do not name a team of a later game in an earlier sentence')
      firstSentence[key] = h.picture
    }
  }
  return v
}
function mech(script) {
  const v = []
  if (!script || !Array.isArray(script.beats) || !script.beats.length) return ['The script has no segments']
  const ids = script.beats.map(b => b.id)
  if (ids.join(',') !== ORDER.join(',')) v.push('The segments must be exactly ' + ORDER.join(', ') + ' in this order; got ' + ids.join(','))
  const seen = {}
  for (const b of script.beats) {
    if (!Array.isArray(b.sentences) || b.sentences.length < 1 || b.sentences.length > 4) v.push('Segment ' + b.id + ' must have 1 to 4 sentences')
    for (const s of (b.sentences || [])) {
      const cap = String(s.cap || '')
      if (!cap.trim()) v.push('Segment ' + b.id + ' has an empty sentence')
      if (cap.trim().split(/\s+/).length > 18) v.push('Sentence over 18 words in ' + b.id + ': "' + cap + '"')
      if (cap.trim().split(/\s+/).length === 1) v.push('One-word sentence in ' + b.id + ': "' + cap + '"')
      for (const num of (cap.match(NUM) || [])) {
        if (!ALLOWED.has(num)) v.push('The number ' + num + ' is not in the verified facts, in ' + b.id + ': "' + cap + '"')
        if (/\./.test(num)) { if (seen[num]) v.push('The decimal number ' + num + ' is said more than once (rule P2)'); seen[num] = true }
        if (NEGATIVE.has(num) && !cap.includes('-' + num) && !/minus/i.test(cap)) v.push('The facts give -' + num + ', a negative score; the caption has ' + num + ' with no minus sign, in ' + b.id + ': "' + cap + '"')
      }
      if (/winless|as is custom/i.test(cap)) v.push('Forbidden phrase (rule P4) in ' + b.id + ': "' + cap + '"')
      if (/\b[WL]\d+\b/.test(cap)) v.push('A streak code such as W5 is printed in ' + b.id + ': "' + cap + '"; say it in words')
      const lower = cap.toLowerCase()
      for (const name of Object.keys(NAMES)) {
        for (let i = lower.indexOf(name.toLowerCase()); i >= 0; i = lower.indexOf(name.toLowerCase(), i + 1)) {      // every place where the name occurs
          if (cap.substr(i, name.length) !== name) { v.push('Team name not spelled exactly as in the facts ("' + name + '") in ' + b.id + ': "' + cap + '"'); break }
        }
        const m = cap.match(new RegExp('(\\w*s)\\s+' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
        if (m && /^s/i.test(name)) v.push('Rule P7: "' + m[1] + ' ' + name + '" runs together when spoken, in ' + b.id + ': "' + cap + '"')
      }
    }
  }
  v.push(...hookProblems(script))
  const st = stats(script)
  if (st.spoken_words > MAX_W) v.push('Too long: ' + st.spoken_words + ' spoken words; the limit is ' + MAX_W)
  if (st.spoken_words < MIN_W) v.push('Too short: ' + st.spoken_words + ' spoken words; the minimum is ' + MIN_W)
  if (st.sentences > MAX_SENT) v.push('Too many sentences: ' + st.sentences + '; the limit is ' + MAX_SENT)
  if (st.name_mentions > MAX_NAMES) v.push('Too many team-name mentions: ' + st.name_mentions + '; the limit is ' + MAX_NAMES)
  if (st.decimal_numbers > MAX_DEC) v.push('Too many decimal numbers: ' + st.decimal_numbers + '; the limit is ' + MAX_DEC)
  if (st.exclamations > MAX_BANG) v.push('Too many exclamation marks: ' + st.exclamations + '; the limit is ' + MAX_BANG)
  if (st.seconds > MAX_SECONDS) v.push('Predicted length ' + st.seconds + ' s is over ' + MAX_SECONDS + ' s')
  return v
}
const show = script => script.beats.map(b => b.id + ':  ' + b.sentences.map(s => s.cap).join('  |  ')).join('\n')

const SCRIPT_SCHEMA = {
  type: 'object',
  properties: {
    beats: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string', enum: ORDER },
      sentences: { type: 'array', items: { type: 'object', properties: { cap: { type: 'string' } }, required: ['cap'] } },
    }, required: ['id', 'sentences'] } },
    notes: { type: 'string', description: 'What you chose and why. Short.' },
  },
  required: ['beats', 'notes'],
}
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      candidate: { type: 'string', description: 'The candidate letter' },
      funny: { type: 'number', description: '1 (no laugh) to 10 (several real laughs)' },
      period_voice: { type: 'number', description: '1 to 10: does it sound like the house voice, a cinema newsreel announcer of about 1940, without a false note and without the register of a crime film' },
      clarity: { type: 'number', description: '1 to 10: understood on one hearing, names and numbers included' },
      overall: { type: 'number', description: '1 to 10' },
      best_lines: { type: 'array', items: { type: 'string' } },
      weak_lines: { type: 'array', items: { type: 'string' } },
      risks: { type: 'array', items: { type: 'string' }, description: 'Fact, rule, taste or speech problems. Empty if none.' },
    }, required: ['candidate', 'funny', 'period_voice', 'clarity', 'overall', 'best_lines', 'weak_lines', 'risks'] } },
    ranking: { type: 'array', items: { type: 'string' }, description: 'Candidate letters, best first' },
    segment_verdicts: { type: 'array', items: { type: 'object', properties: {
      segment: { type: 'string', enum: ORDER },
      best_candidate: { type: 'string' },
      reason: { type: 'string' },
    }, required: ['segment', 'best_candidate', 'reason'] } },
    summary: { type: 'string' },
  },
  required: ['scores', 'ranking', 'segment_verdicts', 'summary'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    violations: { type: 'array', items: { type: 'object', properties: {
      sentence: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' },
    }, required: ['sentence', 'problem', 'fix'] } },
  },
  required: ['pass', 'violations'],
}
const BRIEF = [SHOW, SEGMENTS, FACTS, RULES, SPEECH, LIMITS].join('\n\n')
const COUNTS = `${MIN_W} to ${MAX_W} spoken words, at most ${MAX_SENT} sentences, at most ${MAX_NAMES} team-name mentions, at most ${MAX_DEC} decimal numbers, at most ${MAX_BANG} exclamation marks`

// ---------- Write ----------
phase('Write')
const LENSES = A.lenses || [
  { key: 'headline-call', text: 'Your comic angle: THE HEADLINE CALL. The announcer calls a short headline before each story ("Flash!", "Stop the presses:", "Upset!"), with alliteration and a strong verb, then gives the fact, then one dry quip. Energy first, then the needle.' },
  { key: 'to-the-crowd', text: 'Your comic angle: THE CROWD. The announcer plays to the theater audience: direct address, a question and its answer ("And who sits on top? ..."), mock cheers for the winners and mock sympathy for the losers. Warm and loud; the teams are friends.' },
  A.replace_script
    ? { key: 'revision', text: 'Your comic angle: THE REVISION. Start from the script to replace. Keep its best jokes and its order of facts. Change the register line by line to the house voice: turn each aside into an announcement with an action verb, and remove every word of the crime-film register.' }
    : { key: 'running-story', text: 'Your comic angle: THE RUNNING STORY. A newsreel follows its stories from week to week. Use the facts that connect to last week (the Main Event the paper billed, the streaks, the team that stays in last place) and announce the week as the next chapter. One callback to the model script is welcome.' },
]
const written = await parallel(LENSES.map(l => () => agent(
  `You are a comedy writer. Write the narration for an old-time newsreel video about one week of a fantasy football league.\n\n${BRIEF}\n\n${l.text}\n\n` +
  `Work method: read the facts, choose the one or two facts that each segment needs, write the lines, then count: spoken words (rule L1), sentences, team-name mentions, decimal numbers and exclamation marks. ` +
  `Adjust until every limit holds. Check each picture cue (rule L5). Check each number and each name against the facts, character by character. Return the complete script.`,
  { label: 'write:' + l.key, phase: 'Write', schema: SCRIPT_SCHEMA })))
const variants = written.map((s, i) => s && Array.isArray(s.beats) ? { key: LENSES[i].key, script: s } : null).filter(Boolean)
if (!variants.length) return { error: 'No script was returned' }
log(variants.length + ' of 3 scripts returned: ' + variants.map(v => v.key + ' ' + stats(v.script).spoken_words + ' spoken words, ' + mech(v.script).length + ' problems found by code').join('; '))

// ---------- Judge (blind) ----------
phase('Judge')
const pool = [variants[2], variants[0], variants[1]].filter(Boolean)
const LETTERS = ['A', 'B', 'C']
const cands = pool.map((p, i) => ({ letter: LETTERS[i], key: p.key, script: p.script, st: stats(p.script), problems: mech(p.script) }))
const candText = cands.map(c => `CANDIDATE ${c.letter}  (${c.st.spoken_words} spoken words, about ${c.st.seconds} seconds, ${c.st.sentences} sentences)\n${show(c.script)}` +
  (c.problems.length ? `\nProblems found by code: ${c.problems.join(' ; ')}` : '')).join('\n\n')
const JUDGES = [
  { key: 'comedy', text: 'You are a veteran comedy editor who loves old newsreels and vintage newspapers. Two questions: where are the real laughs, and does the house voice hold without a false note: does it sound like a cinema newsreel announcer of about 1940? A modern phrase in an old-time script is a fault. A line that sounds like a crime film, a police report, a bookmaker or a hard-boiled narrator is a fault. A line that is only pleasant scores low. A joke copied from the model script, other than one running gag, is a fault. Name the funniest and the deadest line of each candidate.' },
  { key: 'member', text: 'You are a manager in this league, watching the video in the group chat on your phone. Judge as a friend among friends: do you hear the names clearly, do the numbers land, is the roast fair and funny to the person roasted, does it hold your attention for 85 seconds, and would you send it to someone outside the league. Penalize any line that needs a second hearing.' },
  { key: 'standards', text: 'You are a standards editor. Check each candidate line by line against the verified facts and the hard rules. A funny line that states a wrong number, pairs a score with the wrong team, computes new math, jokes about a person and not a performance, or uses a period term that is offensive today must be flagged. Also score the comedy, but weight accuracy and tone.' },
]
const judged = await parallel(JUDGES.map(j => () => agent(
  `${j.text}\n\nYou will judge ${cands.length} versions of the same newsreel script. You do not know who wrote them. Judge only the text.\n\n${BRIEF}\n\n${candText}\n\n` +
  `Score every candidate, rank them best first, and for every segment say which candidate has the best version and why. Use the full range of the scales.`,
  { label: 'judge:' + j.key, phase: 'Judge', schema: JUDGE_SCHEMA })))
const judges = judged.map((r, i) => r ? { key: JUDGES[i].key, r } : null).filter(Boolean)
if (!judges.length) return { error: 'No judge returned a result', variants }
const avg = xs => xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length * 10) / 10 : null
const board = cands.map(c => {
  const rows = judges.map(j => (j.r.scores || []).find(s => String(s.candidate).trim().toUpperCase().replace('CANDIDATE ', '') === c.letter)).filter(Boolean)
  return { letter: c.letter, key: c.key, spoken_words: c.st.spoken_words, seconds: c.st.seconds,
    funny: avg(rows.map(r => r.funny)), period_voice: avg(rows.map(r => r.period_voice)), clarity: avg(rows.map(r => r.clarity)), overall: avg(rows.map(r => r.overall)),
    firsts: judges.filter(j => String((j.r.ranking || [])[0] || '').trim().toUpperCase().replace('CANDIDATE ', '') === c.letter).length }
})
log('Scores: ' + board.map(b => `${b.key} funny ${b.funny} voice ${b.period_voice} overall ${b.overall}`).join(' | '))

// ---------- Synthesize ----------
phase('Synthesize')
const judgeText = judges.map(j => `JUDGE (${j.key})\n` + JSON.stringify(j.r, null, 1)).join('\n\n')
const boardText = board.map(b => `Candidate ${b.letter}: funny ${b.funny}, period voice ${b.period_voice}, clarity ${b.clarity}, overall ${b.overall}, ranked first by ${b.firsts} of ${judges.length} judges`).join('\n')
let final = await agent(
  `You are the head writer. Build the FINAL newsreel script from the judged candidates.\n\n${BRIEF}\n\n${candText}\n\nAVERAGE SCORES\n${boardText}\n\n${judgeText}\n\n` +
  `Method: start from the best-ranked candidate. For each segment, take the version the judges preferred. Graft in the lines the judges named as best. Remove or repair every line a judge flagged. ` +
  `Keep ONE consistent announcer voice from start to end; when you graft a line from another candidate, rewrite it into that voice. ` +
  `Then count: ${COUNTS}. Adjust until every limit holds. Check each picture cue (rule L5). Check each number and each name against the facts, character by character. ` +
  `In "notes", state which candidate was the base and which lines came from other candidates.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SCRIPT_SCHEMA })
if (!final || !Array.isArray(final.beats)) {
  const best = board.slice().sort((a, b) => (b.overall || 0) - (a.overall || 0))[0]
  final = cands.find(c => c.letter === best.letter).script
  log('The synthesis agent returned nothing; the best-ranked script is used: ' + best.key)
}

// ---------- Verify, with a repair loop ----------
phase('Verify')
let verification = null
const history = []
for (let round = 0; round < 3; round++) {
  const m = mech(final)
  const text = show(final)
  const [fact, rule] = await parallel([
    () => agent(
      `You are a fact checker. Your job is to REFUTE this script: find every claim that the verified facts do not support.\n\n${FACTS}\n\n${SEGMENTS}\n\nTHE SCRIPT\n${text}\n\n` +
      (A.facts_file ? `You may also open the complete facts file at ${A.facts_file} to confirm a detail. Do not change any file.\n` : '') +
      `Check each sentence. For each number, confirm that it belongs to the team, the player and the event that the sentence gives it. A score paired with the wrong team, two scores swapped, ` +
      `a rank that is the rank after the week when the sentence means before (or the reverse), a streak or record that is not in the facts, a sum or a difference that the facts do not state, ` +
      `a claim such as "first", "only", "best of the season" or "record" that the facts do not state, a claim about an earlier week that the facts do not state, ` +
      `and a player or team that is not in the facts are all violations. ` +
      `If you are not sure that a claim is supported, report it. Set pass to true only when you find no violation.`,
      { label: 'verify:facts r' + (round + 1), phase: 'Verify', schema: VERDICT_SCHEMA }),
    () => agent(
      `You are a standards editor. Your job is to find every breach of the rules in this script.\n\n${RULES}\n\n${SPEECH}\n\n${SEGMENTS}\n\n${SHOW}\n\nTHE SCRIPT\n${text}\n\n` +
      `Check each sentence for: a joke about a person and not a fantasy performance; a guess at why a player scored what he scored; advice; profanity; a period term that is offensive today; ` +
      `a modern phrase that breaks the old-time voice; a line in the register that the house voice forbids (a crime film, a police report, a bookmaker, a hard-boiled aside); a pun that fails when heard; a line that cannot be understood on one hearing; a line that does not fit the picture of its segment; ` +
      `a joke copied from the model script, other than one running gag; and a team name or a player name not spelled exactly as in the facts. ` +
      `Report only real breaches; do not report matters of taste. Set pass to true only when you find no breach.`,
      { label: 'verify:rules r' + (round + 1), phase: 'Verify', schema: VERDICT_SCHEMA }),
  ])
  const factV = fact ? (fact.violations || []) : [{ sentence: '', problem: 'The fact checker returned no result', fix: 'Run the check again' }]
  const ruleV = rule ? (rule.violations || []) : [{ sentence: '', problem: 'The rules checker returned no result', fix: 'Run the check again' }]
  const clean = m.length === 0 && fact && rule && fact.pass && rule.pass && factV.length === 0 && ruleV.length === 0
  verification = { round: round + 1, mechanical: m, facts: factV, rules: ruleV, pass: clean, stats: stats(final) }
  history.push({ round: round + 1, mechanical: m.length, facts: factV.length, rules: ruleV.length })
  log(`Verify round ${round + 1}: ${m.length} by code, ${factV.length} fact, ${ruleV.length} rule problems; ${verification.stats.spoken_words} spoken words, ${verification.stats.seconds} s`)
  if (clean || round === 2) break
  const problems = [
    ...m.map(x => 'FOUND BY CODE: ' + x),
    ...factV.map(x => `FACT: "${x.sentence}" - ${x.problem} Suggested fix: ${x.fix}`),
    ...ruleV.map(x => `RULE: "${x.sentence}" - ${x.problem} Suggested fix: ${x.fix}`),
  ].join('\n')
  const fixed = await agent(
    `You are the head writer. Repair this newsreel script. Change only what the problems below require, and keep every good joke and the one announcer voice.\n\n${BRIEF}\n\nTHE SCRIPT\n${JSON.stringify({ beats: final.beats }, null, 1)}\n\nPROBLEMS TO REPAIR\n${problems}\n\n` +
    `If a checker's finding is wrong, because the facts support the line, keep the line and say so in "notes". A problem found by code is never wrong. ` +
    `After the repair, count again: ${COUNTS}. Check each picture cue (rule L5). Return the complete script.`,
    { label: 'repair r' + (round + 1), phase: 'Verify', schema: SCRIPT_SCHEMA })
  if (fixed && Array.isArray(fixed.beats)) final = fixed
  else { log('The repair agent returned nothing; the loop stops with open problems'); break }
}
if (!verification.pass) log('NOT CLEAN after ' + verification.round + ' round(s). Open problems are in the result.')

return {
  final, verification, history, board,
  letters: cands.map(c => ({ letter: c.letter, key: c.key })),
  judges: judges.map(j => ({ key: j.key, ranking: j.r.ranking, summary: j.r.summary, segment_verdicts: j.r.segment_verdicts, scores: j.r.scores })),
  variants: variants.map(v => ({ key: v.key, stats: stats(v.script), mechanical: mech(v.script), text: show(v.script), notes: v.script.notes })),
}
