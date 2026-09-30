"""'The Funnies': Rivet, the Gazette's original tin-can robot reporter, drawn in ink as SVG.
The writer picks a pose + line per panel; this file draws it. Stdlib only."""
import html
import re

INK, PAPER = "#1c1b19", "#fffefb"
POSES = ("reading", "celebrate", "shrug", "facepalm", "sweat", "bench", "trophy", "money")

ARMS = {  # shoulder -> elbow -> hand, for (left, right)
    "default":   [((72, 104), (62, 124), (60, 144)), ((128, 104), (138, 124), (140, 144))],
    "reading":   [((72, 104), (60, 124), (72, 132)), ((128, 104), (140, 124), (128, 132))],
    "celebrate": [((72, 102), (56, 80), (46, 56)), ((128, 102), (144, 80), (154, 56))],
    "shrug":     [((72, 104), (50, 116), (44, 96)), ((128, 104), (150, 116), (156, 96))],
    "facepalm":  [((72, 104), (62, 124), (60, 144)), ((128, 104), (146, 88), (116, 66))],
    "sweat":     [((72, 104), (64, 122), (58, 138)), ((128, 104), (136, 122), (142, 138))],
    "bench":     [((72, 104), (62, 124), (60, 144)), ((128, 104), (152, 100), (172, 96))],
    "trophy":    [((72, 102), (56, 80), (46, 56)), ((128, 102), (148, 84), (156, 58))],
    "money":     [((72, 104), (62, 124), (60, 144)), ((128, 104), (148, 110), (162, 96))],
}


def _arm(pts):
    (a, b), (c, d), (e, f) = pts
    return (f'<path d="M{a} {b} Q{c} {d} {e} {f}" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M{a} {b} Q{c} {d} {e} {f}" fill="none" stroke="{PAPER}" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="{e}" cy="{f}" r="6" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>')


def _props(pose):
    p = {
        "reading": f'<g transform="rotate(-4 100 130)"><rect x="58" y="112" width="84" height="46" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
                   f'<text x="100" y="125" text-anchor="middle" font-family="UnifrakturMaguntia,serif" font-size="11" fill="{INK}">Gazette</text>'
                   + "".join(f'<line x1="64" y1="{y}" x2="136" y2="{y}" stroke="{INK}" stroke-width="1"/>' for y in (131, 137, 143, 149)) + "</g>",
        "celebrate": "".join(f'<path d="M{x} {y} l0 -8 M{x - 4} {y - 4} l8 0" stroke="{INK}" stroke-width="2"/>' for x, y in ((30, 40), (170, 40), (40, 20), (160, 22))),
        "shrug": f'<text x="146" y="36" text-anchor="middle" font-family="Old Standard TT,serif" font-size="22" fill="{INK}">?</text>',
        "sweat": "".join(f'<path d="M{x} {y} q-4 7 0 10 q4 -3 0 -10z" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>' for x, y in ((62, 44), (140, 50), (146, 64))),
        "bench": f'<rect x="150" y="150" width="46" height="7" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
                 f'<line x1="154" y1="157" x2="154" y2="176" stroke="{INK}" stroke-width="2.5"/><line x1="192" y1="157" x2="192" y2="176" stroke="{INK}" stroke-width="2.5"/>'
                 f'<ellipse cx="173" cy="143" rx="11" ry="7" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/><line x1="167" y1="143" x2="179" y2="143" stroke="{INK}" stroke-width="1.5"/>',
        "trophy": f'<g transform="translate(56 -26)"><path d="M86 42 h28 v8 q0 14 -14 16 q-14 -2 -14 -16z" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
                  f'<path d="M86 46 q-8 0 -6 8 q2 6 8 6 M114 46 q8 0 6 8 q-2 6 -8 6" fill="none" stroke="{INK}" stroke-width="2"/>'
                  f'<rect x="96" y="66" width="8" height="6" fill="{INK}"/><rect x="90" y="72" width="20" height="5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/></g>'
                  + "".join(f'<path d="M{x} {y} l0 -8 M{x - 4} {y - 4} l8 0" stroke="{INK}" stroke-width="2"/>' for x, y in ((186, 20), (130, 14))),
        "money": "".join(f'<g transform="rotate({r} {x} {y})"><rect x="{x - 10}" y="{y - 6}" width="20" height="12" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>'
                         f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-family="Old Standard TT,serif" font-size="10" font-weight="700" fill="{INK}">$</text></g>'
                         for x, y, r in ((168, 80, -20), (182, 58, 15), (156, 50, -8), (186, 100, 25))),
    }
    return p.get(pose, "")


def rivet(pose):
    """Rivet: boxy tin head, rivets, spring antenna topped with a football, chest dial, stubby legs."""
    pose = pose if pose in ARMS else "default"
    shocked = pose in ("sweat", "facepalm")
    happy = pose in ("celebrate", "trophy", "money")
    eyes = "".join(
        f'<circle cx="{x}" cy="62" r="8" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
        f'<circle cx="{x + (0 if shocked else 1)}" cy="{62 if shocked else 63}" r="{2 if shocked else 3.2}" fill="{INK}"/>'
        for x in (88, 112))
    if pose == "facepalm":
        eyes = f'<circle cx="88" cy="62" r="8" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/><circle cx="88" cy="63" r="3" fill="{INK}"/>'
    mouth = (f'<path d="M88 76 q12 10 24 0" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>' if happy else
             f'<path d="M88 78 q3 -3 6 0 q3 3 6 0 q3 -3 6 0 q3 3 6 0" fill="none" stroke="{INK}" stroke-width="2.2"/>' if shocked else
             f'<rect x="88" y="74" width="24" height="7" rx="1" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
             + "".join(f'<line x1="{x}" y1="74" x2="{x}" y2="81" stroke="{INK}" stroke-width="1.3"/>' for x in (94, 100, 106)))
    brows = (f'<path d="M80 54 l14 -5 M120 54 l-14 -5" stroke="{INK}" stroke-width="2.5"/>' if pose == "shrug" else "")
    rivets = "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{INK}"/>' for x, y in ((75, 45), (125, 45), (75, 83), (125, 83), (76, 97), (124, 97), (76, 141), (124, 141)))
    hatch = "".join(f'<line x1="{x}" y1="94" x2="{x - 10}" y2="144" stroke="{INK}" stroke-width=".8"/>' for x in range(116, 128, 4))
    return (
        f'<svg viewBox="0 0 200 200" class="rivet" role="img" aria-label="Rivet the robot, {html.escape(pose)}">'
        f'<line x1="20" y1="184" x2="180" y2="184" stroke="{INK}" stroke-width="2"/>'
        + "".join(f'<line x1="{x}" y1="186" x2="{x - 6}" y2="192" stroke="{INK}" stroke-width="1"/>' for x in range(30, 180, 14))
        + f'<path d="M100 40 l0 -4 l-5 -3 l10 -4 l-10 -4 l5 -3 l0 -3" fill="none" stroke="{INK}" stroke-width="2.2"/>'
          f'<path d="M87 14 Q100 3 113 14 Q100 25 87 14z" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>'
          f'<line x1="95" y1="14" x2="105" y2="14" stroke="{INK}" stroke-width="1.4"/>'
          + "".join(f'<line x1="{x}" y1="11.5" x2="{x}" y2="16.5" stroke="{INK}" stroke-width="1.2"/>' for x in (97, 100, 103))
          + f'<rect x="80" y="146" width="13" height="30" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
          f'<rect x="107" y="146" width="13" height="30" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
          f'<ellipse cx="84" cy="179" rx="12" ry="5" fill="{INK}"/><ellipse cx="116" cy="179" rx="12" ry="5" fill="{INK}"/>'
          f'<rect x="70" y="92" width="60" height="56" rx="4" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>{hatch}'
          f'<circle cx="100" cy="116" r="11" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>'
          f'<line x1="100" y1="116" x2="{107 if happy else 93}" y2="110" stroke="{INK}" stroke-width="2"/>'
          f'<line x1="84" y1="136" x2="116" y2="136" stroke="{INK}" stroke-width="1.5"/>'
          f'<rect x="93" y="86" width="14" height="7" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
          f'<rect x="72" y="40" width="56" height="46" rx="5" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>'
          f'<rect x="66" y="56" width="6" height="14" fill="{PAPER}" stroke="{INK}" stroke-width="2"/><rect x="128" y="56" width="6" height="14" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
        + rivets + eyes + brows + mouth + "".join(_arm(a) for a in ARMS[pose]) + _props(pose) + "</svg>")


def parse(block_text):
    """'STRIP: title' already removed; lines like '1. pose: speech'."""
    panels = []
    for line in block_text.splitlines():
        m = re.match(r"\s*\d+[.)]\s*([a-z]+)\s*[:—–-]\s*(.+)$", line.strip(), re.I)
        if m:
            pose = m.group(1).lower()
            panels.append((pose if pose in POSES else "reading", m.group(2).strip().strip('"“”')))
    return panels[:3]
