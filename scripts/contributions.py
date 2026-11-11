#!/usr/bin/env python3
"""Render contribution cards for the profile README from GitHub's API.

Counts every merged PR the user authored into an organization's repos,
private ones included (needs a classic token with `repo` + `read:org` in GH_TOKEN). Writes
assets/<card>-{dark,light}.svg and refreshes the "merged into" logo row in
README.md. Standard library only.
"""
import base64
import datetime as dt
import json
import math
import os
import re
import urllib.request
from collections import Counter, defaultdict
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "dhananjay6561")
TOKEN = os.environ.get("GH_TOKEN", "")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "assets")
README = os.path.join(ROOT, "README.md")

PALETTES = {
    "dark": dict(card="#0d1117", line="#30363d", fg="#e6edf3", dim="#8b949e",
                 blue="#58a6ff", orange="#ffa657", rail="#161b22"),
    "light": dict(card="#ffffff", line="#d0d7de", fg="#1f2328", dim="#59636e",
                  blue="#0969da", orange="#bc4c00", rail="#eaeef2"),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
WIDE, HALF = 840, 412

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      url mergedAt
      repository {
        nameWithOwner isPrivate stargazerCount
        owner { __typename login }
        primaryLanguage { name color }
      }
    } }
  }
}"""


def graphql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise SystemExit(payload["errors"])
    return payload["data"]


def fetch_prs():
    # search caps at 1000 hits per query, so walk it one year at a time
    found = {}
    for year in range(2015, dt.date.today().year + 1):
        q = f"is:pr is:merged author:{USER} created:{year}-01-01..{year}-12-31"
        cursor = None
        while True:
            page = graphql(QUERY, q=q, cursor=cursor)["search"]
            for pr in page["nodes"]:
                # personal accounts are not orgs, so their repos are left out
                if pr and pr["repository"]["owner"]["__typename"] == "Organization":
                    found[pr["url"]] = pr
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
    return list(found.values())


def avatar_uri(login):
    # GitHub's image proxy blocks remote images inside SVGs, so inline them
    try:
        req = urllib.request.Request(f"https://github.com/{login}.png?size=48",
                                     headers={"User-Agent": USER})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return "data:image/png;base64," + base64.b64encode(resp.read()).decode()
    except OSError:
        return None


def short(n):
    for size, suffix in ((1_000_000, "M"), (1_000, "k")):
        if n >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def frame(w, h, p, title, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f'<style>text{{font-family:{SANS}}}</style>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{p["card"]}" stroke="{p["line"]}"/>'
            f'{inner}</svg>')


def heading(p, text, right=None, w=WIDE):
    out = f'<text x="22" y="34" font-size="15" font-weight="600" fill="{p["fg"]}">{escape(text)}</text>'
    if right:
        out += f'<text x="{w - 22}" y="34" text-anchor="end" font-size="12" fill="{p["dim"]}">{escape(right)}</text>'
    return out


def summary_card(p, tiles):
    h = 112
    col = (WIDE - 44) / len(tiles)
    inner = ""
    for i, (value, label, tone) in enumerate(tiles):
        left = 22 + i * col
        if i:
            inner += f'<line x1="{left:.1f}" y1="28" x2="{left:.1f}" y2="{h - 28}" stroke="{p["line"]}"/>'
        mid = left + col / 2
        inner += (f'<text x="{mid:.1f}" y="60" text-anchor="middle" font-size="30" font-weight="700" '
                  f'fill="{p[tone]}">{value}</text>'
                  f'<text x="{mid:.1f}" y="86" text-anchor="middle" font-size="12.5" fill="{p["dim"]}">'
                  f'{escape(label)}</text>')
    return frame(WIDE, h, p, "Contribution summary", inner)


def orgs_card(p, orgs, avatars, h):
    row = 30
    peak = orgs[0][1]
    inner = heading(p, "Top orgs by merged PRs", w=HALF)
    for i, (login, n) in enumerate(orgs):
        y = 54 + i * row
        if avatars.get(login):
            inner += (f'<clipPath id="a{i}"><rect x="22" y="{y}" width="20" height="20" rx="5"/></clipPath>'
                      f'<image href="{avatars[login]}" x="22" y="{y}" width="20" height="20" clip-path="url(#a{i})"/>')
        inner += f'<text x="50" y="{y + 15}" font-size="13" fill="{p["fg"]}">{escape(login if len(login) <= 17 else login[:16] + '…')}</text>'
        inner += f'<rect x="180" y="{y + 5}" width="170" height="10" rx="5" fill="{p["rail"]}"/>'
        inner += f'<rect x="180" y="{y + 5}" width="{max(6, 170 * n / peak):.1f}" height="10" rx="5" fill="{p["blue"]}"/>'
        inner += (f'<text x="{HALF - 22}" y="{y + 15}" text-anchor="end" font-size="13" font-weight="600" '
                  f'fill="{p["fg"]}">{n}</text>')
    return frame(HALF, h, p, "Merged PRs by org", inner)


def languages_card(p, langs, h):
    total = sum(n for _, n, _ in langs)
    cx, cy, r = 108, 54 + (h - 54) / 2 - 4, 62
    inner = heading(p, "Merged PRs by language", w=HALF)
    start = -math.pi / 2
    for _, n, color in langs:
        end = start + 2 * math.pi * n / total
        gap = 0.014 if len(langs) > 1 else 0.0001
        x0, y0 = cx + r * math.cos(start), cy + r * math.sin(start)
        x1, y1 = cx + r * math.cos(end - gap), cy + r * math.sin(end - gap)
        big = 1 if end - start > math.pi else 0
        inner += (f'<path d="M{x0:.2f},{y0:.2f} A{r},{r} 0 {big} 1 {x1:.2f},{y1:.2f}" fill="none" '
                  f'stroke="{color}" stroke-width="20"/>')
        start = end
    inner += (f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" font-size="24" font-weight="700" fill="{p["fg"]}">{total}</text>'
              f'<text x="{cx}" y="{cy + 21}" text-anchor="middle" font-size="11" fill="{p["dim"]}">merged</text>')
    top = cy - len(langs) * 24 / 2 + 10
    for i, (name, n, color) in enumerate(langs):
        y = top + i * 24
        inner += (f'<rect x="212" y="{y - 9}" width="10" height="10" rx="3" fill="{color}"/>'
                  f'<text x="230" y="{y}" font-size="13" fill="{p["fg"]}">{escape(name)}</text>'
                  f'<text x="{HALF - 22}" y="{y}" text-anchor="end" font-size="13" fill="{p["dim"]}">'
                  f'{100 * n / total:.0f}%</text>')
    return frame(HALF, h, p, "Merged PRs by language", inner)


def monthly_card(p, months):
    h = 200
    peak = max(n for _, n in months) or 1
    inner = heading(p, "Merged PRs per month", "last 12 months")
    slot = (WIDE - 44) / len(months)
    floor, tallest = h - 34, h - 102
    for i, (label, n) in enumerate(months):
        bar = max(3, tallest * n / peak)
        x = 22 + i * slot + slot * 0.2
        mid = x + slot * 0.3
        inner += (f'<rect x="{x:.1f}" y="{floor - bar:.1f}" width="{slot * 0.6:.1f}" height="{bar:.1f}" rx="5" '
                  f'fill="{p["blue"]}" opacity="{0.4 + 0.6 * n / peak:.2f}"/>'
                  f'<text x="{mid:.1f}" y="{floor - bar - 7:.1f}" text-anchor="middle" font-size="12" '
                  f'font-weight="600" fill="{p["fg"]}">{n}</text>'
                  f'<text x="{mid:.1f}" y="{h - 14}" text-anchor="middle" font-size="12" fill="{p["dim"]}">{label}</text>')
    return frame(WIDE, h, p, "Merged PRs per month", inner)


def logo_row(prs):
    # public repos only: a link into a private repo would 404 for visitors
    counts = Counter(pr["repository"]["owner"]["login"] for pr in prs
                     if not pr["repository"]["isPrivate"])
    links = []
    for org, _ in counts.most_common(14):
        url = f"https://github.com/search?q=is%3Apr+is%3Amerged+author%3A{USER}+org%3A{org}&type=pullrequests"
        links.append(f'<a href="{url}"><img src="https://github.com/{org}.png?size=80" width="40" '
                     f'alt="{org}" title="{org}"/></a>')
    return " ".join(links)


def update_readme(row):
    with open(README) as f:
        text = f.read()
    fresh = re.sub(r"(<!--MERGED:START-->\n).*?(<!--MERGED:END-->)",
                   lambda m: m.group(1) + row + "\n" + m.group(2), text, flags=re.S)
    if fresh != text:
        with open(README, "w") as f:
            f.write(fresh)


def main():
    prs = fetch_prs()
    repos = {pr["repository"]["nameWithOwner"]: pr["repository"] for pr in prs}
    orgs = Counter(pr["repository"]["owner"]["login"] for pr in prs)
    stars = sum(r["stargazerCount"] for r in repos.values())

    lang_count, lang_color = Counter(), {}
    for pr in prs:
        lang = pr["repository"]["primaryLanguage"]
        if lang:
            lang_count[lang["name"]] += 1
            lang_color[lang["name"]] = lang["color"] or "#8b949e"
    top = lang_count.most_common(6)
    rest = len(prs) - sum(n for _, n in top)
    langs = [(name, n, lang_color[name]) for name, n in top] + ([("Other", rest, "#8b949e")] if rest else [])

    per_month = defaultdict(int)
    for pr in prs:
        per_month[pr["mergedAt"][:7]] += 1
    today = dt.date.today()
    months = []
    for back in range(11, -1, -1):
        y, m = today.year, today.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        months.append((dt.date(y, m, 1).strftime("%b"), per_month[f"{y}-{m:02d}"]))
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
    recent = sum(1 for pr in prs if pr["mergedAt"] >= since)

    top_orgs = orgs.most_common(8)
    avatars = {login: avatar_uri(login) for login, _ in top_orgs}
    pair_h = 54 + 30 * len(top_orgs) + 12
    tiles = [(short(len(prs)), "PRs merged", "blue"), (short(len(repos)), "repositories", "fg"),
             (short(len(orgs)), "orgs", "fg"), (short(stars), "stars on those repos", "fg"),
             (str(recent), "merged in last 30 days", "orange")]

    os.makedirs(ASSETS, exist_ok=True)
    for theme, p in PALETTES.items():
        cards = {"summary": summary_card(p, tiles), "orgs": orgs_card(p, top_orgs, avatars, pair_h),
                 "languages": languages_card(p, langs, pair_h), "monthly": monthly_card(p, months)}
        for name, svg in cards.items():
            with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as f:
                f.write(svg)
    update_readme(logo_row(prs))
    print(f"{len(prs)} merged ({sum(r['isPrivate'] for r in repos.values())} private repos), "
          f"{len(repos)} repos, {len(orgs)} orgs, {stars} stars, {recent} in last 30 days")


if __name__ == "__main__":
    main()
