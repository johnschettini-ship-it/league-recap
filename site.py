#!/usr/bin/env python3
"""Build the league newspaper from posts/. Stdlib only.
  python site.py   ->  site/index.html + site/week-N.html
Headlines, scoreboxes, tiles and tables come from the verified facts JSON,
never from the LLM. The LLM only supplies story prose.
"""
import html, json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
POSTS, SITE = HERE / "posts", HERE / "site"
NAME = re.compile(r"_(\d{4})_w(\d+)_recap\.txt$")
E = html.escape

CSS = """
:root{--bg:#f2f0eb;--paper:#fffefb;--ink:#1c1b19;--muted:#6a655c;--rule:#2b2925;--soft:#f5f2ea;--accent:#8a2a1c;--up:#2f6b2a;--down:#8a2a1c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 'Old Standard TT',Georgia,'Times New Roman',serif}
.sheet{max-width:1680px;margin:0 auto;padding:22px 16px 48px;background:var(--paper);min-height:100vh;box-shadow:0 0 0 1px rgba(0,0,0,.05),0 6px 30px rgba(0,0,0,.06)}
@media(min-width:760px){.sheet{padding:28px 40px 56px}}
.mast{display:grid;grid-template-columns:1fr;align-items:center;gap:8px;text-align:center;padding-bottom:6px}
@media(min-width:760px){.mast{grid-template-columns:150px 1fr 150px}}
.mast a{color:inherit;text-decoration:none}
.mast h1{font:400 clamp(38px,9vw,92px)/1 'UnifrakturMaguntia','Old English Text MT',serif;margin:0;letter-spacing:.5px}
.ear{display:none;border:1px solid var(--rule);padding:6px 8px;font:700 11px/1.35 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:1px}
@media(min-width:760px){.ear{display:block}}
.ear small{display:block;font-weight:400;font-style:italic;text-transform:none;letter-spacing:0;font-size:12px}
.rules{border-top:4px solid var(--rule);border-bottom:1px solid var(--rule);height:7px;margin-top:6px}
.dateline{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 16px;font:700 12px/1.4 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:1.5px;padding:6px 0;border-bottom:3px double var(--rule);margin-bottom:22px}
.dateline i{font-weight:400;text-transform:none;letter-spacing:.5px;font-size:14px}
.lead{text-align:center;padding-bottom:4px}
h2.head{font:700 clamp(28px,5.4vw,58px)/1.02 'Old Standard TT',Georgia,serif;text-transform:uppercase;margin:0 auto 10px;max-width:22ch;letter-spacing:-.5px}
.deck{font:italic 400 clamp(17px,2.2vw,22px)/1.35 'IM Fell English',Georgia,serif;margin:0 auto 16px;max-width:60ch}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
@media(min-width:760px){.tiles{grid-template-columns:repeat(4,1fr)}}
.tile{padding:10px 12px;border-right:1px solid var(--rule)}
.tile:nth-child(2n){border-right:0}@media(min-width:760px){.tile:nth-child(2n){border-right:1px solid var(--rule)}.tile:last-child{border-right:0}}
@media(max-width:759px){.tile:nth-child(-n+2){border-bottom:1px solid var(--rule)}}
.tile .k{font:700 11px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:2px}
.tile .v{font:700 30px/1.15 'Old Standard TT',serif;font-variant-numeric:oldstyle-nums;margin:4px 0 2px}
.tile .w{font:italic 14px/1.3 'IM Fell English',serif;overflow-wrap:anywhere}
.orn{filter:grayscale(1) contrast(1.3);font-style:normal}
.body{margin-top:22px}
.cols{display:grid;grid-template-columns:1fr}
@media(min-width:760px){.cols{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1150px){.cols{grid-template-columns:repeat(3,1fr)}}
.cols .section-h{grid-column:1/-1}
.section-h{font:700 13px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:3px;text-align:center;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:6px 0;margin:0 0 14px;column-span:all}
.bout{min-width:0;padding:4px 18px 18px;margin-bottom:22px;border-bottom:1px solid var(--rule)}
@media(min-width:760px){.bout{border-left:1px solid var(--rule)}.bout:nth-of-type(2n+1){border-left:0;padding-left:0}.bout:nth-of-type(2n){padding-right:0}}
@media(min-width:1150px){.bout{padding:4px 22px 18px!important;border-left:1px solid var(--rule)!important}.bout:nth-of-type(3n+1){border-left:0!important;padding-left:0!important}.bout:nth-of-type(3n){padding-right:0!important}}
@media(max-width:759px){.bout{padding:4px 0 18px}}
.bout h4{font:700 24px/1.12 'Old Standard TT',serif;text-transform:uppercase;text-align:center;margin:4px 0 4px;letter-spacing:.3px;white-space:nowrap;overflow:hidden}
.fit-wrap{white-space:normal!important}
.bout .sub{text-align:center;font:italic 14px/1.3 'IM Fell English',serif;color:var(--muted);margin:0 0 10px}
.bout .sub::before,.bout .sub::after{content:"— "}.bout .sub::after{content:" —"}
.box{border-top:2px solid var(--rule);border-bottom:2px solid var(--rule);font:15px/1.3 'Old Standard TT',serif;margin:0 0 12px}
.box .row{display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:baseline;padding:5px 2px}
.box .row+.row{border-top:1px dotted var(--rule)}
.box .win{font-weight:700}.box .tm{overflow-wrap:anywhere;text-transform:uppercase;font-size:13px;letter-spacing:.5px}
.box .meta{font-size:12px;color:var(--muted);white-space:nowrap;font-style:italic}
.box .pts{font-weight:700;font-size:18px;min-width:58px;text-align:right;font-variant-numeric:oldstyle-nums tabular-nums}
.box .foot{border-top:1px solid var(--rule);padding:4px 2px;font:italic 13px/1.3 'IM Fell English',serif;color:var(--muted);text-align:center}
.bout p{margin:0 0 10px;text-align:justify;hyphens:auto;-webkit-hyphens:auto;text-indent:1.2em}
.bout p.lede{text-indent:0}
.bout .lede::first-letter{float:left;font:700 54px/.8 'Old Standard TT',serif;margin:5px 6px 0 0;padding:2px 4px;border:1px solid var(--rule)}
blockquote{margin:12px 6px;padding:8px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);text-align:center;font:italic 18px/1.45 'IM Fell English',serif}
.kicker{font:14px/1.45 'Old Standard TT',serif;margin:8px 0 0;text-align:center;text-indent:0!important}
.kicker b{font-variant:small-caps;letter-spacing:1px;margin-right:6px;color:var(--accent)}
.band h3{font:700 13px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:3px;text-align:center;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:6px 0;margin:0 0 10px}
.band{display:grid;grid-template-columns:1fr;gap:24px;margin-top:8px}
@media(min-width:900px){.band{grid-template-columns:2fr 1fr}}
.st2{display:grid;grid-template-columns:1fr;gap:0 28px}@media(min-width:760px){.st2{grid-template-columns:1fr 1fr}}
.band .side section{margin-bottom:22px}
table{width:100%;border-collapse:collapse;font:14px/1.25 'Old Standard TT',serif}
td,th{padding:5px 3px;border-bottom:1px dotted var(--rule);text-align:left}
th{font-size:11px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--rule)}
.n{text-align:right;font-variant-numeric:oldstyle-nums tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}
details{font:14px/1.5 'Old Standard TT',serif;border:1px solid var(--rule);padding:8px 10px}
summary{cursor:pointer;font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:12px}details article{margin-top:8px;font-family:system-ui,sans-serif;font-size:13px}
.archive{text-align:center}.archive a{display:inline-block;margin:0 8px 6px;color:var(--accent);font-style:italic}
footer{margin-top:36px;border-top:3px double var(--rule);padding-top:10px;font:italic 13px 'IM Fell English',serif;color:var(--muted);text-align:center}
"""


def wa(text):
    """WhatsApp/markdown markup -> safe HTML (one line)."""
    s = E(text)
    s = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", s)


def arrow(prev, now):
    if prev is None or prev == now:
        return ""
    d = prev - now
    return f' <span class="{"up" if d > 0 else "down"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>'


def headline(f, banner=""):
    c, h, l = f["closest"], f["high"], f["low"]
    head = banner or f"{h['manager']} Drops {h['pts']}; {l['manager']} Sinks to {l['pts']}"
    deck = f"{c['winner']} survives {c['loser']} by {c['margin']}."
    if f.get("upsets"):
        u = f["upsets"][0]
        deck = f"Upset: No. {u['winner_prev_rank']} {u['winner']} topples No. {u['loser_prev_rank']} {u['loser']}. " + deck
    return head, deck


def tiles(f):
    c, b = f["closest"], f["blowout"]
    items = [("👑 High", f["high"]["pts"], f["high"]["manager"]),
             ("💀 Low", f["low"]["pts"], f["low"]["manager"]),
             ("😬 Closest", c["margin"], f"{c['winner']} over {c['loser']}"),
             ("🔨 Blowout", b["margin"], f"{b['winner']} over {b['loser']}")]
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><div class="k"><span class="orn">{k.split(" ",1)[0]}</span> {k.split(" ",1)[1]}</div><div class="v">{v}</div><div class="w">{E(w)}</div></div>'
        for k, v, w in items) + "</div>"


def scorebox(g):
    rows = ""
    for side, cls in (("winner", "win"), ("loser", "")):
        rows += (f'<div class="row {cls}"><span class="tm">{E(g[side])}</span>'
                 f'<span class="meta">{g.get(side + "_record", "")} · #{g.get(side + "_rank", "")}'
                 f'{arrow(g.get(side + "_prev_rank"), g.get(side + "_rank"))}</span>'
                 f'<span class="pts">{g[side + "_pts"]}</span></div>')
    star = (g.get("winner_lineup") or {}).get("stars") or []
    foot = f"Margin {g['margin']}" + (f" · Star: {E(star[0]['player'])} {star[0]['pts']}" if star else "")
    return f'<div class="box">{rows}<div class="foot">{foot}</div></div>'


def banner_of(md):
    m = re.search(r"^BANNER:\s*(.+)$", md, flags=re.M)
    return m.group(1).strip(" *") if m else ""


def stories_html(md, f):
    out = []
    md = re.sub(r"^BANNER:.*$", "", md, flags=re.M)
    for block in re.split(r"^###\s*", md, flags=re.M):
        block = block.strip()
        if not block:
            continue
        title, _, body = block.partition("\n")
        game = next((g for g in f.get("results", []) if g["winner"] in block and g["loser"] in block), None)
        paras, couplet, kicker, cur = [], [], "", []
        lines = [l.strip() for l in body.splitlines()]
        i = 0
        while i < len(lines):
            l = lines[i]
            if l.startswith("🏆") or not l:                       # score line -> scorebox
                if cur: paras.append(" ".join(cur)); cur = []
            elif l.startswith("🎭"):
                if cur: paras.append(" ".join(cur)); cur = []
                couplet = [l.lstrip("🎭 ").strip()]
                if i + 1 < len(lines) and lines[i + 1] and not lines[i + 1].startswith("🎤"):
                    couplet.append(lines[i + 1]); i += 1
            elif l.startswith("🎤"):
                kicker = re.sub(r"^🎤\s*\*?\*?Kicker:?\*?\*?:?\s*", "", l)
            else:
                cur.append(l)
            i += 1
        if cur:
            paras.append(" ".join(cur))
        paras = [re.sub(r"[🔥🧊]\s*", "", p) for p in paras]          # decluttered prose
        orn = lambda h: re.sub(r"([🚑💸🔄])", r'<span class="orn">\1</span>', h)
        html_p = "".join(f'<p class="{"lede" if n == 0 else ""}">{orn(wa(p))}</p>' for n, p in enumerate(paras))
        quote = f"<blockquote>{'<br>'.join(wa(c) for c in couplet)}</blockquote>" if couplet else ""
        kick = f'<p class="kicker"><b>Kicker</b>{wa(kicker)}</p>' if kicker else ""
        t = title.strip(" *#")
        first, _, rest = t.partition(" ")
        orn = ""
        if rest and not any(ch.isalnum() for ch in first):             # leading emoji -> woodcut ornament
            orn, t = f'<span class="orn">{first}</span> ', rest
        sub = f'<p class="sub">{E(game["winner"])} vs. {E(game["loser"])}</p>' if game else ""
        out.append(f'<section class="bout"><h4>{orn}{E(t)}</h4>{sub}'
                   f'{scorebox(game) if game else ""}{html_p}{quote}{kick}</section>')
    return "".join(out)


def standings(f):
    head = "<tr><th>#</th><th>Manager</th><th>Rec</th><th class=n>PF</th><th>Strk</th></tr>"
    rows = [f"<tr><td>{s['rank']}</td><td>{E(s['manager'])}{arrow(s.get('prev_rank'), s['rank'])}</td><td>{s['record']}</td>"
            f"<td class=n>{s['pf']}</td><td>{s['streak']}</td></tr>" for s in f["standings"]]
    half = (len(rows) + 1) // 2
    return (f'<div class="st2"><table>{head}{"".join(rows[:half])}</table>'
            f'<table>{head}{"".join(rows[half:])}</table></div>')


def page(f, text, stories, weeks, title_prefix="", others=""):
    league = E(f["league"])
    head, deck = headline(f, banner_of(stories))
    desc = E(f"{head}. {deck}")
    archive = " · ".join(f'<a href="week-{w}.html">Week {w}</a>' for w in sorted(weeks, reverse=True))
    wa_html = "<br>\n".join(wa(l) for l in text.splitlines())
    cols = (f'<div class="cols"><div class="section-h">The Matchups</div>{stories_html(stories, f)}</div>'
            if stories else f'<div class="cols"><article>{wa_html}</article></div>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_prefix}{league} Gazette</title>
<meta property="og:title" content="{league} Gazette — Week {f['week']}">
<meta property="og:description" content="{desc}"><meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=IM+Fell+English:ital@0;1&display=swap" rel="stylesheet">
<meta name='color-scheme' content='light'><style>{CSS}</style></head><body><main class="sheet">
<header class="mast">
<div class="ear">Week {f['week']} Edition<small>Waivers &amp; wagers within</small></div>
<a href="index.html"><h1>The {league} Gazette</h1></a>
<div class="ear">Price: One FAAB Dollar<small>{f['teams']} clubs reporting</small></div>
</header>
<div class="rules"></div>
<div class="dateline"><span>Vol. {f['season']} · No. {f['week']}</span><i>“All the Scores That Are Fit to Print”</i><span>Late City Final</span></div>
<section class="lead"><h2 class="head">{E(head)}</h2><p class="deck">{E(deck)}</p>{tiles(f)}</section>
<div class="body">
{cols}
<div class="band">
<section><h3>The Standings</h3>{standings(f)}</section>
<div class="side">
<section><h3>Back Issues</h3><nav class="archive">{archive}</nav></section>
<section><details><summary>📱 Wire copy (WhatsApp)</summary><article>{wa_html}</article></details></section>
</div>
</div>
</div>
<footer>{others}Every figure verified against the Sleeper wire. The jokes are not.</footer>
</main>
<script>
/* one-line headlines: shrink until they fit; wrap only as a last resort */
function fit(){{document.querySelectorAll('.bout h4').forEach(function(h){{
  h.classList.remove('fit-wrap');h.style.fontSize='';var s=parseFloat(getComputedStyle(h).fontSize);
  while(h.scrollWidth>h.clientWidth&&s>14){{s-=.5;h.style.fontSize=s+'px';}}
  if(h.scrollWidth>h.clientWidth)h.classList.add('fit-wrap');}});}}
document.fonts&&document.fonts.ready.then(fit);fit();addEventListener('resize',fit);
</script></body></html>"""


def load(lid):
    issues = {}
    for p in POSTS.glob(f"{lid}_*_recap.txt"):
        m = NAME.search(p.name)
        facts = p.with_name(p.name.replace(".txt", ".facts.json"))
        if m and facts.exists():
            st = p.with_name(p.name.replace(".txt", ".stories.md"))
            text = "\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith("📰"))
            issues[(int(m[1]), int(m[2]))] = (json.loads(facts.read_text(encoding="utf-8")), text.strip(),
                                              st.read_text(encoding="utf-8") if st.exists() else "")
    return issues


def placeholder(name):
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{E(name)} Gazette</title><style>{CSS}</style><main class=sheet><header class=mast><h1>The {E(name)} Gazette</h1></header>"
            f"<p class=deck style='text-align:center;margin-top:24px'>First edition hits the stands Wednesday morning.</p></main>")


def build():
    lf = HERE / "leagues.json"
    leagues = json.loads(lf.read_text(encoding="utf-8")) if lf.exists() else [{"id": "", "path": ""}]
    papers = []
    for lg in leagues:
        issues = load(lg["id"])
        name = lg.get("display_name") or (issues[max(issues)][0]["league"] if issues else (lg["path"] or "League").replace("-", " ").title())
        papers.append((lg, issues, name))
    for lg, issues, name in papers:
        out = SITE / lg["path"] if lg["path"] else SITE
        out.mkdir(parents=True, exist_ok=True)
        others = ""                                   # papers never link to each other
        if not issues:
            (out / "index.html").write_text(placeholder(name), encoding="utf-8")
            print(f"{name}: no issues yet; placeholder")
            continue
        latest = max(issues)
        weeks = [w for (s, w) in issues if s == latest[0]]
        for (s, w), (f, text, stories) in issues.items():
            if s == latest[0]:
                (out / f"week-{w}.html").write_text(page(f, text, stories, weeks, f"Week {w} · ", others), encoding="utf-8")
        f, text, stories = issues[latest]
        (out / "index.html").write_text(page(f, text, stories, weeks, "", others), encoding="utf-8")
        print(f"{name}: {len(weeks)} issue(s); front page = week {latest[1]}")


if __name__ == "__main__":
    build()
