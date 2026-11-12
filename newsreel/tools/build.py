#!/usr/bin/env python3
"""Generate the HyperFrames compositions of the Gazette newsreel.

Usage: python3 tools/build.py --gazette /path/to/league-recap [--facts data/<edition>.facts.json]

Reads:  build/timeline.json (from tools/narrate.py), the facts file of the edition in the timeline, pronunciations.json
Writes: index.html, compositions/<segment>.html for each segment of the script, compositions/captions.html, compositions/film.html

Every number and name on screen comes from the facts file. Nothing is typed by hand.
The robot "Rivet" is drawn by comic.py of the gazette repository, with the costume of that week's edition.
"""
import argparse, html, json, pathlib, random, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--gazette", required=True, help="path of the league-recap repository (for comic.py and theme.py)")
ap.add_argument("--facts", help="the facts file; the default is data/<edition>.facts.json, with the edition of build/timeline.json")
ap.add_argument("--site", default="johnschettini-ship-it.github.io/league-recap")
ap.add_argument("--format", choices=("chat", "social"), default="chat",
                help="chat: 1080x1350 for a group chat. social: 1080x1920; the lower third stays empty for the platform's buttons")
args = ap.parse_args()
sys.path.insert(0, args.gazette)
import comic, theme  # noqa: E402  (the gazette's own drawing and edition code)
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from plan import plan, surname, verb, result_line, cue_pattern, lead_line  # noqa: E402  (which facts each segment shows)

TL = json.loads((ROOT / "build" / "timeline.json").read_text())
if not args.facts and not TL.get("edition"):
    sys.exit("build/timeline.json has no edition. Run tools/narrate.py again, or pass --facts.")
F = json.loads((ROOT / (args.facts or f"data/{TL['edition']}.facts.json")).read_text())
F["league"] = F["league"].strip()                 # the gazette writes "Coozeball " with a space at the end
for key in ("league", "season", "week"):         # the narration and the pictures must be of the same edition
    if str(F[key]) != str(TL[key]):
        sys.exit(f"The narration is for {key} {TL[key]!r} and the facts file is for {key} {F[key]!r}. Build stopped.")
P = plan(F)
SAY = {k: v for k, v in json.loads((ROOT / "pronunciations.json").read_text()).items() if not k.startswith("_")}
ED = theme.edition(F)
BEATS = {b["id"]: b for b in TL["beats"]}
DUR = TL["duration"]
W, H = (1080, 1350) if args.format == "chat" else (1080, 1920)
FPS = 30                                      # the frame rate of the render
OFF = 60 if args.format == "chat" else 0      # the chat frame has no platform bar at the top, so the layout moves up
# The colours of the gazette site (site.py, :root). The accent is the accent of the edition, as on the site.
INK, PAPER, CARD, ACCENT = "#1c1b19", "#fffefb", "#f5f2ea", ED["accent"]      # --ink, --paper, --soft, --accent
RULE, UP, DOWN = "#2b2925", "#2f6b2a", "#8a2a1c"                              # --rule, --up, --down
MUTED = "#57524a"                                                             # --muted
PAPER_NAME = f"The {F['league']} Gazette"                                     # the masthead of the site
E = html.escape
WEEK, SEASON, LEAGUE = F["week"], F["season"], F["league"]

FONTS = """
    @font-face { font-family: "UnifrakturMaguntia"; src: url('assets/fonts/UnifrakturMaguntia-Book.ttf') format('truetype'); }
    @font-face { font-family: "Old Standard TT"; font-weight: 400; font-style: normal; src: url('assets/fonts/OldStandard-Regular.ttf') format('truetype'); }
    @font-face { font-family: "Old Standard TT"; font-weight: 700; font-style: normal; src: url('assets/fonts/OldStandard-Bold.ttf') format('truetype'); }
    @font-face { font-family: "Old Standard TT"; font-weight: 400; font-style: italic; src: url('assets/fonts/OldStandard-Italic.ttf') format('truetype'); }"""
BASE = FONTS + """
    #root { position: absolute; inset: 0; overflow: hidden; color: INK; font-family: "Old Standard TT", serif; }
    .clip { position: absolute; }
    .in { width: 100%; height: 100%; }
    .fraktur { font-family: "UnifrakturMaguntia", serif; line-height: 1; }
    .gothic { font-family: "League Gothic", sans-serif; text-transform: uppercase; line-height: 0.92; white-space: nowrap; }
    .b { font-weight: 700; }
    .i { font-style: italic; }
    .accent { color: ACCENT; }
    .card { background: CARD; border: 4px solid INK; box-shadow: 10px 12px 0 rgba(28, 27, 25, 0.14); }
    .hdr { position: absolute; left: 70px; top: HDRTOPpx; width: 940px; height: 84px; border-top: 6px double INK; border-bottom: 6px double INK;
           display: flex; align-items: center; justify-content: space-between; }
    .hdr .m { font-family: "UnifrakturMaguntia", serif; font-size: HDRMASTpx; line-height: 1; white-space: nowrap; }
    .hdr .w { font-family: "League Gothic", sans-serif; font-size: 40px; letter-spacing: 4px; }
    .rivet svg { width: 100%; height: 100%; display: block; }
""".replace("INK", INK).replace("ACCENT", ACCENT).replace("CARD", CARD).replace("HDRTOP", str(176 - OFF)).replace("HDRMAST", str(int(min(52, 600 / (len(PAPER_NAME) * 0.5)))))
HEADER = f'<div class="hdr"><span class="m">{E(PAPER_NAME)}</span><span class="w">NEWSREEL · WEEK {WEEK}</span></div>'


def fit(text, max_px, base, ratio=0.42):
    """A font size for one line of League Gothic that fits max_px."""
    return int(min(base, max_px / (max(1, len(text)) * ratio)))


def rivet(pose, panel):
    return comic.rivet(pose, WEEK, panel, ED)


class Scene:
    """One sub-composition: timed clips plus one paused GSAP timeline."""

    def __init__(self, sid):
        self.id, self.beat = sid, BEATS.get(sid)
        self.dur = round(self.beat["end"] - self.beat["start"], 3) if self.beat else DUR
        self.html, self.js, self.css = [], [], ""

    def local(self, t):
        return t - self.beat["start"]

    def when(self, words, fallback):
        """Local start time of the first sentence that has one of the words; else a fraction of the scene."""
        for s in self.beat["sentences"]:
            if any(re.search(cue_pattern(w), s["cap"], flags=re.I) for w in words if w):
                return max(0.1, self.local(s["start"]))
        return round(self.dur * fallback, 2)

    def when_re(self, pattern):
        """Local start time of the first sentence that matches the pattern, or None."""
        for s in self.beat["sentences"]:
            if re.search(pattern, s["cap"], flags=re.I):
                return max(0.1, self.local(s["start"]))
        return None

    def sentence(self, i):
        ss = self.beat["sentences"]
        return max(0.1, self.local(ss[min(i, len(ss) - 1)]["start"]))

    def clip(self, cid, start, box, inner, dur=None, cls="", attrs=""):
        start = round(max(0.0, min(start, self.dur - 0.3)), 2)
        dur = round(min(dur if dur is not None else self.dur, self.dur - start - 0.01), 2)
        if "rivet" in cls:
            attrs += " data-layout-ignore"          # the robot drawing has small decorative text
        if f"height:{H}px" not in box:              # every box except a full-frame one moves with the layout
            box = re.sub(r"top:(\d+)px", lambda m: f"top:{int(m.group(1)) - OFF}px", box)
        self.html.append(f'<div id="{self.id}-{cid}" class="clip"{" " + attrs.strip() if attrs.strip() else ""} data-start="{start}" data-duration="{dur}" style="{box}">'
                         f'<div id="{self.id}-{cid}-in" class="in {cls}">{inner}</div></div>')
        return start

    def tween(self, cid, frm, to, at):
        self.js.append(f'tl.fromTo("#{self.id}-{cid}-in", {json.dumps(frm)}, {json.dumps(to)}, {round(at, 2)});')

    def enter(self, cid, start, box, inner, kind="rise", dur=None, cls="", attrs=""):
        at = self.clip(cid, start, box, inner, dur, cls, attrs)
        moves = {
            "rise": ({"opacity": 0, "y": 46}, {"opacity": 1, "y": 0, "duration": 0.34, "ease": "power3.out"}),
            "slam": ({"opacity": 0, "scale": 2.3, "rotation": -9}, {"opacity": 1, "scale": 1, "rotation": 0, "duration": 0.26, "ease": "power4.in"}),
            "pop": ({"opacity": 0, "scale": 0.2}, {"opacity": 1, "scale": 1, "duration": 0.38, "ease": "back.out(1.9)"}),
            "drop": ({"opacity": 0, "y": -420, "rotation": -13}, {"opacity": 1, "y": 0, "rotation": 0, "duration": 0.46, "ease": "back.out(1.3)"}),
            "left": ({"opacity": 0, "x": -520}, {"opacity": 1, "x": 0, "duration": 0.36, "ease": "power3.out"}),
            "right": ({"opacity": 0, "x": 520}, {"opacity": 1, "x": 0, "duration": 0.36, "ease": "power3.out"}),
            "spin": ({"opacity": 0, "scale": 0.04, "rotation": -720}, {"opacity": 1, "scale": 1, "rotation": -2, "duration": 0.95, "ease": "power2.out"}),
        }
        frm, to = moves[kind]
        self.tween(cid, frm, to, at)
        return at

    def write(self):
        body = "\n    ".join(self.html)
        js = "\n      ".join(self.js)
        text = f"""<template>
  <style>{BASE}{self.css}  </style>
  <div id="root" data-composition-id="{self.id}" data-width="{W}" data-height="{H}">
    {body}
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      {js}
      window.__timelines = window.__timelines || {{}};
      window.__timelines["{self.id}"] = tl;
    }})();
  </script>
</template>
"""
        OUT.append((ROOT / "compositions" / f"{self.id}.html", text))


OUT = []            # (path, text) of each file. The files are written at the end, so a build that stops leaves the last edition complete.


def standing(manager):
    return next(s for s in F["standings"] if s["manager"] == manager)


# ---------------------------------------------------------------- n1: open
def n1():
    s = Scene("n1")
    s.css = """
    #n1-page-in { text-align: center; }
    #n1-page-in .kick { font-family: "League Gothic", sans-serif; font-size: 40px; letter-spacing: 6px; }
    #n1-page-in .m1 { font-size: M1SIZEpx; margin-top: 16px; white-space: nowrap; }
    #n1-page-in .m2 { font-size: 196px; margin-top: -8px; }
    #n1-page-in .rule { border-top: 8px double INK; margin: 20px 0 14px; }
    #n1-page-in .ve { font-size: 118px; letter-spacing: 8px; }
    #n1-page-in .tag { font-size: 38px; margin-top: 6px; }
    #n1-stamp-in .tilt { transform: rotate(-11deg); border: 9px solid ACCENT; color: ACCENT; font-size: 100px; padding: 6px 22px 0; display: inline-block; }
    #n1-leader-in { background: rgba(20, 18, 16, 0.84); }
    #n1-leader-in svg { position: absolute; left: 0; top: 0; }
""".replace("INK", INK).replace("ACCENT", ACCENT).replace("M1SIZE", str(fit(f"The {LEAGUE}", 900, 150, 0.5)))
    page = (f'<div class="kick">SEASON {SEASON} · WEEK {WEEK} · {E(ED["label"].upper())}</div>'
            f'<div class="fraktur m1">The {E(LEAGUE)}</div><div class="fraktur m2">Gazette</div><div class="rule"></div>'
            f'<div class="gothic ve">Video Edition</div><div class="i tag">“{E(ED["tagline"])}”</div>')
    s.clip("page", 0, "left:70px;top:296px;width:940px;height:620px", page)
    s.clip("rivet", 0, "left:415px;top:905px;width:250px;height:250px", rivet("reading", 1), cls="rivet")
    # the film leader: 3, 2, 1 over the masthead, 0.8 s each
    CY = 760 - OFF
    leader = (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
              f'<circle cx="540" cy="{CY}" r="330" fill="none" stroke="#fffefb" stroke-width="10"/>'
              f'<circle cx="540" cy="{CY}" r="270" fill="none" stroke="#fffefb" stroke-width="4"/>'
              f'<path d="M150 {CY} H930 M540 {CY - 390} V{CY + 390}" stroke="#fffefb" stroke-width="4"/>'
              f'<path id="n1-hand" d="M540 {CY} L540 {CY - 330}" stroke="#fffefb" stroke-width="12" stroke-linecap="round"/>'
              + "".join(f'<text id="n1-c{n}" x="540" y="{CY + 140}" text-anchor="middle" font-family="League Gothic" font-size="420" fill="#fffefb" opacity="{1 if n == 3 else 0}">{n}</text>' for n in (3, 2, 1))
              + '</svg>')
    s.clip("leader", 0, f"left:0;top:0;width:{W}px;height:{H}px", leader, dur=2.6, attrs="data-layout-allow-occlusion data-layout-allow-overlap data-layout-ignore")
    s.js.append('tl.fromTo("#n1-hand", { rotation: 0 }, { rotation: 1080, duration: 2.4, ease: "none", svgOrigin: "540 CY" }, 0);'.replace("CY", str(CY)))
    for i, n in enumerate((3, 2, 1)):
        s.js.append(f'tl.set("#n1-c{n}", {{ opacity: 1 }}, {round(i * 0.8, 2)});')
        s.js.append(f'tl.set("#n1-c{n}", {{ opacity: 0 }}, {round(i * 0.8 + 0.8, 2)});')
    s.js.append('tl.to("#n1-leader-in", { opacity: 0, duration: 0.18, ease: "power2.in" }, 2.4);')
    s.enter("stamp", s.sentence(0) + 0.05, "left:694px;top:952px;width:320px;height:150px", '<span class="gothic tilt">Extra!</span>', kind="slam")
    s.js.append(f'tl.fromTo("#n1-rivet-in", {{ y: 0 }}, {{ y: -22, duration: 0.22, ease: "power2.out", yoyo: true, repeat: 3 }}, {round(s.sentence(1), 2)});')
    s.write()


# ---------------------------------------------------------------- n2: the lead
def n2():
    s = Scene("n2")
    hi, g = P["high"], P["lead"]
    name = hi["manager"].upper()
    _, word, other = lead_line(F, hi, g)
    long_deck = len(f"{hi['manager']} {word} {other},") * 0.47 * 46 > 650      # the result line does not fit in one row
    s.css = f"""
    #n2-card-in {{ padding: 30px 34px; text-align: center; }}
    #n2-card-in .kick {{ font-family: "League Gothic", sans-serif; font-size: 46px; letter-spacing: 10px; border-bottom: 4px solid {INK}; padding-bottom: 8px; }}
    #n2-card-in .h1 {{ font-size: {fit(name, 860, 140)}px; margin-top: 22px; }}      /* 140 px at most: a short name must leave room for the label */
    #n2-card-in .h2 {{ font-size: 300px; color: {ACCENT}; margin-top: 4px; }}
    #n2-card-in .h3 {{ font-size: {fit(P["high_label"], 860, 84, 0.46)}px; letter-spacing: 3px; }}
    #n2-deck-in {{ font-size: {42 if long_deck else 46}px; text-align: center; line-height: 1.2; border-top: 6px double {INK}; padding-top: {12 if long_deck else 18}px; }}
"""
    card = (f'<div class="kick">EXTRA · WEEK {WEEK}</div><div class="gothic h1">{E(name)}</div>'
            f'<div class="gothic h2">{hi["pts"]}</div><div class="gothic h3">{E(P["high_label"])}</div>')
    s.html.append(HEADER)
    # The page turns two times as it comes in. For that second the layout check sees its lines on top of each other; that is the animation, not a fault.
    s.enter("card", 0.12, "left:70px;top:296px;width:940px;height:620px", card, kind="spin", cls="card", attrs="data-layout-allow-overlap")
    deck = (f'<span class="b">{E(hi["manager"])}</span> {word}{"<br>" if long_deck else " "}<span class="b">{E(other)}</span>,<br>'
            f'{g["winner_pts"]} to {g["loser_pts"]}')
    # A reader needs about 3 seconds for the result line, and more for long names, so it enters early when the last sentence is short.
    s.enter("deck", min(s.when([other], 0.55), s.dur - (3.7 if long_deck else 3.0)), "left:70px;top:950px;width:650px;height:190px", deck)
    s.enter("rivet", s.when([other], 0.55) + 0.25, "left:760px;top:925px;width:240px;height:240px", rivet("celebrate", 2), kind="pop", cls="rivet")
    s.write()


# ---------------------------------------------------------------- n3: upsets, or the other scores
def n3():
    s = Scene("n3")
    mode, items = P["n3"]["mode"], P["n3"]["items"]
    s.css = f"""
    #n3-title-in {{ font-size: 190px; color: {ACCENT}; }}
    .n3-tilt {{ padding: 16px 28px; height: 100%; }}
    .n3-top {{ display: flex; align-items: flex-end; justify-content: space-between; }}
    .n3-rank {{ font-size: 100px; }}
    .n3-rank small {{ font-size: 54px; letter-spacing: 4px; padding: 0 14px; color: {ACCENT}; }}
    .n3-tag {{ letter-spacing: 2px; color: {ACCENT}; padding-bottom: 8px; }}
    .n3-who {{ font-size: 40px; margin-top: 2px; white-space: nowrap; }}
"""
    s.html.append(HEADER)
    s.enter("title", 0.1, "left:70px;top:286px;width:660px;height:180px", f'<span class="gothic">{E(P["n3"]["title"])}</span>', kind="slam")
    s.enter("rivet", 0.5, "left:770px;top:270px;width:230px;height:230px", rivet("shrug", 3), kind="pop", cls="rivet")
    rows = []                              # (the time of the sentence that brings the clipping in, or None; the clipping)
    for u in items:
        who = f'<div class="n3-who"><span class="b">{E(u["winner"])}</span> {verb(u)} <span class="b">{E(u["loser"])}</span></div>'
        if mode == "upsets":
            said = s.when_re(rf"(number|no\.?|#)\s*{u['winner_prev_rank']}\b")
            top = f'<div class="gothic n3-rank">No. {u["winner_prev_rank"]}<small>over</small>No. {u["loser_prev_rank"]}</div>'
        else:
            said = s.when_re("|".join(cue_pattern(n) for n in (u["winner"], u["loser"])))
            big = (len(str(u["winner_pts"])) + len(str(u["loser_pts"]))) * 42 + 110          # the width of the two scores, in px
            top = (f'<div class="n3-top"><div class="gothic n3-rank">{u["winner_pts"]}<small>to</small>{u["loser_pts"]}</div>'
                   f'<div class="gothic n3-tag" style="font-size:{fit(u["tag"], 844 - big - 24, 46, 0.47)}px">{E(u["tag"])}</div></div>')
        rows.append((said, top + who))
    if mode == "scores":                   # the clippings come in the order that the announcer names the games
        rows.sort(key=lambda r: (r[0] is None, r[0] or 0))
    step = max(0.7, min(1.7, (s.dur - 2.4) / max(1, len(rows))))
    prev = 0.0
    for i, (said, inner) in enumerate(rows):
        t = said + 0.1 if said is not None else 0.75 + i * step
        t = max(prev + 0.5, min(t, s.dur - 3.4 - (len(rows) - 1 - i) * 0.5))      # each clipping stays on screen long enough to read
        prev = t
        at = s.enter(f"u{i}", t, f"left:{84 + i * 14}px;top:{500 + i * 218}px;width:900px;height:190px",
                     f'<div class="card n3-tilt" style="transform: rotate({(-2.4, 1.8, -1.3)[i % 3]}deg)">{inner}</div>', kind="drop")
        SFX.append(("pop", s.beat["start"] + at + 0.36, 0.5))
    s.write()


# ---------------------------------------------------------------- n4: the bench crime
def n4():
    s = Scene("n4")
    bc, g = P["crime"], P["crime_game"]
    how, other, margin = result_line(g, bc["manager"])
    lost = how == "Lost to"
    s.css = f"""
    #n4-poster-in {{ text-align: center; padding: 26px 30px; border: 10px double {INK}; background: {CARD}; }}
    #n4-poster-in .t {{ font-size: 176px; color: {ACCENT}; letter-spacing: 10px; }}
    #n4-poster-in .w {{ font-size: {fit(bc["manager"].upper(), 840, 104)}px; margin-top: 2px; }}
    #n4-poster-in .s {{ font-size: 38px; margin-top: 4px; }}
    .n4-row {{ display: flex; align-items: center; justify-content: space-between; border-top: 4px solid {INK}; padding: 14px 6px 8px; text-align: left; }}
    .n4-row .l {{ font-family: "League Gothic", sans-serif; font-size: 44px; letter-spacing: 5px; color: {ACCENT}; }}
    .n4-row .n {{ font-size: 62px; font-weight: 700; line-height: 1.05; }}
    .n4-row .p {{ font-family: "League Gothic", sans-serif; font-size: 140px; line-height: 0.9; }}
    #n4-foot-in {{ font-size: {fit(f"{how} {other}" + (f" by {margin}" if margin is not None else ""), 690, 54, 0.53)}px; text-align: center; white-space: nowrap; }}
"""
    s.html.append(HEADER)
    poster = (f'<div class="gothic t">Wanted</div><div class="gothic w">{E(bc["manager"].upper())}</div>'
              f'<div class="i s">— for a bench crime, Week {WEEK} —</div>')
    at = s.enter("poster", 0.1, "left:70px;top:290px;width:940px;height:372px", poster, kind="slam")
    SFX.append(("impact", s.beat["start"] + at + 0.2, 0.45))
    benched = (f'<div class="n4-row"><div><div class="l">LEFT ON THE BENCH</div><div class="n">{E(bc["benched"])}</div></div><div class="p">{bc["benched_pts"]}</div></div>')
    started = (f'<div class="n4-row"><div><div class="l">STARTED AT {E(bc["slot"])}</div><div class="n">{E(bc["started"])}</div></div><div class="p">{bc["started_pts"]}</div></div>')
    t1 = s.enter("benched", s.when([surname(bc["benched"]), str(bc["benched_pts"])], 0.3), "left:90px;top:672px;width:900px;height:172px", benched, kind="left")
    t2 = s.enter("started", max(t1 + 0.5, s.when([surname(bc["started"]), str(bc["started_pts"])], 0.5)), "left:90px;top:846px;width:900px;height:172px", started, kind="right")
    # The poster has the name of the team. The line below gives the other team and the margin of that game.
    foot = f'{how} <span class="b">{E(other)}</span>' + (f' by <span class="b{" accent" if lost else ""}">{margin}</span>' if margin is not None else "")
    t3 = s.enter("foot", max(t2 + 0.5, s.when([str(g["margin"]), "margin", "lost by", other], 0.75)), "left:70px;top:1042px;width:700px;height:86px", foot)
    s.enter("rivet", t3 + 0.2, "left:800px;top:985px;width:185px;height:185px", rivet("facepalm", 1), kind="pop", cls="rivet")
    s.write()


# ---------------------------------------------------------------- n5: boom and bust
def n5():
    s = Scene("n5")
    boom, bust = P["boom"], P["bust"]
    bust_won = any(r["winner"] == bust["manager"] and not r.get("tie") for r in F["results"])
    s.css = f"""
    .n5-c {{ padding: 20px 34px; display: flex; align-items: center; justify-content: space-between; height: 100%; }}
    .n5-c .t {{ font-size: 150px; }}
    .n5-c .n {{ font-weight: 700; line-height: 1.05; }}
    .n5-c .f {{ font-size: 40px; margin-top: 6px; }}
    .n5-c .p {{ font-family: "League Gothic", sans-serif; font-size: 230px; line-height: 0.9; }}
"""
    s.html.append(HEADER)
    def card(title, p, colour, extra=""):
        room = 872 - len(str(p["pts"])) * 97 - 24            # the width that the score leaves for the name, in px
        size = max(42, fit(p["player"], room, 66, 0.52))     # a long name is smaller; below 42 px it wraps
        return (f'<div class="card n5-c"><div><div class="gothic t" style="color:{colour}">{title}</div><div class="n" style="font-size:{size}px">{E(p["player"])}</div>'
                f'<div class="i f">for {E(p["manager"])}{extra}</div></div><div class="p" style="color:{colour}">{p["pts"]}</div></div>')
    s.enter("boom", 0.12, "left:70px;top:296px;width:940px;height:400px", card("Boom", boom, ACCENT), kind="left")
    tb = s.enter("bust", s.when([surname(bust["player"]), str(bust["pts"]), "bust"], 0.5), "left:70px;top:730px;width:940px;height:400px",
                 card("Bust", bust, INK, ", who won anyway" if bust_won else ""), kind="right")
    s.enter("rivet", tb + 0.4, "left:452px;top:628px;width:176px;height:176px", rivet("money", 2), kind="pop", cls="rivet")
    s.write()


# ---------------------------------------------------------------- n6: the basement
def n6():
    s = Scene("n6")
    lo, g = P["low"], P["cellar"]
    st = standing(lo["manager"])
    label = P["low_label"].upper()
    how, other, margin = result_line(g, lo["manager"])
    name = lo["manager"].upper()
    s.css = f"""
    #n6-title-in {{ font-size: {fit("THE BASEMENT", 690, 176)}px; }}
    #n6-web-in svg {{ width: 100%; height: 100%; }}
    #n6-note-in {{ text-align: center; padding: 22px 30px; }}
    #n6-note-in .l {{ font-family: "League Gothic", sans-serif; font-size: {min(46, int((690 - len(label) * 8) / (len(label) * 0.42)))}px; letter-spacing: 8px; color: {ACCENT}; }}
    #n6-note-in .n {{ font-size: {fit(name, 840, 170)}px; margin-top: 8px; }}
    #n6-note-in .p {{ font-size: 276px; margin-top: 2px; }}
    #n6-note-in .r {{ font-size: 46px; border-top: 4px solid {INK}; padding-top: 12px; margin-top: 4px; }}
    #n6-game {{ font-size: {fit(f"{how} {other}" + (f" by {margin}" if margin is not None else ""), 680, 44, 0.52)}px; margin-top: 4px; white-space: nowrap; }}
"""
    s.html.append(HEADER)
    s.enter("title", 0.1, "left:70px;top:286px;width:700px;height:170px", '<span class="gothic">The Basement</span>', kind="rise")
    web = ('<svg viewBox="0 0 200 200"><g fill="none" stroke="' + INK + '" stroke-width="2.2">'
           '<path d="M200 0 L0 0 M200 0 L30 60 M200 0 L80 130 M200 0 L150 190 M200 0 L200 200"/>'
           '<path d="M150 0 Q150 24 158 15 Q172 36 176 45 Q186 60 200 62"/><path d="M90 0 Q98 44 104 34 Q130 76 138 90 Q164 118 200 128"/>'
           '<path d="M30 0 Q44 62 50 53 Q86 116 100 135 Q140 180 200 192"/></g></svg>')
    s.clip("web", 0, "left:790px;top:262px;width:220px;height:220px", web)
    note = (f'<div class="l">{E(label)}</div><div class="gothic n">{E(name)}</div><div class="gothic p">{lo["pts"]}</div>'
            f'<div class="r">Record <span class="b">{st["record"]}</span> · Rank <span class="b">{st["rank"]}</span> of {F["teams"]}</div>'
            f'<div id="n6-game">{how} <span class="b">{E(other)}</span>' + (f' by <span class="b accent">{margin}</span>' if margin is not None else "") + '</div>')
    tn = s.enter("note", 0.45, "left:70px;top:486px;width:760px;height:650px", note, kind="rise", cls="card")
    tg = max(tn + 0.5, min(s.when([other], 0.5), s.dur - 3.0))        # with the sentence that names the other team; on screen for 3 seconds or more
    s.js.append(f'tl.fromTo("#n6-game", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.34, ease: "power3.out" }}, {round(tg, 2)});')
    s.enter("rivet", tn + 0.5, "left:850px;top:930px;width:180px;height:180px", rivet("sweat", 3), kind="pop", cls="rivet")
    s.write()


# ---------------------------------------------------------------- n7: the standings
def n7():
    s = Scene("n7")
    s.css = f"""
    #n7-title-in {{ font-size: 150px; }}
    #n7-sub-in {{ font-size: 38px; text-align: right; }}
    .n7-row {{ display: flex; align-items: center; height: 100%; border-bottom: 2px solid rgba(28, 27, 25, 0.45); font-size: 40px; }}
    .n7-row .k {{ font-family: "League Gothic", sans-serif; font-size: 50px; width: 78px; }}
    .n7-row .n {{ flex: 1; font-weight: 700; white-space: nowrap; }}
    .n7-row .m {{ width: 92px; font-family: "League Gothic", sans-serif; font-size: 38px; text-align: right; padding-right: 26px; }}
    .n7-row .r {{ font-family: "League Gothic", sans-serif; font-size: 52px; width: 96px; text-align: right; }}
    .n7-top .k, .n7-top .r {{ color: {ACCENT}; }}
    .n7-row .m.up {{ color: {UP}; }}
    .n7-row .m.dn {{ color: {DOWN}; }}
    .n7-line {{ border-bottom: 6px double {INK}; }}
    #n7-cut-in {{ font-family: "League Gothic", sans-serif; font-size: 30px; letter-spacing: 6px; color: {ACCENT}; text-align: center; }}
"""
    s.html.append(HEADER)
    s.enter("title", 0.1, "left:70px;top:284px;width:660px;height:140px", '<span class="gothic">The Standings</span>', kind="rise")
    s.enter("sub", 0.3, "left:700px;top:350px;width:310px;height:60px", f'<span class="i">after Week {WEEK}</span>')
    best = F["standings"][0]["record"]
    cut = F.get("playoff_teams") or 0
    rowh, gap = 54, 38                     # the gap holds the "PLAYOFF LINE" label
    for i, r in enumerate(F["standings"]):
        d = 0 if r.get("prev_rank") is None else r["prev_rank"] - r["rank"]
        move = "" if r.get("prev_rank") is None else ("–" if d == 0 else (f"UP {d}" if d > 0 else f"DN {-d}"))
        mcls = "m" if d == 0 else ("m up" if d > 0 else "m dn")
        cls = "n7-row" + (" n7-top" if r["record"] == best else "") + (" n7-line" if cut and r["rank"] == cut else "")
        inner = (f'<div class="{cls}"><span class="k">{r["rank"]}</span><span class="n">{E(r["manager"])}</span>'
                 f'<span class="{mcls}">{move}</span><span class="r">{r["record"]}</span></div>')
        top = 436 + i * rowh + (gap if cut and r["rank"] > cut else 0)
        s.enter(f"r{i}", 0.4 + i * 0.07, f"left:70px;top:{top}px;width:940px;height:{rowh}px", inner, kind="left")
    if cut:
        s.enter("cut", 0.4 + len(F["standings"]) * 0.07 + 0.2, f"left:70px;top:{436 + cut * rowh + 4}px;width:940px;height:{gap - 6}px",
                "PLAYOFF LINE", kind="rise")
    s.write()


# ---------------------------------------------------------------- n7b: the power rankings
def n7b():
    """The power rankings of the gazette: rank, team, move from last week, season record, and true record (the all-play record)."""
    s = Scene("n7b")
    s.css = f"""
    #n7b-title-in {{ font-size: {fit("Power Rankings", 930, 150)}px; }}
    #n7b-note-in {{ display: flex; align-items: flex-end; justify-content: space-between; font-size: 34px; line-height: 1.1; }}
    #n7b-note-in .h {{ font-family: "League Gothic", sans-serif; font-size: 34px; letter-spacing: 2px; color: {ACCENT}; white-space: nowrap; line-height: 1; }}
    #n7b-note-in .h span {{ display: inline-block; text-align: right; }}
    .n7b-row {{ display: flex; align-items: center; height: 100%; border-bottom: 2px solid rgba(28, 27, 25, 0.45); font-size: 40px; }}
    .n7b-row .k {{ font-family: "League Gothic", sans-serif; font-size: 50px; width: 78px; }}
    .n7b-row .n {{ flex: 1; font-weight: 700; white-space: nowrap; }}
    .n7b-row .m {{ width: 92px; font-family: "League Gothic", sans-serif; font-size: 38px; text-align: right; padding-right: 22px; }}
    .n7b-row .c {{ width: 86px; font-family: "League Gothic", sans-serif; font-size: 44px; text-align: right; color: {MUTED}; }}
    .n7b-row .r {{ width: 150px; font-family: "League Gothic", sans-serif; font-size: 52px; text-align: right; }}
    .n7b-top .k, .n7b-top .r {{ color: {ACCENT}; }}
    .n7b-row .m.up {{ color: {UP}; }}
    .n7b-row .m.dn {{ color: {DOWN}; }}
"""
    s.html.append(HEADER)
    s.enter("title", 0.1, "left:70px;top:284px;width:940px;height:140px", '<span class="gothic">Power Rankings</span>', kind="rise")
    note = ('<span class="i">True record: against every team, every week</span>'
            '<span class="h"><span style="width:86px">REC</span><span style="width:150px">TRUE REC</span></span>')
    s.enter("note", 0.3, "left:70px;top:432px;width:940px;height:44px", note)
    rowh = 54
    for i, r in enumerate(P["power"]):
        prev = r.get("prev_power_rank")                 # no value in the first week
        d = 0 if prev is None else prev - r["power_rank"]
        move = "" if prev is None else ("–" if d == 0 else (f"UP {d}" if d > 0 else f"DN {-d}"))
        mcls = "m" if d == 0 else ("m up" if d > 0 else "m dn")
        inner = (f'<div class="n7b-row{" n7b-top" if r["power_rank"] == 1 else ""}"><span class="k">{r["power_rank"]}</span><span class="n">{E(r["manager"])}</span>'
                 f'<span class="{mcls}">{move}</span><span class="c">{r["record"]}</span><span class="r">{r["all_play"]}</span></div>')
        s.enter(f"r{i}", 0.4 + i * 0.07, f"left:70px;top:{478 + i * rowh}px;width:940px;height:{rowh}px", inner, kind="left")
        said = s.when_re(cue_pattern(r["manager"]))     # the row of a team gets a tint when the announcer names that team
        if said is not None:
            tint = "rgba({}, {}, {}, 0.13)".format(*(int(ACCENT[k:k + 2], 16) for k in (1, 3, 5)))      # the accent of the edition
            s.js.append(f'tl.to("#n7b-r{i}-in", {{ backgroundColor: "{tint}", duration: 0.25, ease: "power1.out" }}, {round(max(said, 0.4 + i * 0.07 + 0.4), 2)});')
    s.write()


# ---------------------------------------------------------------- n8: next week
def n8():
    s = Scene("n8")
    c = P["card"]
    a, b, o = c["a"], c["b"], c["odds"]
    s.css = f"""
    #n8-title-in {{ font-size: 200px; color: {ACCENT}; text-align: center; }}
    #n8-wk-in {{ font-size: 54px; letter-spacing: 14px; text-align: center; border-top: 6px double {INK}; border-bottom: 6px double {INK}; padding: 9px 0 3px; }}
    .n8-f {{ text-align: center; }}
    .n8-f .n {{ line-height: 0.95; }}
    .n8-f .r {{ font-size: 40px; }}
    #n8-vs-in {{ font-size: 78px; text-align: center; color: {CARD}; background: {INK}; border-radius: 50%; line-height: 108px; }}
    #n8-odds-in {{ font-size: 70px; text-align: center; padding: 14px 0 4px; }}
"""
    s.html.append(HEADER)
    at = s.enter("title", 0.1, "left:70px;top:278px;width:940px;height:186px", f'<span class="gothic">{E(c["billing"])}</span>', kind="slam")
    SFX.append(("impact", s.beat["start"] + at + 0.2, 0.4))
    s.enter("wk", 0.45, "left:70px;top:472px;width:940px;height:84px", f'<span class="gothic">Week {c["week"]}</span>')
    def fighter(t):
        nm = t["manager"].upper()
        return (f'<div class="n8-f"><div class="gothic n" style="font-size:{fit(nm, 900, 122)}px">{E(nm)}</div>'
                f'<div class="r">No. {t["rank"]} · <span class="b">{t["record"]}</span></div></div>')
    s.enter("a", 0.8, "left:70px;top:578px;width:940px;height:166px", fighter(a), kind="left")
    s.enter("vs", 1.1, "left:486px;top:752px;width:108px;height:108px", '<span class="gothic">vs</span>', kind="pop")
    s.enter("b", 1.3, "left:70px;top:868px;width:940px;height:166px", fighter(b), kind="right")
    # the odds replace nothing: they land on the fighters' band when the announcer says them
    odds = f'<span class="gothic">The odds: <span class="accent">{E(o["favorite"])}</span> {o["favorite_pct"]}%</span>'
    s.css += f"    #n8-odds-in {{ background: {CARD}; border: 4px solid {INK}; box-shadow: 10px 12px 0 rgba(28,27,25,.14); }}\n"
    s.enter("odds", s.when([str(o["favorite_pct"]), "percent", "odds", "money"], 0.62), "left:70px;top:1048px;width:940px;height:100px", odds, kind="rise")
    s.write()


# ---------------------------------------------------------------- n9: sign-off
def n9():
    s = Scene("n9")
    s.css = f"""
    #n9-mast-in {{ text-align: center; }}
    #n9-mast-in .m1 {{ font-size: {fit(f"The {LEAGUE}", 900, 100, 0.5)}px; white-space: nowrap; }}
    #n9-mast-in .m2 {{ font-size: 136px; margin-top: -6px; }}
    #n9-news-in {{ font-size: {fit("THAT’S THE NEWS", 900, 132)}px; text-align: center; border-top: 8px double {INK}; padding-top: 16px; }}
    #n9-end-in {{ text-align: center; padding: 22px 20px; }}
    #n9-end-in .a {{ font-size: 96px; color: {ACCENT}; }}
    #n9-end-in .u {{ font-size: 37px; font-weight: 700; margin-top: 10px; }}
    #n9-end-in .t {{ font-size: 48px; margin-top: 10px; letter-spacing: 6px; }}
"""
    s.clip("mast", 0, "left:70px;top:236px;width:940px;height:250px", f'<div class="fraktur m1">The {E(LEAGUE)}</div><div class="fraktur m2">Gazette</div>')
    s.enter("news", 0.15, "left:70px;top:490px;width:940px;height:160px", '<span class="gothic">That’s the news</span>', kind="slam")
    s.enter("rivet", 0.6, "left:440px;top:650px;width:200px;height:200px", rivet("celebrate", 3), kind="pop", cls="rivet")
    last = s.beat["sentences"][-1]
    site = E(args.site) if len(args.site) <= 46 else E(args.site).replace("/league-recap/", "/league-recap/<br>")      # a long address breaks at a slash, not inside a word
    end = (f'<div class="gothic a">Read the full edition</div><div class="u">{site}</div><div class="t">— 30 —</div>')
    s.enter("end", s.sentence(len(s.beat["sentences"]) - 1) if len(s.beat["sentences"]) > 1 else 1.2,
            "left:70px;top:866px;width:940px;height:270px", end, kind="rise", cls="card")
    s.write()


# ---------------------------------------------------------------- captions
GLUE = "\ue000"            # holds the words of a name together while a sentence is cut into captions
SMALL = {"the", "a", "an", "our", "of", "for", "to", "and", "has", "have", "is", "in", "at", "with", "on", "by", "its", "their"}


def names_in_facts():
    """Team names and player names of the facts that have more than one word."""
    found = {s["manager"] for s in F["standings"]}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("player", "benched", "started") and isinstance(v, str):
                    found.add(v)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(F)
    return sorted((n for n in found if " " in n), key=len, reverse=True)


def spoken_len(word):
    word = word.replace(GLUE, " ")
    for name, say in SAY.items():
        if name in word:
            return len(say) + len(word) - len(name)
    digits = sum(ch.isdigit() for ch in word)
    return len(word) + digits * 5


def caption_groups():
    units = names_in_facts() + ["true record", "True record", "power rankings", "Power rankings", "Main Event"]      # a name or a fixed term stays in one caption
    text_of = lambda ch: " ".join(ch).replace(GLUE, " ")
    groups = []
    for b in TL["beats"]:
        for sen in b["sentences"]:
            cap = sen["cap"]
            for u in units:
                cap = cap.replace(u, u.replace(" ", GLUE))
            words = cap.split(" ")
            chunks, cur, chars = [], [], 0
            for w in words:
                if cur and (sum(x.count(GLUE) + 1 for x in cur) >= 4 or chars + len(w) + 1 > 25):
                    chunks.append(cur); cur, chars = [], 0
                cur.append(w); chars += len(w) + 1
            if cur:
                if chunks and len(cur) == 1 and len(text_of(chunks[-1] + cur)) <= 30:
                    chunks[-1] += cur
                else:
                    chunks.append(cur)
            for i in range(len(chunks) - 1):          # a caption does not end on a small word: the word goes to the next caption
                if len(chunks[i]) >= 2 and chunks[i][-1].lower() in SMALL and len(text_of([chunks[i][-1]] + chunks[i + 1])) <= 32:
                    chunks[i + 1].insert(0, chunks[i].pop())
            i = 0
            while i < len(chunks) - 1:                # a caption of one word joins the next caption when the two fit
                if len(chunks[i]) == 1 and GLUE not in chunks[i][0] and len(text_of(chunks[i] + chunks[i + 1])) <= 32:
                    chunks[i:i + 2] = [chunks[i] + chunks[i + 1]]
                else:
                    i += 1
            total = sum(spoken_len(w) for w in words)
            share = lambda ch: (sen["end"] - sen["start"]) * sum(spoken_len(w) for w in ch) / total
            i = 0
            while i < len(chunks):        # a caption that stays for more than 2.9 s reads as a frozen screen: cut it at its most even point
                ch = chunks[i]
                if share(ch) > 2.9 and len(ch) >= 2:
                    k = min(range(1, len(ch)), key=lambda k: abs(sum(spoken_len(w) for w in ch[:k]) - sum(spoken_len(w) for w in ch[k:])))
                    chunks[i:i + 1] = [ch[:k], ch[k:]]
                else:
                    i += 1
            t = sen["start"]
            for ch in chunks:
                d = share(ch)
                groups.append([t, t + d, text_of(ch)])
                t += d
    for i, g in enumerate(groups):            # hold each group until the next one when the pause is short
        nxt = groups[i + 1][0] if i + 1 < len(groups) else DUR
        g[1] = nxt if nxt - g[1] <= 0.7 else g[1] + 0.25
    return groups


def captions():
    rows, n = [], 0
    # A caption starts and ends in the middle between two video frames. Then no frame is on the border of two captions:
    # each frame shows one caption, never two and never none. (Before, a hole of 0.01 s between two captions made the strip blink.)
    snap = lambda t: (int(t * FPS) + 0.5) / FPS
    for start, end, text in caption_groups():
        start, end = snap(start), snap(end)
        size = 56 if len(text) <= 32 else max(40, int(920 / (len(text) * 0.51)))      # one size; only a very long caption is smaller
        rows.append(f'<div id="cap-{n}" class="clip" data-start="{start:.4f}" data-duration="{max(2 / FPS, end - start):.4f}" '
                    f'style="left:70px;top:{1184 - OFF}px;width:940px;height:124px"><div class="cap" style="font-size:{size}px"><span>{E(text)}</span></div></div>')
        n += 1
    text = f"""<template>
  <style>{FONTS}
    #root {{ position: absolute; inset: 0; }}
    .clip {{ position: absolute; }}
    .cap {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; text-align: center;
            font-family: "Old Standard TT", serif; font-weight: 700; color: {INK}; background: {CARD};
            border-top: 6px double {INK}; border-bottom: 6px double {INK}; white-space: nowrap; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
    {chr(10).join('    ' + r for r in rows).strip()}
  </div>
  <script>
    window.__timelines["captions"] = gsap.timeline({{ paused: true }});
  </script>
</template>
"""
    OUT.append((ROOT / "compositions" / "captions.html", text))
    return n


# ---------------------------------------------------------------- old film overlay
def film():
    rng = random.Random(1938)             # a fixed seed: every build gives the same flicker and scratches
    wrap = lambda rows: "[\n        " + ",\n        ".join(", ".join(json.dumps(r) for r in rows[i:i + 8]) for i in range(0, len(rows), 8)) + "\n      ]"
    flicker = [round(rng.uniform(0.0, 0.012), 3) for _ in range(int(DUR / 0.13))]     # the frame darkens a little, about 8 times each second
    scratches, t = [], 0.4
    while t < DUR - 1:                    # a thin line jumps across the frame, then goes away
        scratches.append([round(t, 2), rng.choice(("a", "b")), rng.randint(60, W - 60), round(rng.uniform(0.25, 0.6), 2), round(t + rng.uniform(0.08, 0.5), 2)])
        t += rng.uniform(0.5, 2.2)
    dust, t = [], 0.8
    while t < DUR - 1:                    # a speck shows for two frames
        dust.append([round(t, 2), rng.randint(40, W - 60), rng.randint(200, H - 300), round(rng.uniform(0.5, 1.8), 2)])
        t += rng.uniform(0.35, 1.5)
    cuts = [round(b["start"], 2) for b in TL["beats"][1:]]                             # a white flash on each cut, like a splice
    js = [
        f"const FLICKER = {wrap(flicker)};",
        f"const SCRATCHES = {wrap(scratches)};",
        f"const DUST = {wrap(dust)};",
        f"const CUTS = {json.dumps(cuts)};",
        f'tl.to("#film-flicker", {{ keyframes: {{ opacity: FLICKER, easeEach: "none" }}, duration: {DUR}, ease: "none" }}, 0);',
        'SCRATCHES.forEach(([t, which, x, o, end]) => { tl.set("#film-scratch-" + which, { x: x, opacity: o }, t); tl.set("#film-scratch-" + which, { opacity: 0 }, end); });',
        'DUST.forEach(([t, x, y, k]) => { tl.set("#film-dust", { x: x, y: y, scale: k, opacity: 0.75 }, t); tl.set("#film-dust", { opacity: 0 }, t + 0.07); });',
        'CUTS.forEach((t) => { tl.set("#film-flash", { opacity: 0.6 }, t); tl.to("#film-flash", { opacity: 0, duration: 0.14, ease: "power1.out" }, t + 0.01); });',
    ]
    grain = (ROOT / "compositions" / "components" / "grain-overlay.html").read_text()
    grain = re.sub(r"<!--.*?-->", "", grain, flags=re.S).strip()
    # a lighter and slower grain than the component default: a fast grain makes the video file about three times larger
    assert "opacity: 0.15;" in grain and "hf-grain-noise 0.5s steps(1) infinite" in grain, "the grain component changed"
    grain = grain.replace("opacity: 0.15;", "opacity: 0.03;").replace("hf-grain-noise 0.5s steps(1) infinite", "hf-grain-noise 1.1s steps(1) infinite")
    style = re.search(r"<style>(.*?)</style>", grain, flags=re.S).group(1)
    markup = re.sub(r"<style>.*?</style>", "", grain, flags=re.S).strip()
    text = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    .film-layer {{ position: absolute; inset: 0; }}
    #film-vignette {{ background: radial-gradient(ellipse at 50% 46%, rgba(0, 0, 0, 0) 70%, rgba(0, 0, 0, 0.04) 100%); }}
    #film-flicker {{ background: #000; opacity: 0; }}
    #film-flash {{ background: #fff; opacity: 0; }}
    .film-scratch {{ position: absolute; top: 0; left: 0; width: 3px; height: {H}px; background: rgba(28, 27, 25, 0.5); opacity: 0; }}
    #film-scratch-b {{ width: 2px; background: rgba(20, 20, 20, 0.8); }}
    #film-dust {{ position: absolute; left: 0; top: 0; width: 16px; height: 11px; border-radius: 50%; background: rgba(15, 15, 15, 0.9); opacity: 0; }}
    {style.strip()}
  </style>
  <div id="root" data-composition-id="film" data-width="{W}" data-height="{H}" data-layout-ignore>
    {markup}
    <div id="film-scratch-a" class="film-scratch" data-layout-ignore></div>
    <div id="film-scratch-b" class="film-scratch" data-layout-ignore></div>
    <div id="film-dust" data-layout-ignore></div>
    <div id="film-vignette" class="film-layer" data-layout-ignore></div>
    <div id="film-flicker" class="film-layer" data-layout-ignore></div>
    <div id="film-flash" class="film-layer" data-layout-ignore></div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join('      ' + j for j in js).strip()}
      window.__timelines["film"] = tl;
    }})();
  </script>
</template>
"""
    OUT.append((ROOT / "compositions" / "film.html", text))


# ---------------------------------------------------------------- sound effects and the root file
SFX = []            # (kind, absolute time, volume), filled by the scenes
SFX_SRC = {"whoosh": "whoosh.mp3", "pop": "pop.mp3", "impact": "impact-bass-1.mp3"}


def sfx_files(skill_dir):
    """Copy the bundled effects into the project with the same narrow band as the voice."""
    out = ROOT / "assets" / "audio" / "sfx"
    out.mkdir(parents=True, exist_ok=True)
    durs = {}
    for kind, name in SFX_SRC.items():
        dst = out / f"{kind}.wav"
        if not dst.exists():
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(pathlib.Path(skill_dir) / name),
                            "-af", "highpass=f=250,lowpass=f=3600,aresample=44100", "-ac", "1", str(dst)], check=True)
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)], capture_output=True, text=True, check=True)
        durs[kind] = float(p.stdout.strip())
    return durs


def index(durs):
    hosts = []
    for i, b in enumerate(TL["beats"]):
        hosts.append(f'<div id="{b["id"]}" data-composition-id="{b["id"]}" data-composition-src="compositions/{b["id"]}.html" '
                     f'data-start="{b["start"]}" data-duration="{round(b["end"] - b["start"], 3)}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:1"></div>')
    audio = [f'<audio id="vo" class="clip" data-start="0" data-duration="{DUR}" data-track-index="4" data-volume="1" src="assets/audio/narration.mp3"></audio>']
    for n, (kind, at, vol) in enumerate(sorted(SFX, key=lambda x: x[1])):
        d = min(durs[kind], DUR - at - 0.05)
        audio.append(f'<audio id="sfx-{n}-{kind}" class="clip" data-start="{round(at, 2)}" data-duration="{round(d, 2)}" data-track-index="{5 + n % 2}" '
                     f'data-volume="{vol}" src="assets/audio/sfx/{kind}.wav"></audio>')
    text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{E(PAPER_NAME)} — Newsreel, Week {WEEK}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {PAPER}; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      #paper {{ position: absolute; inset: 0; background: {PAPER}; }}
      #topbar {{ position: absolute; left: 0; top: 0; width: {W}px; height: 16px; background: {ACCENT}; z-index: 2; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="{W}" data-height="{H}">
      <div id="paper" data-layout-ignore></div>
      <div id="topbar" data-layout-ignore></div>
      {chr(10).join('      ' + h for h in hosts).strip()}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{DUR}"
           data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:5"></div>
      <div id="film" data-composition-id="film" data-composition-src="compositions/film.html" data-start="0" data-duration="{DUR}"
           data-track-index="3" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:9"></div>
      {chr(10).join('      ' + a for a in audio).strip()}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    OUT.append((ROOT / "index.html", text))


if __name__ == "__main__":
    (ROOT / "compositions").mkdir(exist_ok=True)
    SFX.append(("whoosh", BEATS["n2"]["start"] + 0.12, 0.5))
    scenes = {"n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5, "n6": n6, "n7": n7, "n7b": n7b, "n8": n8, "n9": n9}
    for b in TL["beats"]:                  # the script gives the segments and their order
        if b["id"] not in scenes:
            sys.exit(f"The script has a segment {b['id']!r}. The builder has no picture for it.")
        scenes[b["id"]]()
    n_caps = captions()
    film()
    skill_sfx = ROOT.parent / ".claude" / "skills" / "media-use" / "audio" / "assets" / "sfx"
    index(sfx_files(skill_sfx))
    for path, text in OUT:                 # every scene is built: write the files now
        path.write_text(text)
    print(f"wrote index.html, {len(TL['beats'])} scenes, {n_caps} caption groups, {len(SFX)} sound effects; duration {DUR} s; edition {ED['label']}")
