#!/usr/bin/env python3
"""Render the intro header card for both themes. Static: edit and rerun, no token needed."""
import os
from xml.sax.saxutils import escape

from contributions import ASSETS, PALETTES, USER, WIDE, avatar_uri, frame

NAME = "Dhananjay Aggarwal"
ROLE = "DevRel Engineer at Keploy  ·  Bangalore"
TAGLINE = ["I build developer tools and AI experiments,",
           "then turn them into demos developers actually want to watch."]
CHIPS = ["API testing", "AI agents", "Developer tools", "100 Days of AI"]


def header_card(p, avatar):
    h = 224
    inner = (f'<text x="32" y="66" font-size="34" font-weight="700" fill="{p["fg"]}">{escape(NAME)}</text>'
             f'<text x="32" y="98" font-size="16" font-weight="600" fill="{p["blue"]}" xml:space="preserve">{escape(ROLE)}</text>')
    for i, line in enumerate(TAGLINE):
        inner += f'<text x="32" y="{128 + i * 21}" font-size="14" fill="{p["dim"]}">{escape(line)}</text>'
    x = 32
    for chip in CHIPS:
        w = 7.2 * len(chip) + 26
        inner += (f'<rect x="{x}" y="171" width="{w:.0f}" height="26" rx="13" fill="{p["rail"]}" stroke="{p["line"]}"/>'
                  f'<text x="{x + w / 2:.1f}" y="188" text-anchor="middle" font-size="12" fill="{p["fg"]}">{escape(chip)}</text>')
        x += w + 8
    if avatar:
        cx, cy, r = WIDE - 120, h / 2, 74
        inner += (f'<circle cx="{cx}" cy="{cy}" r="{r + 5}" fill="none" stroke="{p["blue"]}" stroke-width="2" opacity="0.6"/>'
                  f'<clipPath id="face"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                  f'<image href="{avatar}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#face)"/>')
    return frame(WIDE, h, p, f"{NAME}, {ROLE.replace('  ', ' ')}", inner)


def main():
    avatar = avatar_uri(USER, size=300)
    for theme, p in PALETTES.items():
        with open(os.path.join(ASSETS, f"header-{theme}.svg"), "w") as f:
            f.write(header_card(p, avatar))


if __name__ == "__main__":
    main()
