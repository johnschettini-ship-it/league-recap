#!/usr/bin/env python3
"""Build the league newspaper from posts/. Stdlib only.
  python site.py   ->  site/index.html + site/week-N.html
Headlines and tables come from the verified facts JSON, never from the LLM.
"""
import html, json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
POSTS, SITE = HERE / "posts", HERE / "site"
NAME = re.compile(r"_(\d{4})_w(\d+)_recap\.txt$")

CSS = """
:root{--bg:#f6f1e7;--paper:#fffdf8;--ink:#1d1b17;--muted:#6b645a;--rule:#1d1b17;--accent:#b3261e;--up:#1e7a3c;--down:#b3261e}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15130f;--paper:#1f1c17;--ink:#eee8dc;--muted:#a39b8e;--rule:#eee8dc;--accent:#ff8a7a;--up:#6fd08c;--down:#ff8a7a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 Georgia,'Times New Roman',serif}
main{max-width:720px;margin:0 auto;padding:24px 16px 48px;background:var(--paper);min-height:100vh}
.mast{text-align:center;border-bottom:3px double var(--rule);padding-bottom:10px}
.mast a{color:inherit;text-decoration:none}.mast h1{font:900 clamp(28px,8vw,48px)/1.05 'Playfair Display',Georgia,serif;margin:0;letter-spacing:-.5px}
.dateline{display:flex;justify-content:space-between;font:12px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:1px;color:var(--muted);border-bottom:1px solid var(--rule);padding:8px 0;margin-bottom:20px}
h2.head{font:800 clamp(24px,6vw,34px)/1.15 'Playfair Display',Georgia,serif;margin:0 0 6px}
.deck{color:var(--muted);font-style:italic;margin:0 0 20px}
article strong{font-family:system-ui,sans-serif;font-size:.95em}
h3{font:700 13px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:1.5px;margin:32px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:6px}
table{width:100%;border-collapse:collapse;font:15px/1.3 system-ui,sans-serif}td,th{padding:7px 4px;border-bottom:1px solid color-mix(in srgb,var(--ink) 15%,transparent);text-align:left}
th{font-size:12px;text-transform:uppercase;color:var(--muted)}.n{text-align:right;font-variant-numeric:tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}
.archive a{display:inline-block;margin:0 10px 8px 0;color:var(--accent)}
.bout{border-top:1px solid var(--rule);padding-top:12px;margin-top:18px}.bout h4{font:800 22px/1.2 'Playfair Display',Georgia,serif;margin:0 0 8px}.bout p{margin:0 0 12px}
footer{margin-top:40px;font:12px system-ui,sans-serif;color:var(--muted);text-align:center}
"""


def wa(text):
    """WhatsApp markup -> safe HTML."""
    out = []
    for line in text.splitlines():
        s = html.escape(line)
        s = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", s)
        out.append(s)
    return "<br>\n".join(out)


def headline(f):
    c, h, l = f["closest"], f["high"], f["low"]
    head = f"{h['manager']} Drops {h['pts']}; {l['manager']} Sinks to {l['pts']}"
    deck = f"{c['winner']} survives {c['loser']} by {c['margin']}."
    if f.get("upsets"):
        u = f["upsets"][0]
        deck = f"Upset: No. {u['winner_prev_rank']} {u['winner']} topples No. {u['loser_prev_rank']} {u['loser']}. " + deck
    return head, deck


def standings(f):
    rows = []
    for s in f["standings"]:
        mv = ""
        if "prev_rank" in s and s["prev_rank"] != s["rank"]:
            d = s["prev_rank"] - s["rank"]
            mv = f'<span class="{"up" if d > 0 else "down"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>'
        rows.append(f"<tr><td>{s['rank']}</td><td>{html.escape(s['manager'])} {mv}</td><td>{s['record']}</td>"
                    f"<td class=n>{s['pf']}</td><td>{s['streak']}</td></tr>")
    return ("<table><tr><th>#</th><th>Manager</th><th>Rec</th><th class=n>PF</th><th>Strk</th></tr>"
            + "".join(rows) + "</table>")


def stories_html(md):
    out = []
    for block in re.split(r"^###\s*", md, flags=re.M):
        block = block.strip()
        if not block:
            continue
        title, _, body = block.partition("\n")
        paras = "".join(f"<p>{wa(p.strip())}</p>" for p in re.split(r"\n\s*\n", body) if p.strip())
        out.append(f'<section class="bout"><h4>{html.escape(title.strip(" *#"))}</h4>{paras}</section>')
    return "".join(out)


def page(f, text, stories, weeks, title_prefix=""):
    league = html.escape(f["league"])
    head, deck = headline(f)
    desc = html.escape(f"{head}. {deck}")
    archive = " ".join(f'<a href="week-{w}.html">Week {w}</a>' for w in sorted(weeks, reverse=True))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_prefix}{league} Gazette</title>
<meta property="og:title" content="{league} Gazette — Week {f['week']}">
<meta property="og:description" content="{desc}"><meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>
<header class="mast"><a href="index.html"><h1>The {league} Gazette</h1></a></header>
<div class="dateline"><span>Season {f['season']}</span><span>Week {f['week']} Edition</span></div>
<h2 class="head">{html.escape(head)}</h2><p class="deck">{html.escape(deck)}</p>
{"<h3>The Matchups</h3>" + stories_html(stories) if stories else ""}
<h3>The Rundown</h3><article>{wa(text)}</article>
<h3>Standings</h3>{standings(f)}
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
