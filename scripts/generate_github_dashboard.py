#!/usr/bin/env python3
"""Generate a self-contained SVG snapshot for the profile README."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import textwrap
from urllib.request import Request, urlopen


USERNAME = "07Rinat07"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "github-dashboard.svg"
API_ROOT = "https://api.github.com"


def github_api(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-dashboard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API_ROOT}{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def compact_number(value: int) -> str:
    if value < 1_000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return f"{value / 1_000_000:.1f}m".replace(".0m", "m")


def iso_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def truncate(value: str, length: int) -> str:
    clean = " ".join((value or "").split())
    if len(clean) <= length:
        return clean
    return clean[: length - 1].rstrip() + "…"


def language_color(language: str) -> str:
    return {
        "PHP": "#777BB4",
        "JavaScript": "#D6B700",
        "TypeScript": "#3178C6",
        "Python": "#3776AB",
        "HTML": "#E34F26",
        "CSS": "#1572B6",
        "Vue": "#42B883",
        "Kotlin": "#7F52FF",
        "Shell": "#4EAA25",
    }.get(language, "#6D28D9")


def render_dashboard(user: dict, repositories: list[dict]) -> str:
    now = datetime.now(timezone.utc)
    owned = [
        repo
        for repo in repositories
        if not repo["fork"] and not repo["archived"] and repo["name"] != USERNAME
    ]
    active_cutoff = now.timestamp() - 90 * 24 * 60 * 60
    active = [repo for repo in owned if iso_date(repo["pushed_at"]).timestamp() >= active_cutoff]
    language_counts = Counter(repo["language"] for repo in owned if repo["language"])
    top_languages = language_counts.most_common()
    language_total = sum(count for _, count in top_languages) or 1
    recent_limit = min(6, max(3, (len(top_languages) + 1) // 2))
    recent = sorted(owned, key=lambda repo: repo["pushed_at"], reverse=True)[:recent_limit]

    language_start = 392
    language_step = 52
    recent_start = 384
    recent_step = 94
    language_bottom = language_start + max(0, len(top_languages) - 1) * language_step + 30
    recent_bottom = recent_start + max(0, len(recent) - 1) * recent_step + 72
    panel_y = 290
    panel_bottom = max(language_bottom, recent_bottom, 648) + 24
    panel_height = panel_bottom - panel_y
    svg_height = panel_bottom + 48
    footer_y = svg_height - 16

    joined_at = iso_date(user["created_at"])
    journey_years = now.year - joined_at.year - ((now.month, now.day) < (joined_at.month, joined_at.day))
    metrics = [
        ("PUBLIC PROJECTS", compact_number(len(owned)), "Owned and maintained repositories", "#6D28D9"),
        ("ACTIVE · 90 DAYS", compact_number(len(active)), "Projects updated recently", "#7C3AED"),
        ("CORE LANGUAGES", compact_number(len(language_counts)), "Primary languages across projects", "#8B5CF6"),
        ("GITHUB JOURNEY", f"{journey_years}+ yrs", "Building in public since Apr 2022", "#A855F7"),
    ]

    metric_cards = []
    for index, (label, value, note, accent) in enumerate(metrics):
        x = 38 + index * 282
        metric_cards.append(
            f"""
            <g transform="translate({x} 112)">
              <rect width="262" height="154" rx="20" fill="#FFFFFF" stroke="#E4E4E7"/>
              <rect x="0" y="0" width="6" height="154" rx="3" fill="{accent}"/>
              <text x="24" y="38" class="eyebrow">{label}</text>
              <text x="24" y="92" class="metric">{value}</text>
              <text x="24" y="130" class="note">{note}</text>
            </g>"""
        )

    language_rows = []
    for index, (language, count) in enumerate(top_languages):
        y = language_start + index * language_step
        share = count / language_total
        width = max(24, round(345 * share))
        color = language_color(language)
        language_rows.append(
            f"""
            <text x="66" y="{y}" class="row-title">{escape(language)}</text>
            <text x="485" y="{y}" text-anchor="end" class="row-meta">{count} projects</text>
            <rect x="66" y="{y + 10}" width="419" height="8" rx="4" fill="#F0F0F2"/>
            <rect x="66" y="{y + 10}" width="{width}" height="8" rx="4" fill="{color}"/>"""
        )

    recent_rows = []
    for index, repo in enumerate(recent):
        y = recent_start + index * recent_step
        language = repo["language"] or "Mixed stack"
        updated = iso_date(repo["pushed_at"]).strftime("%b %d, %Y")
        description = truncate(repo.get("description") or "Actively maintained public project", 48)
        divider = '<line x1="650" y1="80" x2="1122" y2="80" stroke="#ECECEF"/>' if index < len(recent) - 1 else ""
        recent_rows.append(
            f"""
            <g transform="translate(0 {y})">
              <circle cx="666" cy="7" r="7" fill="{language_color(language)}"/>
              <text x="684" y="12" class="repo-title">{escape(repo["name"])}</text>
              <text x="1118" y="12" text-anchor="end" class="row-meta">{escape(language)} · {updated}</text>
              <text x="666" y="38" class="repo-description">{escape(description)}</text>
              {divider}
            </g>"""
        )

    generated = now.strftime("%b %d, %Y · %H:%M UTC")
    joined = iso_date(user["created_at"]).strftime("%b %Y")

    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{svg_height}" viewBox="0 0 1200 {svg_height}" role="img" aria-labelledby="title description">
          <title id="title">{USERNAME} GitHub engineering snapshot</title>
          <desc id="description">Current repository, community, language and recently active project metrics.</desc>
          <defs>
            <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="8" stdDeviation="16" flood-color="#18181B" flood-opacity="0.06"/>
            </filter>
            <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#6D28D9"/>
              <stop offset="0.52" stop-color="#9333EA"/>
              <stop offset="1" stop-color="#C026D3"/>
            </linearGradient>
            <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="#D4D4D8" opacity="0.45"/>
            </pattern>
            <style>
              text {{ font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #18181B; }}
              .title {{ font-size: 31px; font-weight: 750; letter-spacing: -0.7px; }}
              .subtitle {{ font-size: 15px; fill: #71717A; }}
              .eyebrow {{ font-size: 13px; font-weight: 720; letter-spacing: 1.15px; fill: #71717A; }}
              .metric {{ font-size: 42px; font-weight: 780; letter-spacing: -1.1px; }}
              .note {{ font-size: 14px; fill: #71717A; }}
              .section-title {{ font-size: 17px; font-weight: 760; letter-spacing: 0.35px; }}
              .section-note {{ font-size: 14px; fill: #71717A; }}
              .row-title {{ font-size: 15px; font-weight: 700; }}
              .row-meta {{ font-size: 13px; fill: #71717A; }}
              .repo-title {{ font-size: 16px; font-weight: 740; }}
              .repo-description {{ font-size: 14px; fill: #71717A; }}
              .footer {{ font-size: 12px; fill: #A1A1AA; }}
            </style>
          </defs>

          <rect width="1200" height="{svg_height}" rx="28" fill="#F7F7F8"/>
          <rect width="1200" height="{svg_height}" rx="28" fill="url(#dots)"/>
          <rect x="0" y="0" width="1200" height="6" rx="3" fill="url(#accent)"/>

          <g transform="translate(40 38)">
            <rect width="42" height="42" rx="13" fill="#18181B"/>
            <text x="21" y="27" text-anchor="middle" font-size="13" font-weight="800" style="fill:#FFFFFF">RS</text>
            <text x="58" y="20" class="title">Engineering snapshot</text>
            <text x="58" y="41" class="subtitle">Live signals from owned public repositories · profile active since {joined}</text>
          </g>
          <g transform="translate(964 44)">
            <rect width="196" height="34" rx="17" fill="#FFFFFF" stroke="#E4E4E7"/>
            <circle cx="20" cy="17" r="5" fill="#22C55E"/>
            <text x="35" y="22" font-size="14" font-weight="700">github.com/{USERNAME}</text>
          </g>

          <g filter="url(#shadow)">{''.join(metric_cards)}</g>

          <g filter="url(#shadow)">
            <rect x="38" y="{panel_y}" width="488" height="{panel_height}" rx="22" fill="#FFFFFF" stroke="#E4E4E7"/>
            <rect x="546" y="{panel_y}" width="616" height="{panel_height}" rx="22" fill="#FFFFFF" stroke="#E4E4E7"/>
          </g>

          <text x="66" y="334" class="section-title">TECHNOLOGY FOOTPRINT</text>
          <text x="66" y="359" class="section-note">Primary languages across owned repositories</text>
          {''.join(language_rows)}

          <text x="574" y="334" class="section-title">RECENTLY ACTIVE</text>
          <text x="574" y="359" class="section-note">Latest public projects by push activity</text>
          {''.join(recent_rows)}

          <text x="40" y="{footer_y}" class="footer">Generated from the GitHub API · {escape(generated)}</text>
          <text x="1160" y="{footer_y}" text-anchor="end" class="footer">Auto-refreshed daily</text>
        </svg>
        """
    )


def main() -> None:
    user = github_api(f"/users/{USERNAME}")
    repositories = github_api(
        f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=pushed&direction=desc"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_dashboard(user, repositories), encoding="utf-8")
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
