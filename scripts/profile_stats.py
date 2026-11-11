#!/usr/bin/env python3
"""Render the GitHub stats cards (calendar, lifetime totals, languages,
weekday rhythm) from GitHub's API, private contributions included.

Shares the drawing helpers and palettes with contributions.py. Writes
assets/<card>-{dark,light}.svg. Standard library only.
"""
import datetime as dt
import os
from collections import Counter
from xml.sax.saxutils import escape

from contributions import (ASSETS, HALF, PALETTES, USER, WIDE, frame, graphql,
                           heading, short, summary_card)

# blue ramp from empty to busiest, tuned per theme
HEAT = {
    "dark": ["#161b22", "#0c2d6b", "#1158c7", "#388bfd", "#79c0ff"],
    "light": ["#eaeef2", "#b6d4fe", "#6ea8fe", "#2f81f7", "#0550ae"],
}
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


def level(n, cuts):
    return 0 if n == 0 else 1 + sum(n > c for c in cuts)


def calendar_card(p, heat, calendar, current):
    weeks = calendar["weeks"]
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    cuts = [counts[len(counts) * q // 4] for q in (1, 2, 3)] if counts else [0, 0, 0]
    cell, step, left, top = 11, 14, 56, 74
    h = top + 7 * step + 44
    total = calendar["totalContributions"]
    streak = f"current streak · {current} day{'s' * (current != 1)}"
    inner = heading(p, f"{total:,} contributions in the last year", streak)

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        inner += (f'<text x="22" y="{top + row * step + 9}" font-size="11" fill="{p["dim"]}">{name}</text>')
    last_month = None
    for col, week in enumerate(weeks):
        x = left + col * step
        month = week["contributionDays"][0]["date"][:7]
        if month != last_month:
            if last_month is not None or week["contributionDays"][0]["date"][8:] <= "07":
                label = dt.date.fromisoformat(month + "-01").strftime("%b")
                inner += f'<text x="{x}" y="{top - 8}" font-size="11" fill="{p["dim"]}">{label}</text>'
        last_month = month
        for d in week["contributionDays"]:
            y = top + d["weekday"] * step
            n = d["contributionCount"]
            inner += (f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" '
                      f'fill="{heat[level(n, cuts)]}"><title>{n} on {d["date"]}</title></rect>')

    busiest = max((d for w in weeks for d in w["contributionDays"]), key=lambda d: d["contributionCount"])
    when = dt.date.fromisoformat(busiest["date"]).strftime("%b %-d")
    inner += (f'<text x="22" y="{h - 18}" font-size="12" fill="{p["dim"]}">Busiest day: '
              f'<tspan fill="{p["fg"]}" font-weight="600">{busiest["contributionCount"]}</tspan> on {when}</text>')
    lx = WIDE - 22 - 5 * step - 34
    inner += f'<text x="{lx - 6}" y="{h - 18}" text-anchor="end" font-size="11" fill="{p["dim"]}">Less</text>'
    for i, shade in enumerate(heat):
        inner += f'<rect x="{lx + i * step}" y="{h - 28}" width="{cell}" height="{cell}" rx="2.5" fill="{shade}"/>'
    inner += f'<text x="{lx + 5 * step + 3}" y="{h - 18}" font-size="11" fill="{p["dim"]}">More</text>'
    return frame(WIDE, h, p, "Contribution calendar", inner)


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
        cards = {"calendar": calendar_card(p, HEAT[theme], calendar, current),
                 "lifetime": summary_card(p, tiles),
                 "langs": languages_card(p, langs, pair_h),
                 "weekdays": weekday_card(p, calendar, pair_h)}
        for name, svg in cards.items():
            with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as f:
                f.write(svg)
    print(f"since {created[:10]}: {dict(totals)}, streak {current}/{longest}, langs {[n for n, _, _ in langs]}")


if __name__ == "__main__":
    main()
