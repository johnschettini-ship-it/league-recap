#!/usr/bin/env python3
"""Build the league newspaper from posts/. Stdlib only.
  python site.py   ->  site/index.html + site/week-N.html
Headlines, scoreboxes, tiles and tables come from the verified facts JSON,
never from the LLM. The LLM only supplies story prose.
"""
import html, json, re, pathlib
import comic
import theme

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
.mast h1{font:400 clamp(38px,9vw,92px)/1.05 'UnifrakturMaguntia','Old English Text MT',serif;margin:0;letter-spacing:.5px;white-space:nowrap;overflow:hidden}
.mast a{min-width:0;display:block}.mast h1.fit-wrap{white-space:normal}
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
.features{display:grid;grid-template-columns:1fr;margin:6px 0 18px}
@media(min-width:900px){.features{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.feat{padding:0 22px;border-left:1px solid var(--rule)}.feat:first-child{border-left:0;padding-left:0}.feat:last-child{padding-right:0}}
.features .feat{margin-bottom:18px}
.list{list-style:none;margin:0;padding:0}.list li{padding:7px 0;border-bottom:1px dotted var(--rule);line-height:1.35}
.list b{font-variant:small-caps;letter-spacing:.5px;margin-right:6px}.list .aw{display:block}.list i{color:var(--muted);font-size:14px}
.tape{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;text-align:center;border-top:2px solid var(--rule);border-bottom:2px solid var(--rule);padding:10px 0}
.tm-name{font:700 17px/1.2 'Old Standard TT',serif;text-transform:uppercase;overflow-wrap:anywhere}.tm-meta{font:italic 13px/1.4 'IM Fell English',serif;color:var(--muted)}
.vs{font:italic 700 22px 'IM Fell English',serif;padding:0 10px}
.h2h{text-align:center;font:italic 14px/1.4 'IM Fell English',serif;margin:8px 0}
.preview{text-align:justify;hyphens:auto;-webkit-hyphens:auto;margin:6px 0 0}
.power{margin:10px 0 26px}.power .note{text-align:center;font:italic 14px 'IM Fell English',serif;color:var(--muted);margin:-6px 0 10px}
.power td.roast{font:italic 15px/1.35 'IM Fell English',serif}

.leadstory{margin:22px 0 8px}
.lead-cols{max-width:760px;margin:0 auto;font-size:19px;line-height:1.65}
.lead-cols p{margin:0 0 14px;text-align:justify;hyphens:auto;-webkit-hyphens:auto}
.lead-cols .lede::first-letter{float:left;font:700 68px/.8 'Old Standard TT',serif;margin:6px 10px 0 0;padding:2px 6px;border:1px solid var(--rule)}
.cols{display:grid;grid-template-columns:1fr}
@media(min-width:760px){.cols{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1150px){.cols{grid-template-columns:repeat(3,1fr)}}
.section-h{font:700 13px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:3px;text-align:center;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:6px 0;margin:0 0 14px}
.cell{min-width:0;padding:4px 0 18px;margin-bottom:22px;border-bottom:1px solid var(--rule)}
@media(min-width:760px) and (max-width:1149px){.cols>.cell{padding:4px 20px 18px;border-left:1px solid var(--rule)}.cols>.cell:nth-child(2n+1){border-left:0;padding-left:0}.cols>.cell:nth-child(2n){padding-right:0}}
@media(min-width:1150px){.cols>.cell{padding:4px 22px 18px;border-left:1px solid var(--rule)}.cols>.cell:nth-child(3n+1){border-left:0;padding-left:0}.cols>.cell:nth-child(3n){padding-right:0}}
.cell.feat .section-h{margin-top:4px}
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

/* ---- UI pass ---- */
.mgr{font-family:'Old Standard TT',Georgia,serif;font-style:normal}
.jump{position:sticky;top:0;z-index:5;display:flex;justify-content:center;gap:4px 22px;flex-wrap:wrap;background:var(--paper);border-bottom:1px solid var(--rule);padding:8px 0;margin:-14px 0 18px;font:700 12px/1.2 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:2px}
.jump a{color:var(--ink);text-decoration:none;padding:4px 2px}.jump a:hover,.jump a:focus-visible{color:var(--accent);text-decoration:underline}
[id]{scroll-margin-top:52px}
.finder{max-width:900px;margin:0 auto 16px;text-align:center;font:15px/1.9 'Old Standard TT',serif}
.finder b{font-variant:small-caps;letter-spacing:1px;margin-right:4px}
.finder a{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent);white-space:nowrap}
.finder a:hover,.finder a:focus-visible{border-bottom-style:solid}
.bout:target{background:linear-gradient(var(--soft),var(--soft))}
.ding{font-weight:700;color:var(--accent);font-family:'Old Standard TT',Georgia,serif}
.box .row.lose{color:var(--muted)}.box .row.lose .pts{font-weight:400}.box .row.win .pts{font-size:20px}
:root{--muted:#57524a}
.tm-meta,.box .meta,.box .foot,.bout .sub,.h2h,.tile .w{font-size:14px}
@media(max-width:759px){.bout p,.lead-cols p,.preview{text-align:left;hyphens:manual;-webkit-hyphens:manual}.jump{gap:4px 14px;letter-spacing:1px}}

/* ---- tables: fixed, matching columns ---- */
.st2 table,.pw{table-layout:fixed}
.c-rk{width:2.4em}.c-rec{width:3.6em}.c-pf{width:5.2em}.c-st{width:3.4em}.c-mg{width:30%}.c-ap{width:6.8em}
td,th{overflow-wrap:anywhere;vertical-align:baseline}
td.n,th.n{text-align:right;padding-right:14px;font-variant-numeric:tabular-nums lining-nums}
td.st,th.st{text-align:left;padding-left:8px;font-variant-numeric:tabular-nums}
.pw th.roast,.pw td.roast{padding-left:14px}
td .up,td .down{font-size:.8em;margin-left:1px;white-space:nowrap}


@media(max-width:640px){
 .pw colgroup{display:none}
 .pw,.pw tbody{display:block;width:100%}
 .pw tr{display:grid;grid-template-columns:2em minmax(0,1fr) 3em 4.4em;align-items:baseline;border-bottom:1px dotted var(--rule);padding:6px 0}
 .pw td,.pw th{border:0;padding:2px 3px}
 .pw th.roast{display:none}
 .pw td.roast{grid-column:2/-1;padding:2px 3px 2px 3px!important;line-height:1.4}
}

/* ---- The Funnies ---- */
.funnies{margin:30px 0 8px}
.strip-title{text-align:center;font:italic 20px/1.3 'IM Fell English',serif;margin:0 0 12px}
.strip-title span{display:block;font-size:14px;color:var(--muted)}
.strip{display:grid;grid-template-columns:1fr;gap:12px;max-width:1100px;margin:0 auto}
@media(min-width:640px){.strip{grid-template-columns:repeat(3,1fr)}}
.panel{position:relative;margin:0;border:3px solid var(--ink);background:var(--paper);padding:10px 10px 4px;display:flex;flex-direction:column;min-height:330px;
 background-image:radial-gradient(color-mix(in srgb,var(--ink) 9%,transparent) 1px,transparent 1.2px);background-size:7px 7px}
.bubble{position:relative;align-self:center;max-width:92%;background:var(--paper);border:2px solid var(--ink);border-radius:18px;padding:8px 12px;
 font:700 14px/1.3 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:.4px;text-align:center;margin-bottom:14px}
.bubble::after{content:"";position:absolute;left:46%;bottom:-13px;border:7px solid transparent;border-top:13px solid var(--ink);border-bottom:0}
.bubble::before{content:"";position:absolute;left:calc(46% + 3px);bottom:-8px;border:4px solid transparent;border-top:9px solid var(--paper);border-bottom:0;z-index:1}
.panel .rivet{width:100%;max-width:220px;margin:auto auto 0;display:block}
.pn{position:absolute;right:6px;bottom:4px;font:italic 12px 'IM Fell English',serif;color:var(--muted)}

/* ---- editions: ornaments, playoff line, bracket, champion ---- */
.orn-row{display:flex;justify-content:center;gap:18px;margin:-12px 0 16px;opacity:.9}.orn-row svg{width:20px;height:20px}
.sheet{border-top:6px solid var(--accent)}
tr.cut td{border-bottom:2px dashed var(--accent)}
.cutnote{font:italic 14px 'IM Fell English',serif;margin:8px 0 0;display:flex;align-items:center;gap:8px}
.cutkey{display:inline-block;width:28px;border-top:2px dashed var(--accent)}
.bracket{margin:6px 0 26px}.brs{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(180px,1fr);gap:18px;overflow-x:auto;padding-bottom:6px}
.br h4{font:700 13px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:2px;text-align:center;margin:0 0 10px}
.br{display:flex;flex-direction:column;justify-content:space-around;gap:12px}
.bm{border:2px solid var(--ink);font:15px/1.3 'Old Standard TT',serif}.bt{padding:6px 10px}.bt+.bt{border-top:1px dotted var(--ink)}
.bt.won{font-weight:700;background:color-mix(in srgb,var(--accent) 10%,transparent)}
.champ{text-align:center;border:3px double var(--ink);padding:14px;margin:0 0 22px;background:color-mix(in srgb,var(--accent) 6%,transparent)}
.champ .rivet{width:150px}.champ-k{font:700 13px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:3px;color:var(--accent)}
.champ-n{font:700 clamp(30px,6vw,56px)/1.1 'Old Standard TT',serif;text-transform:uppercase}.ru{font:italic 17px 'IM Fell English',serif;margin:4px 0 0}

/* ---- On Deck: next week's card ---- */
.ondeck{margin:6px 0 26px}
.ods{display:grid;grid-template-columns:1fr;gap:22px 0}
@media(min-width:1250px){.ods{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.od{padding:0 22px;border-left:1px solid var(--rule)}.od:first-child{border-left:0;padding-left:0}.od:last-child{padding-right:0}}
@media(max-width:1249px){.od{width:100%;max-width:640px;margin:0 auto}}
.od,.tm-side{min-width:0}.tm-name.one{white-space:nowrap;overflow:hidden}
@media(max-width:759px){.od .tm-name{font-size:15px}}
.bill{text-align:center;font:700 12px/1 'Old Standard TT',serif;text-transform:uppercase;letter-spacing:3px;color:var(--accent);margin:0 0 8px}
.features .feat:only-child .list{columns:2 320px;column-gap:32px}.features .list li{break-inside:avoid}
"""


def wa(text):
    """WhatsApp/markdown markup -> safe HTML (one line)."""
    s = E(text)
    s = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", s)


def n2(x):
    """Scores always show 2 decimals: 181.2 -> 181.20."""
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return E(str(x))


def slug(name):
    return "m-" + re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def managers(f):
    return sorted({s["manager"] for s in f.get("standings", [])}, key=len, reverse=True)


def upright(html_body, f):
    """Wrap manager names in text nodes with <span class=mgr> (upright, plain type)."""
    names = [E(n) for n in managers(f) if n]
    if not names:
        return html_body
    pat = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) + r")(?![\w-])")
    parts = re.split(r"(<[^>]+>)", html_body)
    skip = 0
    for i, p in enumerate(parts):
        if p.startswith("<"):
            if re.match(r"<(script|style|title)\b", p): skip += 1
            elif re.match(r"</(script|style|title)>", p): skip -= 1
            continue
        if not skip:
            parts[i] = pat.sub(r'<span class="mgr">\1</span>', p)
    return "".join(parts)


def arrow(prev, now):
    if prev is None or prev == now:
        return ""
    d = prev - now
    return f'&nbsp;<span class="{"up" if d > 0 else "down"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>'


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
        f'<div class="tile"><div class="k"><span class="orn">{k.split(" ",1)[0]}</span> {k.split(" ",1)[1]}</div><div class="v">{n2(v)}</div><div class="w">{E(w)}</div></div>'
        for k, v, w in items) + "</div>"


def scorebox(g):
    rows = ""
    for side, cls in (("winner", "win"), ("loser", "lose")):
        rows += (f'<div class="row {cls}"><span class="tm">{E(g[side])}</span>'
                 f'<span class="meta">{g.get(side + "_record", "")} · #{g.get(side + "_rank", "")}'
                 f'{arrow(g.get(side + "_prev_rank"), g.get(side + "_rank"))}</span>'
                 f'<span class="pts">{n2(g[side + "_pts"])}</span></div>')
    star = (g.get("winner_lineup") or {}).get("stars") or []
    foot = f"Margin {n2(g['margin'])}" + (f" · Star: {E(star[0]['player'])} {n2(star[0]['pts'])}" if star else "")
    return f'<div class="box">{rows}<div class="foot">{foot}</div></div>'


def banner_of(md):
    m = re.search(r"^BANNER:\s*(.+)$", md, flags=re.M)
    return m.group(1).strip(" *") if m else ""


BLOCKS = r"(?=^(?:BANNER|LEAD|MARQUEE|PREVIEWS|POWER|STRIP|PUNS|EPITHETS):|^###|\Z)"


def block(md, name):
    """Text of a 'NAME:' section, up to the next section or story heading."""
    m = re.search(rf"^{name}:[ \t]*\n?(.*?){BLOCKS}", md, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


def lead_of(md):
    return block(md, "LEAD")


def lead_html(md):
    lead = lead_of(md)
    if not lead:
        return ""
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", lead) if p.strip()]
    ps = "".join(f'<p class="{"lede" if n == 0 else ""}">{wa(p)}</p>' for n, p in enumerate(paras))
    return f'<section class="leadstory" id="review"><div class="section-h">The Week in Review</div><div class="lead-cols">{ps}</div></section>'


def stories_html(md, f):
    out = []
    md = re.sub(r"^(?:BANNER|PUNS|EPITHETS):.*$", "", md, flags=re.M)
    md = re.sub(rf"^(?:LEAD|MARQUEE|PREVIEWS|POWER|STRIP):.*?{BLOCKS}", "", md, flags=re.M | re.S)
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
        DING = {"🚑": "✚", "💸": "$", "🔄": "⇄"}
        orn = lambda h: re.sub(r"[🚑💸🔄]\s*", lambda m: f'<span class="ding">{DING[m.group(0).strip()]}</span> ', h)
        html_p = "".join(f'<p class="{"lede" if n == 0 else ""}">{orn(wa(p))}</p>' for n, p in enumerate(paras))
        quote = f"<blockquote>{'<br>'.join(wa(c) for c in couplet)}</blockquote>" if couplet else ""
        kick = f'<p class="kicker"><b>Kicker</b>{wa(kicker)}</p>' if kicker else ""
        t = title.strip(" *#")
        first, _, rest = t.partition(" ")
        orn = ""
        if rest and not any(ch.isalnum() for ch in first):             # leading emoji -> woodcut ornament
            orn, t = f'<span class="orn">{first}</span> ', rest
        sub = f'<p class="sub">{E(game["winner"])} vs. {E(game["loser"])}</p>' if game else ""
        aid = f' id="{slug(game["winner"])}"' if game else ""
        out.append(f'<section class="cell bout"{aid}><h4>{orn}{E(t)}</h4>{sub}'
                   f'{scorebox(game) if game else ""}{html_p}{quote}{kick}</section>')
    return "".join(out)


def awards_html(f):
    a, items = f.get("awards") or {}, []
    if a.get("boom"):
        b = a["boom"]; items.append(("🔥", "Boom of the Week", f"{E(b['player'])} · {b['pts']}", E(b["manager"])))
    if a.get("dud"):
        d = a["dud"]; items.append(("🧊", "Dud of the Week", f"{E(d['player'])} · {d['pts']}", E(d["manager"])))
    if a.get("bench_crime"):
        c = a["bench_crime"]
        items.append(("🚑", "Bench Crime", f"{E(c['benched'])} ({c['benched_pts']}) sat for {E(c['started'])} ({c['started_pts']})", E(c["manager"])))
    if a.get("big_spender"):
        x = a["big_spender"]; items.append(("💸", "Big Spender", f"${x['faab']} on {E(x['player'])}", E(x["manager"])))
    elif a.get("most_active"):
        x = a["most_active"]; items.append(("🔁", "Most Active", f"{x['moves']} moves", E(x["manager"])))
    rows = "".join(f'<li><span class="orn">{i}</span> <b>{k}</b><span class="aw">{v}</span><i>{m}</i></li>' for i, k, v, m in items)
    return f'<div class="feat"><div class="section-h">Weekly Awards</div><ul class="list">{rows}</ul></div>' if items else ""


def card_of(f):
    """Next week's games to preview. Older issues stored a single marquee game."""
    return f.get("next_week_card") or ([dict(f["next_week"], billing="Main Event")] if f.get("next_week") else [])


def ondeck_html(f, md):
    card = card_of(f)
    if not card:
        return ""
    texts = [" ".join(t.split()) for t in re.split(r"^\s*\d+[.)]\s*", block(md, "PREVIEWS"), flags=re.M) if t.strip()]
    texts = texts or [" ".join(block(md, "MARQUEE").split())]
    def tape(x):
        one = "" if " " in x["manager"].strip() else " one"          # one-word names shrink instead of splitting
        return (f'<div class="tm-side"><div class="tm-name{one}">{E(x["manager"])}</div>'
                f'<div class="tm-meta">{x["record"]} · #{x["rank"]} · {x["streak"]}</div>'
                f'<div class="tm-meta">Power #{x["power_rank"]}</div></div>')
    cells = ""
    for i, g in enumerate(card):
        h = g.get("head_to_head") or []
        h2h = ("; ".join(f"Week {m['week']}: {E(m['winner'])} won {m['score']}" for m in h)
               if h else "First meeting this season")
        body = f'<p class="preview">{wa(texts[i])}</p>' if i < len(texts) and texts[i] else ""
        cells += (f'<div class="od"><div class="bill">{E(g.get("billing", ""))}</div>'
                  f'<div class="tape">{tape(g["a"])}<div class="vs">vs.</div>{tape(g["b"])}</div>'
                  f'<p class="h2h">{h2h}</p>{body}</div>')
    return (f'<section class="ondeck" id="ondeck"><div class="section-h">On Deck: Week {card[0]["week"]}</div>'
            f'<div class="ods">{cells}</div></section>')


def lore_html(f):
    l = f.get("lore") or {}
    if not l:
        return ""
    items = [("📈", "Season high", f"{E(l['season_high']['manager'])}, {l['season_high']['pts']} in Week {l['season_high']['week']}"),
             ("📉", "Season low", f"{E(l['season_low']['manager'])}, {l['season_low']['pts']} in Week {l['season_low']['week']}")]
    if l.get("hot_streak"):
        items.append(("🔥", "Hottest", f"{E(l['hot_streak']['manager'])} ({l['hot_streak']['streak']})"))
    if l.get("cold_streak"):
        items.append(("🧊", "Coldest", f"{E(l['cold_streak']['manager'])} ({l['cold_streak']['streak']})"))
    for k, i, lab in (("luckiest", "🍀", "Luckiest"), ("unluckiest", "😤", "Unluckiest")):
        p = l[k]
        items.append((i, lab, f"{E(p['manager'])}: {p['record']} record, {p['all_play']} true record"))
    v = l["schedule_victim"]
    items.append(("🎯", "Schedule victim", f"{E(v['manager'])}, {v['pa']} points against"))
    rows = "".join(f'<li><span class="orn">{i}</span> <b>{k}</b><span class="aw">{t}</span></li>' for i, k, t in items)
    return f'<div class="feat"><div class="section-h">League Lore</div><ul class="list">{rows}</ul></div>'


def power_html(f, md):
    pr = f.get("power_rankings") or []
    if not pr:
        return ""
    lines = block(md, "POWER").splitlines()
    def roast(name):
        for l in lines:
            if name in l:
                return re.split(r"\s[—–-]\s|:\s", l.split(name, 1)[1], maxsplit=1)[-1].strip()
        return ""
    rows = "".join(
        f"<tr><td>{p['power_rank']}</td><td>{E(p['manager'])}{arrow(p.get('prev_power_rank'), p['power_rank'])}</td>"
        f"<td>{p['record']}</td><td class=n>{p['all_play']}</td><td class=roast>{wa(roast(p['manager']))}</td></tr>"
        for p in pr)
    return (f'<section class="power" id="power"><div class="section-h">Power Rankings</div>'
            f'<p class="note">True Record = how each team would fare against every team, every week. '
            f'Rank blends True Record (60%), the last 3 weeks (25%) and total points (15%).</p>'
            f'<table class="pw"><colgroup><col class="c-rk"><col class="c-mg"><col class="c-rec"><col class="c-ap"><col></colgroup>'
            f'<tr><th>#</th><th>Manager</th><th>Rec</th><th class=n>True Rec.</th><th class=roast>The word on the street</th></tr>{rows}</table></section>')


def standings(f):
    head = ('<colgroup><col class="c-rk"><col><col class="c-rec"><col class="c-pf"><col class="c-st"></colgroup>'
            "<tr><th>#</th><th>Manager</th><th>Rec</th><th class=n>PF</th><th class=st>Strk</th></tr>")
    race = f.get("playoff_race")
    cut = (race or {}).get("playoff_teams")
    rows = [f"<tr{' class=cut' if cut and s['rank'] == cut else ''}><td>{s['rank']}</td><td>{E(s['manager'])}{arrow(s.get('prev_rank'), s['rank'])}</td><td>{s['record']}</td>"
            f"<td class=n>{n2(s['pf'])}</td><td class=st>{s['streak']}</td></tr>" for s in f["standings"]]
    half = (len(rows) + 1) // 2
    note = ""
    if race:
        left = race["weeks_left"]
        when = "The field is set." if left == 0 else f"{left} week{'s' if left > 1 else ''} left in the regular season."
        note = f'<p class="cutnote"><span class="cutkey"></span> Playoff line: top {cut} advance. {when}</p>'
    return (f'<div class="st2"><table>{head}{"".join(rows[:half])}</table>'
            f'<table>{head}{"".join(rows[half:])}</table></div>{note}')


def bracket_html(f):
    rows = [b for b in f.get("bracket") or [] if b.get("place") in (None, 1)]
    if not rows:
        return ""
    rounds = sorted({b["round"] for b in rows if b.get("round")})
    last = rounds[-1] if rounds else 0
    name = lambda r: theme.ROUND_NAMES.get(last - r + 1, f"Round {r}")
    def match(b):
        side = lambda t: (f'<div class="bt{" won" if b["winner"] and t == b["winner"] else ""}">{E(t) if t else "<i>TBD</i>"}'
                          f'{" ✓" if b["winner"] and t == b["winner"] else ""}</div>')
        return f'<div class="bm">{side(b["a"])}{side(b["b"])}</div>'
    cols = "".join(f'<div class="br"><h4>{name(r)}</h4>{"".join(match(b) for b in rows if b["round"] == r)}</div>' for r in rounds)
    return f'<section class="bracket" id="bracket"><div class="section-h">The Bracket</div><div class="brs">{cols}</div></section>'


def champion_html(f):
    c = f.get("champion")
    if not c:
        return ""
    ru = f'<p class="ru">Defeated {E(c["runner_up"])} in the final.</p>' if c.get("runner_up") else ""
    return (f'<section class="champ"><div class="champ-k">Your {f["season"]} Champion</div>'
            f'{comic.rivet("trophy", 0, 1, {"costumes": ("crown",), "scenes": ("confetti",)})}'
            f'<div class="champ-n">{E(c["manager"])}</div>{ru}</section>')


ORN = {
    "pumpkin": '<ellipse cx="12" cy="14" rx="9" ry="7"/><path d="M12 7 q1 -4 4 -4" fill="none"/><path d="M8 13 l2 -2 l2 2 M12 13 l2 -2 l2 2 M8 17 q4 3 8 0" fill="none" stroke="var(--paper)"/>',
    "leaf": '<path d="M12 3 q9 9 0 18 q-9 -9 0 -18z"/><path d="M12 3 v19" stroke="var(--paper)" fill="none"/>',
    "turkey": '<circle cx="12" cy="15" r="6"/><path d="M4 12 a8 8 0 0 1 16 0" fill="none" stroke-width="3"/><circle cx="12" cy="8" r="3"/>',
    "snowflake": '<path d="M12 2 v20 M3 7 l18 10 M3 17 l18 -10" fill="none" stroke-width="2"/>',
    "holly": '<path d="M4 12 q4 -6 8 0 q4 -6 8 0 q-4 6 -8 0 q-4 6 -8 0z"/><circle cx="12" cy="7" r="2.5"/><circle cx="9" cy="5" r="2"/>',
    "star": '<path d="M12 2 l3 7 h7 l-6 4 l2 8 l-6 -5 l-6 5 l2 -8 l-6 -4 h7z"/>',
    "football": '<path d="M3 12 q9 -10 18 0 q-9 10 -18 0z"/><path d="M9 12 h6 M10 10 v4 M12 10 v4 M14 10 v4" fill="none" stroke="var(--paper)"/>',
    "trophy": '<path d="M7 3 h10 v5 q0 6 -5 7 q-5 -1 -5 -7z"/><rect x="10" y="15" width="4" height="4"/><rect x="7" y="19" width="10" height="3"/>',
}


def ornaments(ed):
    o = ORN.get(ed.get("ornament") or "")
    if not o:
        return ""
    icon = f'<svg viewBox="0 0 24 24" aria-hidden="true" fill="var(--accent)" stroke="var(--accent)" stroke-width="1.5">{o}</svg>'
    return f'<div class="orn-row" aria-hidden="true">{icon * 9}</div>'



def strip_html(md, week=0, edition=None):
    m = re.search(rf"^STRIP:[ \t]*(.*?)\n(.*?){BLOCKS}", md, flags=re.M | re.S)
    if not m:
        return ""
    title, panels = m.group(1).strip(" *"), comic.parse(m.group(2))
    if len(panels) < 3:
        return ""
    cells = "".join(
        f'<figure class="panel"><div class="bubble">{wa(line)}</div>{comic.rivet(pose, week, n, edition)}'
        f'<figcaption class="pn">{n}</figcaption></figure>' for n, (pose, line) in enumerate(panels, 1))
    return (f'<section class="funnies" id="funnies"><div class="section-h">The Funnies</div>'
            f'<p class="strip-title">“{wa(title)}” <span>starring Rivet, our robot correspondent</span></p>'
            f'<div class="strip">{cells}</div></section>')


def finder(f, stories):
    """'Find your team': each manager links to their matchup story."""
    links = []
    for g in f.get("results", []):
        for side in ("winner", "loser"):
            links.append((g[side], slug(g["winner"])))
    if not stories or not links:
        return ""
    links.sort(key=lambda x: x[0].lower())
    return ('<nav class="finder" aria-label="Find your team"><b>Find your team:</b> '
            + " · ".join(f'<a href="#{a}">{E(n)}</a>' for n, a in links) + "</nav>")


def page(f, text, stories, weeks, title_prefix="", others="", og_url=""):
    league = E(f["league"])
    ed = theme.edition(f)
    head, deck = headline(f, banner_of(stories))
    desc = E(f"{head}. {deck}")
    archive = " · ".join(f'<a href="week-{w}.html">Week {w}</a>' for w in sorted(weeks, reverse=True))
    wa_html = "<br>\n".join(wa(l) for l in text.splitlines())
    feats = [x for x in (awards_html(f), lore_html(f)) if x]
    if stories:
        bouts = stories_html(stories, f)
        empty = (-bouts.count('class="cell bout"')) % 3            # holes in the last row of 3
        fill, rest = feats[:empty], feats[empty:]
        fill = [x.replace('<div class="feat">', '<section class="cell feat">', 1)[:-6] + "</section>" for x in fill]
        cols = f'<div class="section-h" id="matchups">The Matchups</div><div class="cols">{bouts}{"".join(fill)}</div>'
    else:
        rest = feats
        cols = f'<article>{wa_html}</article>'
    features = f'<div class="features">{"".join(rest)}</div>' if rest else ""
    og_img = (f'\n<meta property="og:image" content="{og_url}"><meta property="og:image:width" content="1200">'
              f'<meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">'
              if og_url else "")
    jump = [("#review", "Review") if lead_of(stories) else None, ("#matchups", "Matchups") if stories else None,
            ("#ondeck", "On Deck") if card_of(f) else None,
            ("#bracket", "Bracket") if f.get("bracket") else None,
            ("#power", "Power") if f.get("power_rankings") else None, ("#standings", "Standings"),
            ("#funnies", "Funnies") if re.search(r"^STRIP:", stories or "", re.M) else None]
    jumpbar = '<nav class="jump" aria-label="Sections">' + "".join(f'<a href="{h}">{t}</a>' for h, t in filter(None, jump)) + "</nav>"
    return upright_page(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>{title_prefix}{league} Gazette</title>
<meta property="og:title" content="{league} Gazette — Week {f['week']}">
<meta property="og:description" content="{desc}"><meta name="description" content="{desc}">
<meta property="og:type" content="article">{og_img}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=IM+Fell+English:ital@0;1&display=swap" rel="stylesheet">
<meta name='color-scheme' content='light'><style>{CSS}:root{{--accent:{ed['accent']}}}</style></head><body><main class="sheet">
<header class="mast">
<div class="ear">{E(ed['label'])}<small>{E(ed['sub'])}</small></div>
<a href="index.html"><h1>The {league} Gazette</h1></a>
<div class="ear">Price: One FAAB Dollar<small>{f['teams']} clubs reporting</small></div>
</header>
<div class="rules"></div>
<div class="dateline"><span>Vol. {f['season']} · No. {f['week']}</span><i>“{E(ed['tagline'])}”</i><span>{"Late City Final" if ed['key'] == "regular" and not ed['playoff'] else E(ed['label'])}</span></div>
{ornaments(ed)}
{jumpbar}
{champion_html(f)}
<section class="lead"><h2 class="head">{E(head)}</h2><p class="deck">{E(deck)}</p>{finder(f, stories)}{tiles(f)}</section>
{lead_html(stories)}
<div class="body">
{cols}
{features}
{ondeck_html(f, stories)}
{bracket_html(f)}
{power_html(f, stories)}
<div class="band">
<section id="standings"><h3>The Official Standings</h3>{standings(f)}</section>
<div class="side">
<section><h3>Back Issues</h3><nav class="archive">{archive}</nav></section>
<section><details><summary>📱 Wire copy (Mobile)</summary><article>{wa_html}</article></details></section>
</div>
</div>
</div>
{strip_html(stories, f["week"], ed)}
<footer>{others}Every figure verified against the Sleeper wire. The jokes are not.</footer>
</main>
<script>
/* one-line headlines: shrink until they fit; wrap only as a last resort */
function fit(){{document.querySelectorAll('.bout h4,.mast h1,.tm-name.one').forEach(function(h){{
  h.classList.remove('fit-wrap');h.style.fontSize='';var s=parseFloat(getComputedStyle(h).fontSize);
  var min=h.tagName==='H1'?26:h.tagName==='H4'?14:9;
  while(h.scrollWidth>h.clientWidth&&s>min){{s-=.5;h.style.fontSize=s+'px';}}
  if(h.scrollWidth>h.clientWidth)h.classList.add('fit-wrap');}});}}
document.fonts&&document.fonts.ready.then(fit);fit();addEventListener('resize',fit);
</script></body></html>""", f)


def upright_page(doc, f):
    head, sep, body = doc.partition("<body>")
    return head + sep + upright(body, f)


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
    return (f"<!doctype html><meta charset=utf-8><meta name=robots content='noindex,nofollow'><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{E(name)} Gazette</title><style>{CSS}</style><main class=sheet><header class=mast><h1>The {E(name)} Gazette</h1></header>"
            f"<p class=deck style='text-align:center;margin-top:24px'>First edition hits the stands Wednesday morning.</p></main>")


FONTS = HERE / "fonts"


def og_image(f, head, path):
    """1200x630 share card: masthead, banner headline, four stat tiles. Skips if Pillow is missing."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    W, H, ink, muted, paper = 1200, 630, (28, 27, 25), (87, 82, 74), (255, 254, 251)
    img = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(img)
    font = lambda name, size: ImageFont.truetype(str(FONTS / name), size)
    def fit(text, name, size, maxw, minsize=20):
        while size > minsize and d.textlength(text, font=font(name, size)) > maxw:
            size -= 2
        return font(name, size)
    d.rectangle([18, 18, W - 19, H - 19], outline=ink, width=2)
    title = f"The {f['league']} Gazette"
    ft = fit(title, "UnifrakturMaguntia-Book.ttf", 96, W - 120)
    d.text((W / 2, 92), title, font=ft, fill=ink, anchor="mm")
    d.line([48, 150, W - 48, 150], fill=ink, width=5)
    d.line([48, 158, W - 48, 158], fill=ink, width=1)
    dl = font("OldStandard-Bold.ttf", 20)
    d.text((48, 182), f"VOL. {f['season']} · NO. {f['week']}", font=dl, fill=ink, anchor="lm")
    ed = theme.edition(f)
    right = "LATE CITY FINAL" if ed["key"] == "regular" and not ed["playoff"] else ed["label"].upper()
    d.text((W - 48, 182), right, font=dl, fill=ink, anchor="rm")
    d.text((W / 2, 182), f"“{ed['tagline']}”", font=fit(f"“{ed['tagline']}”", "OldStandard-Italic.ttf", 21, 520, 14), fill=muted, anchor="mm")
    if ed["key"] != "regular" or ed["playoff"]:
        acc = tuple(int(ed["accent"][i:i + 2], 16) for i in (1, 3, 5))
        d.rectangle([18, 18, W - 19, 30], fill=acc)
    d.line([48, 204, W - 48, 204], fill=ink, width=1)
    # banner headline: up to 2 lines, shrink to fit
    words, size = head.upper().split(), 70
    while True:
        fh = font("OldStandard-Bold.ttf", size)
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=fh) <= W - 130 or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if (len(lines) <= 2 and all(d.textlength(l, font=fh) <= W - 130 for l in lines)) or size <= 34:
            break
        size -= 3
    y = 322 - (len(lines) - 1) * size * 0.55
    for l in lines[:3]:
        d.text((W / 2, y), l, font=fh, fill=ink, anchor="mm"); y += size * 1.1
    # stat tiles
    c, b = f["closest"], f["blowout"]
    tiles = [("HIGH", f["high"]["pts"], f["high"]["manager"]), ("LOW", f["low"]["pts"], f["low"]["manager"]),
             ("CLOSEST", c["margin"], c["winner"]), ("BLOWOUT", b["margin"], b["winner"])]
    top, tw = 440, (W - 96) / 4
    d.line([48, top, W - 48, top], fill=ink, width=2)
    d.line([48, H - 48, W - 48, H - 48], fill=ink, width=2)
    for i, (k, v, who) in enumerate(tiles):
        cx = 48 + tw * i + tw / 2
        if i:
            d.line([48 + tw * i, top + 14, 48 + tw * i, H - 62], fill=ink, width=1)
        d.text((cx, top + 32), k, font=font("OldStandard-Bold.ttf", 18), fill=ink, anchor="mm")
        d.text((cx, top + 82), n2(v), font=font("OldStandard-Bold.ttf", 50), fill=ink, anchor="mm")
        d.text((cx, top + 128), who, font=fit(who, "OldStandard-Regular.ttf", 22, tw - 24, 14), fill=muted, anchor="mm")
    img.save(path, optimize=True)
    return True


def build():
    SITE.mkdir(exist_ok=True)
    (SITE / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")   # keep papers out of search
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
        base = (lg.get("site") or "").rstrip("/") + ("/" + lg["path"] if lg["path"] else "")
        for (s, w), (f, text, stories) in issues.items():
            if s == latest[0]:
                img = f"og-week-{w}.png"
                ok = og_image(f, headline(f, banner_of(stories))[0], out / img)
                url = f"{base}/{img}" if ok and base else ""
                html_ = page(f, text, stories, weeks, f"Week {w} · ", others, url)
                (out / f"week-{w}.html").write_text(html_, encoding="utf-8")
                if (s, w) == latest:
                    (out / "index.html").write_text(page(f, text, stories, weeks, "", others, url), encoding="utf-8")
        print(f"{name}: {len(weeks)} issue(s); front page = week {latest[1]}")


if __name__ == "__main__":
    build()
