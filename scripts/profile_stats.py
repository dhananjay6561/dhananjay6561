#!/usr/bin/env python3
"""Render the GitHub stats cards (lifetime totals, contributions per month,
languages, weekday rhythm) from GitHub's API, private contributions included.

Shares the drawing helpers and palettes with contributions.py. Writes
assets/<card>-{dark,light}.svg. Standard library only.
"""
import datetime as dt
import math
import os
from collections import Counter
from xml.sax.saxutils import escape

from contributions import (ASSETS, HALF, PALETTES, USER, WIDE, frame, graphql,
                           heading, short, summary_card)

# notebooks and markup inflate byte counts without saying much about the code
HIDDEN_LANGS = {"Jupyter Notebook", "HTML", "CSS", "SCSS"}

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions totalPullRequestContributions
      totalIssueContributions totalPullRequestReviewContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""

PROFILE_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    contributionsCollection {
      contributionYears
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount weekday } } }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
  }
}"""


def fetch():
    first = graphql(PROFILE_QUERY, login=USER, cursor=None)["user"]
    profile = first["contributionsCollection"]

    lang_bytes, lang_color, page = Counter(), {}, first["repositories"]
    while True:
        for repo in page["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name not in HIDDEN_LANGS:
                    lang_bytes[name] += edge["size"]
                    lang_color[name] = edge["node"]["color"] or "#8b949e"
        if not page["pageInfo"]["hasNextPage"]:
            break
        page = graphql(PROFILE_QUERY, login=USER, cursor=page["pageInfo"]["endCursor"])["user"]["repositories"]

    totals, days = Counter(), {}
    for year in profile["contributionYears"]:
        c = graphql(YEAR_QUERY, login=USER, **{"from": f"{year}-01-01T00:00:00Z",
                                               "to": f"{year}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        totals["contributions"] += c["contributionCalendar"]["totalContributions"]
        totals["commits"] += c["totalCommitContributions"]
        totals["prs"] += c["totalPullRequestContributions"]
        totals["issues"] += c["totalIssueContributions"]
        totals["reviews"] += c["totalPullRequestReviewContributions"]
        for week in c["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    return first["createdAt"], profile["contributionCalendar"], totals, days, lang_bytes, lang_color


def streaks(days):
    today = dt.date.today()
    longest = run = 0
    for date in sorted(days):
        if dt.date.fromisoformat(date) > today:
            break
        run = run + 1 if days[date] else 0
        longest = max(longest, run)
    # today still counts as part of the streak until it ends with nothing
    day = today if days.get(today.isoformat()) else today - dt.timedelta(days=1)
    current = 0
    while days.get(day.isoformat()):
        current += 1
        day -= dt.timedelta(days=1)
    return current, longest


def per_month(days):
    today = dt.date.today()
    counts = Counter()
    for date, n in days.items():
        if date <= today.isoformat():
            counts[date[:7]] += n
    first = min((m for m, n in counts.items() if n), default=today.strftime("%Y-%m"))
    y, m = map(int, first.split("-"))
    months = []
    while (y, m) <= (today.year, today.month):
        months.append((dt.date(y, m, 1), counts[f"{y}-{m:02d}"]))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def nice_step(peak):
    raw = max(peak, 1) / 4
    mag = 10 ** (len(str(int(raw))) - 1)
    return next(k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw)


def monthly_card(p, months, current):
    h = 300
    x0, x1, top, floor = 62, WIDE - 26, 72, h - 46
    peak_n = max(n for _, n in months) or 1
    step = nice_step(peak_n)
    ceiling = step * math.ceil(peak_n / step)
    span = max(len(months) - 1, 1)
    px = lambda i: x0 + (x1 - x0) * i / span
    py = lambda n: floor - (floor - top) * n / ceiling

    streak = f"current streak · {current} day{'s' * (current != 1)}"
    inner = heading(p, "Contributions per month", streak)
    inner += (f'<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
              f'<stop offset="0" stop-color="{p["blue"]}" stop-opacity="0.38"/>'
              f'<stop offset="1" stop-color="{p["blue"]}" stop-opacity="0.02"/></linearGradient></defs>')
    tick = 0
    while tick <= ceiling:
        y = py(tick)
        inner += (f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{p["line"]}" '
                  f'stroke-dasharray="{"0" if tick == 0 else "3 4"}"/>'
                  f'<text x="{x0 - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{p["dim"]}">{short(int(tick))}</text>')
        tick += step

    points = " ".join(f"{px(i):.1f},{py(n):.1f}" for i, (_, n) in enumerate(months))
    inner += f'<polygon points="{x0},{floor} {points} {px(len(months) - 1):.1f},{floor}" fill="url(#fill)"/>'
    inner += (f'<polyline points="{points}" fill="none" stroke="{p["blue"]}" stroke-width="2.5" '
              f'stroke-linejoin="round" stroke-linecap="round"/>')

    best = max(range(len(months)), key=lambda i: months[i][1])
    for i, (month, n) in enumerate(months):
        x, y = px(i), py(n)
        hot = i == best
        inner += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if hot else 3}" fill="{p["orange"] if hot else p["blue"]}" '
                  f'stroke="{p["card"]}" stroke-width="{2 if hot else 1.5}"><title>{n:,} in {month:%b %Y}</title></circle>')
        if month.month == 1:
            inner += f'<text x="{x:.1f}" y="{h - 20}" text-anchor="middle" font-size="12" font-weight="600" fill="{p["fg"]}">{month.year}</text>'
        elif month.month in (4, 7, 10):
            inner += f'<text x="{x:.1f}" y="{h - 20}" text-anchor="middle" font-size="11" fill="{p["dim"]}">{month:%b}</text>'

    bx, by = px(best), py(months[best][1])
    label = f"{months[best][1]:,} in {months[best][0]:%b %Y}"
    anchor = "end" if bx > WIDE - 140 else "start" if bx < 140 else "middle"
    inner += (f'<text x="{bx:.1f}" y="{by - 12:.1f}" text-anchor="{anchor}" font-size="12" font-weight="600" '
              f'fill="{p["orange"]}">{label}</text>')
    return frame(WIDE, h, p, "Contributions per month", inner)


def languages_card(p, langs, h):
    total = sum(n for _, n, _ in langs)
    inner = heading(p, "Languages I write", w=HALF)
    x, bar_w = 22, HALF - 44
    inner += f'<clipPath id="bar"><rect x="22" y="54" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">'
    for _, n, color in langs:
        w = bar_w * n / total
        inner += f'<rect x="{x:.2f}" y="54" width="{w + 0.5:.2f}" height="10" fill="{color}"/>'
        x += w
    inner += "</g>"
    for i, (name, n, color) in enumerate(langs):
        y = 98 + i * 26
        inner += (f'<circle cx="27" cy="{y - 4}" r="5" fill="{color}"/>'
                  f'<text x="40" y="{y}" font-size="13" fill="{p["fg"]}">{escape(name)}</text>'
                  f'<text x="{HALF - 22}" y="{y}" text-anchor="end" font-size="13" fill="{p["dim"]}">'
                  f'{100 * n / total:.1f}%</text>')
    return frame(HALF, h, p, "Languages by code in my repos", inner)


def weekday_card(p, calendar, h):
    per_day = [0] * 7
    for week in calendar["weeks"]:
        for d in week["contributionDays"]:
            per_day[d["weekday"]] += d["contributionCount"]
    order = [1, 2, 3, 4, 5, 6, 0]  # Monday first
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    peak = max(per_day) or 1
    top_day = per_day.index(peak)
    inner = heading(p, "Weekly rhythm", "last year", w=HALF)
    slot = (HALF - 44) / 7
    floor, tallest = h - 34, h - 106
    for i, wd in enumerate(order):
        n = per_day[wd]
        bar = max(3, tallest * n / peak)
        x = 22 + i * slot + slot * 0.18
        mid = x + slot * 0.32
        fill = p["orange"] if wd == top_day else p["blue"]
        inner += (f'<rect x="{x:.1f}" y="{floor - bar:.1f}" width="{slot * 0.64:.1f}" height="{bar:.1f}" rx="5" '
                  f'fill="{fill}" opacity="{1 if wd == top_day else 0.4 + 0.5 * n / peak:.2f}"/>'
                  f'<text x="{mid:.1f}" y="{floor - bar - 7:.1f}" text-anchor="middle" font-size="12" '
                  f'font-weight="600" fill="{p["fg"]}">{short(n)}</text>'
                  f'<text x="{mid:.1f}" y="{h - 14}" text-anchor="middle" font-size="12" '
                  f'fill="{p["fg"] if wd == top_day else p["dim"]}">{names[wd]}</text>')
    return frame(HALF, h, p, "Contributions by weekday", inner)


def main():
    created, calendar, totals, days, lang_bytes, lang_color = fetch()
    current, longest = streaks(days)

    top = lang_bytes.most_common(6)
    rest = sum(lang_bytes.values()) - sum(n for _, n in top)
    langs = [(name, n, lang_color[name]) for name, n in top] + ([("Other", rest, "#8b949e")] if rest else [])

    exact = lambda n: f"{n:,}" if n < 100_000 else short(n)
    tiles = [(exact(totals["contributions"]), "contributions", "blue"), (exact(totals["commits"]), "commits", "fg"),
             (exact(totals["prs"]), "pull requests", "fg"), (exact(totals["issues"]), "issues", "fg"),
             (exact(totals["reviews"]), "code reviews", "fg"), (str(longest), "day longest streak", "orange")]
    pair_h = 98 + 26 * len(langs) + 4

    for theme, p in PALETTES.items():
        cards = {"monthly-contribs": monthly_card(p, per_month(days), current),
                 "lifetime": summary_card(p, tiles),
                 "langs": languages_card(p, langs, pair_h),
                 "weekdays": weekday_card(p, calendar, pair_h)}
        for name, svg in cards.items():
            with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as f:
                f.write(svg)
    print(f"since {created[:10]}: {dict(totals)}, streak {current}/{longest}, langs {[n for n, _, _ in langs]}")


if __name__ == "__main__":
    main()
