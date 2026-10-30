"""Build the watercolor artwork in docs/assets from SVG, rendered with headless Chrome.

    python docs/art/make_art.py            # writes docs/assets/*.jpg (macOS: Chrome, sips)

Every shape is generated here (seeded, so reruns are identical); the watercolor look comes from
SVG filters: turbulence-displaced edges, a darker pooled rim, and pigment granulation, with washes
layered in multiply blend.
"""

import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

INK = "#1c1e21"
GOLD = "#7a5800"
PAPER = "#fbf4e4"
SIGNAL_BLUE = "#3a76f0"

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=DM+Sans:opsz,wght@9..40,500;9..40,700&family=JetBrains+Mono:wght@500&display=block">'
)


def wash_filter(
    fid: str, seed: int, freq: float = 0.03, scale: float = 16, edge: float = 0.55
) -> str:
    """Ragged edge + darker pooled rim + granulation, the three tells of a real wash."""
    return f"""
<filter id="{fid}" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="4" seed="{seed}" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="{scale}" xChannelSelector="R"
    yChannelSelector="G" result="d"/>
  <feGaussianBlur in="d" stdDeviation="0.9" result="b"/>
  <feMorphology in="b" operator="erode" radius="2.5" result="er"/>
  <feComposite in="b" in2="er" operator="out" result="rim"/>
  <feGaussianBlur in="rim" stdDeviation="1.4" result="rimb"/>
  <feComponentTransfer in="rimb" result="rimd">
    <feFuncA type="linear" slope="{edge}"/>
  </feComponentTransfer>
  <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="{seed + 7}" result="g"/>
  <feColorMatrix in="g" type="matrix"
    values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1.1 0 0 0 1.35" result="ga"/>
  <feComposite in="b" in2="ga" operator="in" result="grain"/>
  <feMerge><feMergeNode in="grain"/><feMergeNode in="rimd"/></feMerge>
</filter>"""


PAPER_FILTER = """
<filter id="paper" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="3" result="t"/>
  <feDiffuseLighting in="t" lighting-color="#fff8ea" surfaceScale="1.6" result="l">
    <feDistantLight azimuth="45" elevation="62"/>
  </feDiffuseLighting>
  <feComposite in="l" in2="SourceGraphic" operator="arithmetic" k1="1" k2="0" k3="0" k4="0"/>
</filter>"""


def pts_to_path(pts: list[tuple[float, float]], close: bool = True) -> str:
    """Catmull-Rom through the points, as cubic Beziers."""
    pts = [pts[-1], *pts, pts[0], pts[1]] if close else [pts[0], *pts, pts[-1]]
    d = [f"M{pts[1][0]:.1f},{pts[1][1]:.1f}"]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d) + (" Z" if close else "")


def ribbon(rng, x0, y0, length, width, drift, waves, ruffle, steps=60):
    """A ruffled oral arm: a wavy centerline, swollen in the middle, with frilled edges."""
    left, right = [], []
    phase = rng.uniform(0, math.tau)
    for i in range(steps + 1):
        t = i / steps
        y = y0 + t * length
        x = x0 + drift * t * t + 26 * math.sin(phase + t * waves * math.tau) * (0.3 + t)
        w = width * (0.55 + 0.9 * math.sin(math.pi * min(1, t * 1.15))) * (1 - 0.55 * t)
        frill = ruffle * math.sin(t * 70 + phase) * (0.4 + t)
        left.append((x - w / 2 - abs(frill), y))
        right.append((x + w / 2 + abs(frill), y + frill * 0.3))
    return pts_to_path(left + right[::-1])


def tentacle(rng, x0, y0, length, drift, waves, amp, steps=50):
    pts = []
    phase = rng.uniform(0, math.tau)
    for i in range(steps + 1):
        t = i / steps
        x = x0 + drift * t**1.3 + amp * math.sin(phase + t * waves * math.tau) * (0.2 + t)
        pts.append((x, y0 + t * length))
    return pts_to_path(pts, close=False)


def jellyfish(seed: int = 11) -> tuple[str, str]:
    """Return (defs, group) for the messenger jellyfish, drawn around (0, 0) = bell center."""
    rng = random.Random(seed)
    defs = [wash_filter(f"w{i}", seed * 10 + i, scale=s) for i, s in enumerate([18, 14, 10, 7])]
    defs.append(
        wash_filter("thin", seed + 99, freq=0.05, scale=4, edge=0.3)
        + """
<radialGradient id="bellG" cx="40%" cy="20%" r="85%">
  <stop offset="0" stop-color="#fff1b8"/><stop offset=".35" stop-color="#ffc85a"/>
  <stop offset=".75" stop-color="#f08a2e"/><stop offset="1" stop-color="#d4542a"/>
</radialGradient>
<linearGradient id="armG" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#ef8b52"/><stop offset=".35" stop-color="#e98aa0"/>
  <stop offset=".7" stop-color="#b98ccb"/><stop offset="1" stop-color="#8f86c9"/>
</linearGradient>
<linearGradient id="armG2" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#f4a14a"/><stop offset=".5" stop-color="#e7768d"/>
  <stop offset="1" stop-color="#c88fc2"/>
</linearGradient>
<linearGradient id="wingG" x1="0" y1="1" x2="1" y2="0">
  <stop offset="0" stop-color="#c98d2c"/><stop offset=".6" stop-color="#e9bf5c"/>
  <stop offset="1" stop-color="#f7dd92"/>
</linearGradient>"""
    )
    g = ['<g style="mix-blend-mode:multiply">']

    # Long tentacles, behind everything, trailing down-left as the bell swims up-right.
    colors = ["#e1b23c", "#d65a73", "#e8a13a", "#c9476a", "#dcb04a"]
    for i in range(13):
        x0 = rng.uniform(-150, 150)
        d = tentacle(
            rng,
            x0,
            48 + rng.uniform(-6, 10),
            rng.uniform(300, 470),
            drift=rng.uniform(-260, -120),
            waves=rng.uniform(1.2, 2.6),
            amp=rng.uniform(8, 22),
        )
        g.append(
            f'<path d="{d}" fill="none" stroke="{colors[i % len(colors)]}" '
            f'stroke-width="{rng.uniform(1.6, 3.6):.1f}" stroke-linecap="round" '
            f'opacity="{rng.uniform(0.55, 0.85):.2f}" filter="url(#thin)"/>'
        )

    # Blue-violet underside of the bell, as in a lit translucent body.
    g.append(
        '<path d="M-150,40 C-120,95 120,95 150,40 C100,70 -100,70 -150,40Z" fill="#9db4e3" '
        'opacity=".7" filter="url(#w2)"/>'
    )

    # Oral arms: ruffled ribbons.
    for x0, length, width, drift, fill, op in [
        (-30, 330, 58, -170, "url(#armG)", 0.82),
        (25, 290, 46, -110, "url(#armG2)", 0.78),
        (-70, 250, 38, -210, "url(#armG)", 0.6),
    ]:
        d = ribbon(rng, x0, 55, length, width, drift, waves=1.4, ruffle=6)
        g.append(f'<path d="{d}" fill="{fill}" opacity="{op}" filter="url(#w1)"/>')
        g.append(
            f'<path d="{d}" fill="none" stroke="#e0762f" stroke-width="2.2" opacity=".55" '
            f'filter="url(#w3)"/>'
        )
    # Darker pooled spots inside the arms.
    for _ in range(9):
        x, y = rng.uniform(-200, 20), rng.uniform(110, 330)
        r = rng.uniform(6, 16)
        color = rng.choice(["#a5539c", "#c4465e", "#7f78c4", "#d9752c"])
        g.append(
            f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * 1.6:.0f}" fill="{color}" '
            f'opacity=".45" filter="url(#w3)"/>'
        )

    # Hermes' wings on the bell, as on the winged petasos.
    for side in (-1, 1):
        feathers = []
        for k in range(5):
            ang = math.radians(-178 + k * 15) if side < 0 else math.radians(-2 - k * 15)
            ln = 175 - k * 24
            bx, by = side * 150, -40 + k * 6
            tip = (bx + math.cos(ang) * ln, by + math.sin(ang) * ln)
            nx, ny = -math.sin(ang) * 20, math.cos(ang) * 20
            pts = [(bx, by), ((bx + tip[0]) / 2 + nx, (by + tip[1]) / 2 + ny), tip]
            pts.append(((bx + tip[0]) / 2 - nx * 0.4, (by + tip[1]) / 2 - ny * 0.4))
            feathers.append(pts_to_path(pts))
        for i, d in enumerate(feathers):
            g.append(
                f'<path d="{d}" fill="url(#wingG)" opacity="{0.78 - i * 0.06:.2f}" '
                f'filter="url(#w{1 + i % 2})"/>'
            )
            g.append(
                f'<path d="{d}" fill="none" stroke="#9c6a1c" stroke-width="1.4" opacity=".45" '
                f'filter="url(#thin)"/>'
            )

    # The bell: a scalloped dome in three washes, light left unpainted near the top.
    bell = (
        "M-178,42 C-186,-60 -110,-128 0,-128 C110,-128 186,-60 178,42 "
        "C150,62 128,48 100,60 C72,70 48,52 22,64 C-4,72 -30,54 -58,64 "
        "C-86,72 -112,50 -140,60 C-160,64 -172,56 -178,42Z"
    )
    g.append(f'<path d="{bell}" fill="url(#bellG)" opacity=".92" filter="url(#w0)"/>')
    g.append(
        '<path d="M40,-120 C120,-110 182,-50 176,40 C140,58 100,50 70,58 C120,0 110,-70 40,-120Z" '
        'fill="#d9542a" opacity=".6" filter="url(#w1)"/>'
    )
    g.append(
        '<ellipse cx="-50" cy="-72" rx="85" ry="42" fill="#fffbe8" opacity=".95" '
        'filter="url(#w2)"/>'
    )
    # Ribs radiating from the crown to each scallop.
    for k in range(-5, 6):
        x = k * 31
        g.append(
            f'<path d="M{x * 0.25:.0f},-110 Q{x * 0.8:.0f},-40 {x:.0f},{52 + abs(k) % 2 * 8}" '
            f'fill="none" stroke="#c4521f" stroke-width="{rng.uniform(5, 9):.1f}" '
            f'stroke-linecap="round" opacity=".38" filter="url(#w3)"/>'
        )
    g.append(
        f'<path d="{bell}" fill="none" stroke="#b5401e" stroke-width="2.4" opacity=".55" '
        f'filter="url(#w3)"/>'
    )
    g.append("</g>")
    return "".join(defs), "".join(g)


def bubbles(x: float, y: float) -> tuple[str, str]:
    """Rising water bubbles that become a message bubble: Signal blue, three dots."""
    defs = wash_filter("blue", 501, scale=10, edge=0.7)
    g = ['<g style="mix-blend-mode:multiply">']
    for dx, dy, r in [(40, 70, 7), (22, 40, 10), (0, 0, 0)]:
        if r:
            g.append(
                f'<circle cx="{x + dx}" cy="{y + dy}" r="{r}" fill="none" stroke="{SIGNAL_BLUE}" '
                f'stroke-width="2.5" opacity=".6" filter="url(#thin)"/>'
            )
    bx, by = x - 60, y - 70
    bubble = (
        f"M{bx},{by + 30} C{bx},{by} {bx + 25},{by - 8} {bx + 70},{by - 8} "
        f"C{bx + 115},{by - 8} {bx + 140},{by} {bx + 140},{by + 30} "
        f"C{bx + 140},{by + 60} {bx + 115},{by + 68} {bx + 70},{by + 68} "
        f"C{bx + 55},{by + 68} {bx + 40},{by + 66} {bx + 30},{by + 62} "
        f"L{bx + 8},{by + 80} L{bx + 14},{by + 54} C{bx + 4},{by + 46} {bx},{by + 38} "
        f"{bx},{by + 30}Z"
    )
    g.append(f'<path d="{bubble}" fill="{SIGNAL_BLUE}" opacity=".72" filter="url(#blue)"/>')
    for i in range(3):
        g.append(
            f'<circle cx="{bx + 42 + i * 28}" cy="{by + 30}" r="7" fill="{PAPER}" opacity=".95"/>'
        )
    g.append("</g>")
    return defs, "".join(g)


def splashes(rng, w: int, h: int) -> str:
    out = ['<g style="mix-blend-mode:multiply">']
    for _ in range(5):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        out.append(
            f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rng.uniform(80, 220):.0f}" '
            f'ry="{rng.uniform(50, 140):.0f}" fill="{rng.choice(["#f6d48e", "#f3c3a8", "#d9def2"])}"'
            f' opacity=".13" filter="url(#w0)"/>'
        )
    for _ in range(26):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        out.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(1.2, 4.5):.1f}" '
            f'fill="{rng.choice(["#e0862f", "#d65a73", "#3a76f0", "#c9a03a"])}" '
            f'opacity=".35" filter="url(#thin)"/>'
        )
    out.append("</g>")
    return "".join(out)


def page(w: int, h: int, svg_body: str, html_extra: str = "") -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>
html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:{PAPER}}}
svg{{position:absolute;inset:0}}
.t{{position:absolute;font-family:"DM Sans",sans-serif;color:{INK}}}
.mono{{font-family:"JetBrains Mono",monospace}}
</style></head><body>
<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
<rect width="{w}" height="{h}" fill="{PAPER}"/>
<rect width="{w}" height="{h}" fill="{PAPER}" filter="url(#paper)" opacity=".22"/>
{svg_body}
</svg>{html_extra}</body></html>"""


def banner(with_text: bool) -> str:
    w, h = 1200, 600
    jdefs, jelly = jellyfish()
    bdefs, bub = bubbles(0, 0)
    rng = random.Random(5)
    jx, jy = (860, 215) if with_text else (690, 200)
    bx, by = (575, 548) if with_text else (380, 470)
    body = (
        f"<defs>{PAPER_FILTER}{jdefs}{bdefs}</defs>{splashes(rng, w, h)}"
        f'<g transform="translate({jx},{jy}) rotate(14) scale(1.02)">{jelly}</g>'
        f'<g transform="translate({bx},{by}) rotate(-6)">{bub}</g>'
    )
    text = ""
    if with_text:
        text = f"""
<div class="t" style="left:72px;top:150px;width:520px">
  <div style="font-size:21px;font-weight:500;color:{GOLD};letter-spacing:.14em;
    text-transform:uppercase">Hermes plugin</div>
  <div style="font-size:76px;font-weight:700;line-height:1.02;margin-top:14px;
    letter-spacing:-.02em">signal&#8209;notify</div>
  <div style="font-size:27px;line-height:1.35;margin-top:22px;color:#3d3a33">
    A Signal text when Hermes finishes, fails, or needs you.</div>
  <div class="mono" style="display:inline-block;margin-top:34px;font-size:18px;padding:12px 18px;
    border:1.5px solid {GOLD};border-radius:10px;background:#fff8e6cc;color:{GOLD}">
    hermes plugins install signal-notify</div>
</div>"""
    return page(w, h, body, text)


MESSAGES = [
    ("⏸ Hermes paused", "cli …a41f09c2", "All 38 tests pass. Ready to tag v1.1.0?"),
    ("❓ Hermes is asking", "tui …7be3d915", "Amber or violet for the README banner?"),
    ("🔐 Hermes needs approval", "cli …a41f09c2", "git push origin main --tags"),
    ("❌ Hermes errored", "cli …0c9e44b1", "context overflow"),
]


def texts() -> str:
    w, h = 1200, 750
    jdefs, jelly = jellyfish(seed=23)
    rng = random.Random(9)
    body = (
        f"<defs>{PAPER_FILTER}{jdefs}</defs>{splashes(rng, w, h)}"
        f'<g transform="translate(960,230) rotate(18) scale(.95)">{jelly}</g>'
    )
    rows = "".join(
        f"""<div style="max-width:470px;background:#fffdf7;border:1px solid #e9dcc0;border-radius:22px
          22px 22px 6px;padding:14px 20px 16px;margin-bottom:16px;box-shadow:0 2px 0 #eadfc8">
          <div style="font-size:21px;font-weight:700">{head}
            <span class="mono" style="font-size:15px;font-weight:500;color:{GOLD}">[{where}]</span>
          </div><div style="font-size:20px;margin-top:6px;color:#3d3a33">{text}</div></div>"""
        for head, where, text in MESSAGES
    )
    html = f"""
<div class="t" style="left:72px;top:60px;width:600px">
  <div style="font-size:19px;font-weight:500;color:{GOLD};letter-spacing:.14em;
    text-transform:uppercase;margin-bottom:26px">What lands on your phone</div>
  {rows}
</div>"""
    return page(w, h, body, html)


SETTINGS = [
    ("Turn finished", True),
    ("Turn failed", True),
    ("Turn stopped", True),
    ("Questions", True),
    ("Approvals and sudo", True),
    ("Include message text", False),
]


def toggles() -> str:
    w, h = 1200, 750
    jdefs, jelly = jellyfish(seed=31)
    rng = random.Random(4)
    body = (
        f"<defs>{PAPER_FILTER}{jdefs}</defs>{splashes(rng, w, h)}"
        f'<g transform="translate(930,200) rotate(-12) scale(.9)">{jelly}</g>'
    )

    def switch(on: bool) -> str:
        track = GOLD if on else "#d8cfbd"
        knob = "26px" if on else "3px"
        return (
            f'<span style="position:relative;display:inline-block;width:52px;height:29px;'
            f'border-radius:15px;background:{track}"><span style="position:absolute;top:3px;'
            f"left:{knob};width:23px;height:23px;border-radius:50%;background:#fffdf7;"
            f'box-shadow:0 1px 2px #0003"></span></span>'
        )

    rows = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
          padding:15px 0;border-top:1px solid #eadfc8;font-size:21px">{label}{switch(on)}</div>"""
        for label, on in SETTINGS
    )
    html = f"""
<div class="t" style="left:72px;top:60px;width:520px">
  <div style="font-size:19px;font-weight:500;color:{GOLD};letter-spacing:.14em;
    text-transform:uppercase;margin-bottom:22px">Pick what texts you</div>
  <div style="background:#fffdf7e6;border:1px solid #e9dcc0;border-radius:18px;padding:10px 28px">
    {rows}</div>
  <div class="mono" style="font-size:15px;color:{GOLD};margin-top:18px">
    plugins.entries.signal-notify.settings</div>
</div>"""
    return page(w, h, body, html)


def render(html: str, name: str, w: int, h: int, tmp: Path) -> None:
    src = tmp / f"{name}.html"
    src.write_text(html, encoding="utf-8")
    shot = tmp / f"{name}.png"
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--window-size={w},{h}",
            "--virtual-time-budget=6000",
            f"--screenshot={shot}",
            src.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    # JPEG: the paper grain makes PNGs ~5 MB; at quality 82 they are a tenth of that.
    out = OUT / f"{name}.jpg"
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", str(shot), "--out", str(out)],
        check=True,
        capture_output=True,
    )
    print(f"wrote docs/assets/{name}.jpg")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        render(banner(with_text=True), "header", 1200, 600, tmp)
        render(banner(with_text=False), "banner", 1200, 600, tmp)
        render(texts(), "texts", 1200, 750, tmp)
        render(toggles(), "toggles", 1200, 750, tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
