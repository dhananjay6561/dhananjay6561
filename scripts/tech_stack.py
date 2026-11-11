#!/usr/bin/env python3
"""Render the tech stack card, grouped by area, for both themes.

Icons come from skill-icons (MIT) and, where it has none, Simple Icons (CC0),
drawn into the same tile. They are inlined at build time, so the README never
calls out to either. Edit STACK and rerun; no token needed.
"""
import base64
import os
import re
import urllib.request
from xml.sax.saxutils import escape

from contributions import ASSETS, PALETTES, WIDE, frame, heading

# picked from what the repos actually import, build and deploy with
STACK = [
    ("Languages", ["ts", "js", "py", "go", "kotlin", "java"]),
    ("Frontend", ["react", "nextjs", "vite", "tailwind", "threejs"]),
    ("Backend", ["nodejs", "express", "fastapi", "flask"]),
    ("AI & ML", ["si:langchain", "si:openai", "sklearn"]),
    ("Databases", ["postgres", "supabase", "redis", "prisma"]),
    ("DevOps & cloud", ["docker", "kubernetes", "githubactions", "vercel"]),
    ("Testing", ["jest", "vitest", "si:pytest", "si:playwright"]),
    ("Mobile", ["androidstudio", "si:jetpackcompose"]),
]
# brand colour per Simple Icons slug; None follows the theme's text colour
SIMPLE_COLORS = {"langchain": None, "openai": None, "pytest": "#0A9EDC",
                 "playwright": "#2EAD33", "jetpackcompose": "#4285F4"}
TILE_BG = {"dark": "#242938", "light": "#F4F2ED"}  # skill-icons' own tile colours
NAMES = {"ts": "TypeScript", "js": "JavaScript", "py": "Python", "go": "Go", "kotlin": "Kotlin",
         "java": "Java", "react": "React", "nextjs": "Next.js", "vite": "Vite", "tailwind": "Tailwind CSS",
         "threejs": "Three.js", "nodejs": "Node.js", "express": "Express", "fastapi": "FastAPI",
         "flask": "Flask", "langchain": "LangChain", "openai": "OpenAI", "sklearn": "scikit-learn",
         "postgres": "PostgreSQL", "supabase": "Supabase", "redis": "Redis", "prisma": "Prisma",
         "docker": "Docker", "kubernetes": "Kubernetes", "githubactions": "GitHub Actions",
         "vercel": "Vercel", "jest": "Jest", "vitest": "Vitest", "pytest": "pytest",
         "playwright": "Playwright", "androidstudio": "Android Studio", "jetpackcompose": "Jetpack Compose"}
ICON, GAP = 44, 10


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def skill_icons(theme):
    # one request for the whole set: the service is slow per call
    keys = [k for _, ks in STACK for k in ks if not k.startswith("si:")]
    combined = get(f"https://skillicons.dev/icons?i={','.join(keys)}&theme={theme}&perline=50")
    icons = re.findall(r'<g transform="translate\([^)]*\)">\s*(<svg.*?</svg>)\s*</g>', combined, re.S)
    if len(icons) != len(keys):
        raise SystemExit(f"expected {len(keys)} skill-icons, got {len(icons)}")
    return dict(zip(keys, icons))


def tile(key, theme, p, skills):
    if key.startswith("si:"):
        slug = key[3:]
        path = re.search(r'<path d="([^"]+)"', get(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg")).group(1)
        color = SIMPLE_COLORS[slug] or p["fg"]
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
               f'<rect width="256" height="256" rx="60" fill="{TILE_BG[theme]}"/>'
               f'<g transform="translate(56 56) scale(6)"><path d="{path}" fill="{color}"/></g></svg>')
    else:
        svg = skills[key]
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def stack_card(theme, p):
    skills = skill_icons(theme)
    col_w = (WIDE - 44) / 2
    block_h = 96
    rows = (len(STACK) + 1) // 2
    h = 58 + rows * block_h
    inner = heading(p, "Tech stack", "from the repos I ship")
    for g, (label, keys) in enumerate(STACK):
        x0 = 22 + (g % 2) * col_w
        y0 = 58 + (g // 2) * block_h
        inner += f'<text x="{x0}" y="{y0 + 14}" font-size="12" font-weight="600" letter-spacing="0.4" fill="{p["dim"]}">{escape(label.upper())}</text>'
        for i, key in enumerate(keys):
            name = NAMES[key.removeprefix("si:")]
            inner += (f'<image href="{tile(key, theme, p, skills)}" x="{x0 + i * (ICON + GAP)}" y="{y0 + 26}" '
                      f'width="{ICON}" height="{ICON}"><title>{escape(name)}</title></image>')
    return frame(WIDE, h, p, "Tech stack: " + ", ".join(NAMES[k.removeprefix("si:")] for _, ks in STACK for k in ks), inner)


def main():
    for theme, p in PALETTES.items():
        with open(os.path.join(ASSETS, f"stack-{theme}.svg"), "w") as f:
            f.write(stack_card(theme, p))
    print(f"{sum(len(k) for _, k in STACK)} tools in {len(STACK)} groups")


if __name__ == "__main__":
    main()
