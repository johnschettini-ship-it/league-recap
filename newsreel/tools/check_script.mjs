// Run the code checks of the script panel (workflows/script-panel.js) on one saved script, without agents.
// Usage: node tools/check_script.mjs <edition>        reads build/<edition>.brief.json and scripts/<edition>.script.json
// Prints the counts and every problem. Exit code 1 when there is a problem.
import fs from 'fs'
const ed = process.argv[2]
if (!ed) { console.error('Usage: node tools/check_script.mjs <edition>'); process.exit(2) }
let src = fs.readFileSync(new URL('../workflows/script-panel.js', import.meta.url), 'utf8').replace('export const meta', 'const meta')
src = src.slice(0, src.indexOf('// ---------- Write ----------')) + '\nreturn { mech, stats }'
const brief = JSON.parse(fs.readFileSync(`build/${ed}.brief.json`, 'utf8'))
Object.assign(brief, { min_words: 212, max_words: 236, max_name_mentions: 18, max_sentences: 28, max_seconds: 92 }, brief.limits || {})
const { mech, stats } = await new Function('args', 'agent', 'parallel', 'phase', 'log', 'return (async () => {' + src + '})()')(brief, null, null, () => {}, () => {})
const s = JSON.parse(fs.readFileSync(`scripts/${ed}.script.json`, 'utf8'))
const problems = mech(s)
console.log(ed, JSON.stringify(stats(s)))
for (const p of problems) console.log('  -', p)
process.exit(problems.length ? 1 : 0)
