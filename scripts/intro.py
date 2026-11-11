#!/usr/bin/env python3
"""Render the animated intro cards (hero, projects, connect) for both themes.

Animation is plain CSS inside each SVG, which GitHub plays in <img> tags; it
stops for viewers who ask for reduced motion. Static content: edit the data
below and rerun, no token needed.
"""
import base64
import os
import re
import urllib.request
from xml.sax.saxutils import escape

from contributions import ASSETS, HALF, PALETTES, SANS, USER, WIDE, avatar_uri

HANDLE = "@dhananjay6561"
FIRST, LAST = "Dhananjay", "Aggarwal."
STATUS = "Shipping from Bangalore"
# the hero line rotates through these; the first word is the highlighted verb
LINES = ["Building for the web, Android and AI agents.",
         "Shipping side projects people actually use.",
         "Sharing one real AI tool a day on Instagram."]
ABOUT = "Full stack developer from Bangalore, India."
CHIPS = ["Full stack", "AI agents", "Android", "Dev tools"]

PROJECTS = [
    dict(slug="intervueclub", verb="Building", title="IntervueClub",
         desc=["Free system design interview prep:", "deep-written problems and an HLD course."],
         stack="Next.js · Drizzle · Postgres", motif="system"),
    dict(slug="dot", verb="Shipping", title="Dot",
         desc=["Offline music player for Android and", "Nothing Phone. Glyph lights on the beat."],
         stack="Kotlin · Jetpack Compose", motif="matrix"),
    dict(slug="design-md-hub", verb="Curating", title="design-md-hub",
         desc=["120 brand design systems as", "DESIGN.md specs for AI coding agents."],
         stack="Markdown · HTML", motif="swatches"),
    dict(slug="diskwhy", verb="Tinkering", title="diskwhy",
         desc=["A CLI that finds what is eating your", "disk and cleans it up, safely."],
         stack="Go · CLI", motif="terminal"),
]
SOCIALS = [
    dict(slug="linkedin", icon="linkedin", color="#0A66C2", title="LinkedIn", sub="in/dhananjay6561"),
    dict(slug="instagram", icon="instagram", color="#E4405F", title="Instagram", sub="@dhananjaydontknow"),
    dict(slug="leetcode", icon="leetcode", color="#FFA116", title="LeetCode", sub="u/dhananjay6561"),
    dict(slug="email", icon="gmail", color="#EA4335", title="Email", sub="dhananjay6561@gmail.com"),
]
GREEN = {"dark": "#3fb950", "light": "#1a7f37"}
NOTHING_RED = "#D71921"

MOTION = """
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes ping{0%{transform:scale(1);opacity:.65}80%,100%{transform:scale(2.8);opacity:0}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes flow{to{stroke-dashoffset:-24}}
@keyframes glide{0%{transform:translateX(0);opacity:0}10%,90%{opacity:1}100%{transform:translateX(700px);opacity:0}}
@keyframes line{0%,30%{opacity:1;transform:none}34%{opacity:0;transform:translateY(-10px)}35%,96%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:none}}
@keyframes blink{50%{opacity:0}}
@keyframes eq{0%,100%{opacity:1}50%{opacity:.15}}
@keyframes fan{0%,100%{transform:rotate(var(--a))}50%{transform:rotate(calc(var(--a) * 1.6))}}
@keyframes fill{0%,60%{transform:scaleX(1)}72%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes nudge{0%,100%{transform:translate(0,0)}50%{transform:translate(3px,-3px)}}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 28s linear infinite}
.orbit{transform-box:view-box;animation:spin 9s linear infinite}
.ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out infinite}
.float{animation:float 4.5s ease-in-out infinite}
.flow{stroke-dasharray:4 4;animation:flow 1.2s linear infinite}
.glide{animation:glide 6s ease-in-out infinite}
.line{opacity:0;animation:line 9s ease-in-out infinite}
.blink{animation:blink 1.1s steps(1) infinite}
.eq{animation:eq 1.4s ease-in-out infinite}
.fan{transform-box:view-box;animation:fan 5s ease-in-out infinite}
.fill{transform-box:fill-box;transform-origin:left;animation:fill 6s cubic-bezier(.3,.7,.2,1) infinite}
.nudge{animation:nudge 2.2s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.line{opacity:0}.l0{opacity:1}}
"""


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def simple_icon(slug):
    return re.search(r'<path d="([^"]+)"', get(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg")).group(1)


def card(w, h, p, title, inner, glow=None):
    defs = ""
    if glow:
        gx, gy, gr = glow
        defs = (f'<defs><radialGradient id="glow" cx="{gx}" cy="{gy}" r="{gr}" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0" stop-color="{p["blue"]}" stop-opacity="0.22"/>'
                f'<stop offset="1" stop-color="{p["blue"]}" stop-opacity="0"/></radialGradient></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f'<style>text{{font-family:{SANS}}}{MOTION}</style>{defs}'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{p["card"]}" stroke="{p["line"]}"/>'
            + (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="url(#glow)"/>' if glow else "")
            + f'{inner}</svg>')


def arrow(p, x, y):
    return (f'<g class="nudge"><path d="M{x - 7} {y + 7} L{x + 7} {y - 7} M{x - 3} {y - 7} H{x + 7} V{y + 3}" '
            f'fill="none" stroke="{p["dim"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>')


def hero(theme, p, avatar):
    w, h = WIDE, 330
    cx, cy, r = w - 150, 196, 90
    inner = f'<text x="36" y="44" font-size="11" font-weight="700" letter-spacing="2" fill="{p["blue"]}">{HANDLE.upper()}</text>'
    sx = w - 36 - 6.4 * len(STATUS) - 14
    inner += (f'<circle class="ping" cx="{sx}" cy="40" r="4" fill="{GREEN[theme]}"/>'
              f'<circle cx="{sx}" cy="40" r="4" fill="{GREEN[theme]}"/>'
              f'<text x="{w - 36}" y="44" text-anchor="end" font-size="12" fill="{p["dim"]}">{STATUS}</text>')
    inner += f'<line x1="36" y1="62" x2="{w - 36}" y2="62" stroke="{p["line"]}"/>'
    inner += (f'<g class="glide"><rect x="36" y="61" width="90" height="2" rx="1" fill="{p["blue"]}" opacity="0.8"/></g>')
    inner += (f'<text x="34" y="134" font-size="62" font-weight="800" letter-spacing="-2" fill="{p["fg"]}">{FIRST}</text>'
              f'<text x="34" y="198" font-size="62" font-weight="800" '
              f'letter-spacing="-2" fill="{p["blue"]}">{LAST}</text>')
    for i, line in enumerate(LINES):
        verb, rest = line.split(" ", 1)
        inner += (f'<text class="line l{i}" style="animation-delay:{3 * i}s" x="36" y="240" font-size="18" font-weight="600" '
                  f'fill="{p["fg"]}"><tspan fill="{p["orange"]}">{verb}</tspan> {escape(rest)}</text>')
    inner += f'<text x="36" y="266" font-size="13.5" fill="{p["dim"]}">{ABOUT}</text>'
    x = 36
    for chip in CHIPS:
        cw = 7 * len(chip) + 24
        inner += (f'<rect x="{x}" y="282" width="{cw:.0f}" height="24" rx="12" fill="{p["rail"]}" stroke="{p["line"]}"/>'
                  f'<text x="{x + cw / 2:.1f}" y="298" text-anchor="middle" font-size="11.5" fill="{p["fg"]}">{chip}</text>')
        x += cw + 8
    inner += (f'<circle class="spin" cx="{cx}" cy="{cy}" r="{r + 16}" fill="none" stroke="{p["blue"]}" '
              f'stroke-width="1.5" stroke-dasharray="2 7" opacity="0.7"/>'
              f'<g class="orbit" style="transform-origin:{cx}px {cy}px"><circle cx="{cx}" cy="{cy - r - 16}" r="5" fill="{p["orange"]}"/></g>')
    if avatar:
        inner += (f'<clipPath id="face"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                  f'<image href="{avatar}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#face)"/>'
                  f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["line"]}" stroke-width="2"/>')
    inner += (f'<g class="float"><path d="M{w - 46} 88 v14 M{w - 53} 95 h14" stroke="{p["orange"]}" '
              f'stroke-width="2" stroke-linecap="round"/></g>')
    return card(w, h, p, f"Dhananjay Aggarwal, full stack developer from Bangalore. {' '.join(LINES)}", inner,
                glow=(cx, cy, 260))


def motif(kind, theme, p, logo):
    out = ""
    if kind == "system":
        out += (f'<path class="flow" d="M330 86 L296 124 M330 86 L366 124 M313 134 H349" fill="none" '
                f'stroke="{p["blue"]}" stroke-width="1.6"/>')
        if logo:
            out += (f'<clipPath id="logo"><rect x="312" y="52" width="36" height="36" rx="9"/></clipPath>'
                    f'<image href="{logo}" x="312" y="52" width="36" height="36" clip-path="url(#logo)"/>'
                    f'<rect x="312" y="52" width="36" height="36" rx="9" fill="none" stroke="{p["line"]}"/>')
        for x, label in ((278, "API"), (348, "DB")):
            out += (f'<rect x="{x}" y="124" width="36" height="22" rx="6" fill="{p["rail"]}" stroke="{p["line"]}"/>'
                    f'<text x="{x + 18}" y="139" text-anchor="middle" font-size="10" font-weight="600" fill="{p["fg"]}">{label}</text>')
    elif kind == "matrix":
        heights = [3, 5, 6, 4, 6, 5, 2]
        for col, top in enumerate(heights):
            for row in range(6):
                lit = row >= 6 - top
                delay = (col * 0.17 + (5 - row) * 0.11) % 1.4
                cls = 'class="eq" ' if lit else ""
                out += (f'<circle {cls}style="animation-delay:{delay:.2f}s" '
                        f'cx="{290 + col * 13}" cy="{70 + row * 13}" r="3.6" '
                        f'fill="{NOTHING_RED if lit else p["rail"]}"/>')
    elif kind == "swatches":
        colors = ["#1DB954", "#635BFF", "#FF5A5F", "#F24E1E", p["fg"]]
        for i, color in enumerate(colors):
            angle = (i - 2) * 9
            out += (f'<g class="fan" style="--a:{angle}deg;transform-origin:325px 150px">'
                    f'<rect x="303" y="64" width="44" height="78" rx="8" fill="{color}" stroke="{p["card"]}" stroke-width="2"/></g>')
    elif kind == "terminal":
        out += (f'<rect x="270" y="52" width="122" height="96" rx="9" fill="{p["rail"]}" stroke="{p["line"]}"/>'
                + "".join(f'<circle cx="{282 + i * 9}" cy="63" r="2.6" fill="{c}"/>'
                          for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")))
                + f'<text x="280" y="86" font-size="10.5" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
                  f'fill="{p["fg"]}">$ diskwhy<tspan class="blink" fill="{p["blue"]}">▍</tspan></text>')
        for i, (share, color) in enumerate(((0.92, p["orange"]), (0.64, p["blue"]), (0.38, p["dim"]))):
            y = 98 + i * 14
            out += (f'<rect x="280" y="{y}" width="100" height="7" rx="3.5" fill="{p["card"]}"/>'
                    f'<rect class="fill" style="animation-delay:{i * 0.25}s" x="280" y="{y}" width="{100 * share:.0f}" '
                    f'height="7" rx="3.5" fill="{color}"/>')
    return out


def project(theme, p, proj, logo):
    w, h = HALF, 172
    inner = (f'<rect x="22" y="20" width="{8 * len(proj["verb"]) + 30}" height="22" rx="11" fill="{p["rail"]}" stroke="{p["line"]}"/>'
             f'<circle class="ping" cx="34" cy="31" r="3.5" fill="{GREEN[theme]}"/><circle cx="34" cy="31" r="3.5" fill="{GREEN[theme]}"/>'
             f'<text x="44" y="35" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="{p["fg"]}">{proj["verb"].upper()}</text>')
    inner += arrow(p, w - 30, 31)
    inner += f'<text x="22" y="76" font-size="21" font-weight="700" letter-spacing="-0.4" fill="{p["fg"]}">{escape(proj["title"])}</text>'
    for i, line in enumerate(proj["desc"]):
        inner += f'<text x="22" y="{100 + i * 18}" font-size="12.5" fill="{p["dim"]}">{escape(line)}</text>'
    inner += f'<text x="22" y="{h - 20}" font-size="11.5" font-weight="600" fill="{p["blue"]}">{escape(proj["stack"])}</text>'
    # keep the motif clear of the text column
    inner += f'<g transform="translate(6 6)">{motif(proj["motif"], theme, p, logo)}</g>' if proj["motif"] not in ("system", "swatches") \
        else motif(proj["motif"], theme, p, logo)
    alt = f'{proj["verb"]} {proj["title"]}: {" ".join(proj["desc"])} Built with {proj["stack"].replace(" · ", ", ")}.'
    return card(w, h, p, alt, inner)


def social(theme, p, s, path):
    w, h = HALF, 92
    color = s["color"]
    inner = (f'<rect x="22" y="22" width="48" height="48" rx="12" fill="{p["rail"]}" stroke="{p["line"]}"/>'
             f'<g transform="translate(34 34)"><path d="{path}" fill="{color}"/></g>'
             f'<text x="86" y="44" font-size="17" font-weight="700" fill="{p["fg"]}">{s["title"]}</text>'
             f'<text x="86" y="66" font-size="12.5" fill="{p["dim"]}">{escape(s["sub"])}</text>')
    inner += arrow(p, w - 34, h / 2)
    return card(w, h, p, f'{s["title"]}: {s["sub"]}', inner)


def write(name, theme, svg):
    with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as f:
        f.write(svg)


def main():
    avatar = avatar_uri(USER, size=400)
    logo = avatar_uri("IntervueClub", size=96)
    paths = {s["icon"]: simple_icon(s["icon"]) for s in SOCIALS}
    for theme, p in PALETTES.items():
        write("hero", theme, hero(theme, p, avatar))
        for proj in PROJECTS:
            write(f"project-{proj['slug']}", theme, project(theme, p, proj, logo))
        for s in SOCIALS:
            write(f"social-{s['slug']}", theme, social(theme, p, s, paths[s["icon"]]))
    print(f"hero, {len(PROJECTS)} projects, {len(SOCIALS)} socials")


if __name__ == "__main__":
    main()
