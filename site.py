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
:root{--bg:#efe9dc;--paper:#fffdf8;--ink:#1d1b17;--muted:#6b645a;--rule:#1d1b17;--soft:#e9e2d3;--accent:#b3261e;--up:#1e7a3c;--down:#b3261e}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#110f0c;--paper:#1c1915;--ink:#eee8dc;--muted:#a39b8e;--rule:#eee8dc;--soft:#2a261f;--accent:#ff8a7a;--up:#6fd08c;--down:#ff8a7a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Georgia,'Times New Roman',serif}
main{max-width:720px;margin:0 auto;padding:24px 16px 48px;background:var(--paper);min-height:100vh}
.mast{text-align:center;border-bottom:3px double var(--rule);padding-bottom:10px}
.mast a{color:inherit;text-decoration:none}.mast h1{font:900 clamp(28px,8vw,48px)/1.05 'Playfair Display',Georgia,serif;margin:0;letter-spacing:-.5px}
.mast .motto{font:italic 13px/1.4 Georgia,serif;color:var(--muted);margin-top:4px}
.dateline{display:flex;justify-content:space-between;font:12px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:1px;color:var(--muted);border-bottom:1px solid var(--rule);padding:8px 0;margin-bottom:22px}
h2.head{font:800 clamp(26px,6.5vw,38px)/1.12 'Playfair Display',Georgia,serif;margin:0 0 8px}
.deck{color:var(--muted);font-style:italic;margin:0 0 20px;font-size:18px}
h3{font:700 13px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:1.5px;margin:36px 0 12px;border-bottom:2px solid var(--rule);padding-bottom:6px}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0 0 8px}
@media(min-width:600px){.tiles{grid-template-columns:repeat(4,1fr)}}
.tile{background:var(--soft);border-radius:8px;padding:10px 12px;font-family:system-ui,sans-serif}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}
.tile .v{font:800 22px/1.2 'Playfair Display',Georgia,serif;font-variant-numeric:tabular-nums;margin:2px 0}
.tile .w{font-size:13px;overflow-wrap:anywhere}
.bout{padding-top:4px;margin:28px 0 0;border-top:1px solid var(--rule)}h3+.bout{border-top:0;margin-top:0}
.bout h4{font:800 25px/1.2 'Playfair Display',Georgia,serif;margin:14px 0 12px}
.box{border:1px solid var(--rule);border-radius:6px;font:15px/1.3 system-ui,sans-serif;margin:0 0 14px;overflow:hidden}
.box .row{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;padding:8px 12px}
.box .row+.row{border-top:1px solid color-mix(in srgb,var(--ink) 15%,transparent)}
.box .win{font-weight:700}.box .tm{overflow-wrap:anywhere}.box .meta{font-size:12px;color:var(--muted);white-space:nowrap}
.box .pts{font-variant-numeric:tabular-nums;font-size:18px;min-width:64px;text-align:right}
.box .foot{background:var(--soft);padding:6px 12px;font-size:12px;color:var(--muted)}
.bout p{margin:0 0 12px}
.bout .lede::first-letter{float:left;font:900 52px/.85 'Playfair Display',Georgia,serif;margin:6px 8px 0 0}
blockquote{margin:16px 0;padding:6px 0 6px 16px;border-left:3px solid var(--accent);font-style:italic;font-size:19px;line-height:1.5}
.kicker{font:14px/1.5 system-ui,sans-serif;border-top:1px dotted var(--muted);padding-top:8px;margin-top:4px}
.kicker b{text-transform:uppercase;letter-spacing:1px;font-size:11px;color:var(--accent);margin-right:6px}
table{width:100%;border-collapse:collapse;font:15px/1.3 system-ui,sans-serif}td,th{padding:7px 4px;border-bottom:1px solid color-mix(in srgb,var(--ink) 15%,transparent);text-align:left}
th{font-size:12px;text-transform:uppercase;color:var(--muted)}.n{text-align:right;font-variant-numeric:tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}
details{margin-top:28px;font:15px/1.5 system-ui,sans-serif;border:1px solid color-mix(in srgb,var(--ink) 20%,transparent);border-radius:6px;padding:10px 12px}
summary{cursor:pointer;font-weight:600}details article{margin-top:10px}
.archive a{display:inline-block;margin:0 10px 8px 0;color:var(--accent)}
footer{margin-top:40px;font:12px system-ui,sans-serif;color:var(--muted);text-align:center}
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


def headline(f):
    c, h, l = f["closest"], f["high"], f["low"]
    head = f"{h['manager']} Drops {h['pts']}; {l['manager']} Sinks to {l['pts']}"
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
        f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="w">{E(w)}</div></div>'
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


def stories_html(md, f):
    out = []
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
        html_p = "".join(f'<p class="{"lede" if n == 0 else ""}">{wa(p)}</p>' for n, p in enumerate(paras))
        quote = f"<blockquote>{'<br>'.join(wa(c) for c in couplet)}</blockquote>" if couplet else ""
        kick = f'<p class="kicker"><b>Kicker</b>{wa(kicker)}</p>' if kicker else ""
        out.append(f'<section class="bout"><h4>{E(title.strip(" *#"))}</h4>'
                   f'{scorebox(game) if game else ""}{html_p}{quote}{kick}</section>')
    return "".join(out)


def standings(f):
    rows = "".join(
        f"<tr><td>{s['rank']}</td><td>{E(s['manager'])}{arrow(s.get('prev_rank'), s['rank'])}</td><td>{s['record']}</td>"
        f"<td class=n>{s['pf']}</td><td>{s['streak']}</td></tr>" for s in f["standings"])
    return ("<table><tr><th>#</th><th>Manager</th><th>Rec</th><th class=n>PF</th><th>Strk</th></tr>"
            + rows + "</table>")


def page(f, text, stories, weeks, title_prefix=""):
    league = E(f["league"])
    head, deck = headline(f)
    desc = E(f"{head}. {deck}")
    archive = " ".join(f'<a href="week-{w}.html">Week {w}</a>' for w in sorted(weeks, reverse=True))
    wa_html = "<br>\n".join(wa(l) for l in text.splitlines())
    matchups = f"<h3>The Matchups</h3>{stories_html(stories, f)}" if stories else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_prefix}{league} Gazette</title>
<meta property="og:title" content="{league} Gazette — Week {f['week']}">
<meta property="og:description" content="{desc}"><meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>
<header class="mast"><a href="index.html"><h1>The {league} Gazette</h1></a>
<div class="motto">All the scores that are fit to print</div></header>
<div class="dateline"><span>Season {f['season']}</span><span>Week {f['week']} Edition</span></div>
<h2 class="head">{E(head)}</h2><p class="deck">{E(deck)}</p>
{tiles(f)}
{matchups}
<h3>Standings</h3>{standings(f)}
<details><summary>📱 WhatsApp version</summary><article>{wa_html}</article></details>
<h3>Archive</h3><nav class="archive">{archive}</nav>
<footer>Every number verified against Sleeper. The jokes are not.</footer>
</main></body></html>"""


def build():
    SITE.mkdir(exist_ok=True)
    issues = {}
    for p in POSTS.glob("*_recap.txt"):
        m = NAME.search(p.name)
        facts = p.with_name(p.name.replace(".txt", ".facts.json"))
        if m and facts.exists():
            st = p.with_name(p.name.replace(".txt", ".stories.md"))
            text = "\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith("📰"))
            issues[(int(m[1]), int(m[2]))] = (json.loads(facts.read_text(encoding="utf-8")), text.strip(),
                                              st.read_text(encoding="utf-8") if st.exists() else "")
    if not issues:
        (SITE / "index.html").write_text(
            f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Gazette</title><style>{CSS}</style><main><header class=mast><h1>The Gazette</h1></header>"
            f"<p class=deck style='text-align:center;margin-top:24px'>First edition hits the stands Wednesday morning.</p></main>",
            encoding="utf-8")
        print("no issues yet; placeholder front page")
        return
    latest = max(issues)
    season = latest[0]
    weeks = [w for (s, w) in issues if s == season]
    for (s, w), (f, text, stories) in issues.items():
        if s == season:
            (SITE / f"week-{w}.html").write_text(page(f, text, stories, weeks, f"Week {w} · "), encoding="utf-8")
    f, text, stories = issues[latest]
    (SITE / "index.html").write_text(page(f, text, stories, weeks), encoding="utf-8")
    print(f"built {len(weeks)} issue(s); front page = week {latest[1]}")


if __name__ == "__main__":
    build()
