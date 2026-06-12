"""
generate_html.py
Reads scores.json (and participants.json) from GitHub, generates a fully
self-contained green-pitch leaderboard index.html, writes it locally and
uploads it to GitHub Pages via the GitHub API.
"""

import os
import requests
from dotenv import load_dotenv
from github_utils import read_json, write_html

load_dotenv()

# ---------------------------------------------------------------------------
# Country flag emoji map
# ---------------------------------------------------------------------------
FLAG = {
    "Qatar": "🇶🇦",
    "Uruguay": "🇺🇾",
    "Morocco": "🇲🇦",
    "Argentina": "🇦🇷",
    "Norway": "🇳🇴",
    "Iran": "🇮🇷",
    "Croatia": "🇭🇷",
    "Spain": "🇪🇸",
    "Belgium": "🇧🇪",
    "Ivory Coast": "🇨🇮",
    "Mexico": "🇲🇽",
    "Czechia": "🇨🇿",
    "Bosnia & Herz.": "🇧🇦",
    "Japan": "🇯🇵",
    "Panama": "🇵🇦",
    "Senegal": "🇸🇳",
    "DR Congo": "🇨🇩",
    "Canada": "🇨🇦",
    "Cape Verde": "🇨🇻",
    "Jordan": "🇯🇴",
    "USA": "🇺🇸",
    "South Africa": "🇿🇦",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Colombia": "🇨🇴",
    "Haiti": "🇭🇹",
    "Brazil": "🇧🇷",
    "Sweden": "🇸🇪",
    "France": "🇫🇷",
    "South Korea": "🇰🇷",
    "Ecuador": "🇪🇨",
    "New Zealand": "🇳🇿",
    "Saudi Arabia": "🇸🇦",
    "Netherlands": "🇳🇱",
    "Turkey": "🇹🇷",
    "Paraguay": "🇵🇾",
    "Iraq": "🇮🇶",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Egypt": "🇪🇬",
    "Australia": "🇦🇺",
    "Curaçao": "🇨🇼",
    "Ghana": "🇬🇭",
    "Austria": "🇦🇹",
    "Germany": "🇩🇪",
    "Tunisia": "🇹🇳",
    "Algeria": "🇩🇿",
    "Portugal": "🇵🇹",
    "Switzerland": "🇨🇭",
    "Uzbekistan": "🇺🇿",
}

MEDAL = ["🏆", "🥈", "🥉", "😅"]

# ---------------------------------------------------------------------------
# Event label builder
# ---------------------------------------------------------------------------
EVENT_LABELS = {
    "GROUP_STAGE_WIN": lambda opp: f"won in Group Stage vs {opp}",
    "GROUP_STAGE_DRAW": lambda opp: f"drew in Group Stage vs {opp}",
    "QUALIFY_TOP_2": lambda opp: "qualified from Group (Top 2)",
    "QUALIFY_BEST_THIRD": lambda opp: "qualified as Best 3rd Place",
    "LAST_32_WIN": lambda opp: f"won Round of 32 vs {opp}",
    "LAST_16_WIN": lambda opp: f"won Round of 16 vs {opp}",
    "QUARTER_FINALS_WIN": lambda opp: f"won Quarter-Final vs {opp}",
    "SEMI_FINALS_WIN": lambda opp: f"won Semi-Final vs {opp}",
    "THIRD_PLACE_WIN": lambda opp: f"won 3rd Place Play-off vs {opp}",
    "FINAL_WIN": lambda opp: f"WON THE WORLD CUP! 🏆 vs {opp}",
}


def event_label(event_key, opponent):
    fn = EVENT_LABELS.get(event_key)
    if fn:
        return fn(opponent or "")
    return event_key


def flag(country):
    return FLAG.get(country, "🏳")


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html(scores, participants):
    last_run = scores.get("lastRunAt") or "—"
    # Pretty-print the date
    if last_run != "—":
        try:
            from datetime import datetime, timedelta
            dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            dt_bst = dt + timedelta(hours=1)  # World Cup runs entirely in BST (UTC+1)
            day = str(int(dt_bst.strftime("%d")))  # no leading zero, cross-platform
            last_run = f"{day} {dt_bst.strftime('%b %Y · %H:%M')} BST"
        except Exception:
            pass

    # Sort participants by total descending
    ranked = sorted(
        scores["participants"].items(),
        key=lambda kv: kv[1]["total"],
        reverse=True,
    )

    # Build leaderboard rows HTML
    leaderboard_rows = ""
    for rank_idx, (name, pdata) in enumerate(ranked):
        rank_num = rank_idx + 1
        medal = MEDAL[rank_idx] if rank_idx < len(MEDAL) else "🎖"
        total = pdata["total"]
        is_first = rank_num == 1
        first_class = " first-place" if is_first else ""

        # Countries grid
        countries_html = ""
        for country, cdata in pdata["countries"].items():
            pts = cdata["points"]
            flag_em = flag(country)
            if pts > 0:
                cstyle = "color:#f5c518;font-weight:600;"
            else:
                cstyle = "color:rgba(255,255,255,0.25);"
            pts_str = f"+{pts}" if pts > 0 else "0"
            countries_html += f"""
                <div class="country-cell" style="{cstyle}">
                  <span class="cflag">{flag_em}</span>
                  <span class="cname">{country}</span>
                  <span class="cpts">{pts_str}</span>
                </div>"""

        # Points log
        log_html = ""
        log_entries = sorted(pdata.get("log", []), key=lambda e: e.get("date", ""), reverse=True)
        if log_entries:
            for entry in log_entries:
                pts_val = entry.get("points", 0)
                country_name = entry.get("country", "")
                ev_key = entry.get("event", "")
                opp = entry.get("opponent", "")
                date_str = entry.get("date", "")
                label = event_label(ev_key, opp)
                flag_em = flag(country_name)
                badge_class = "badge-gold" if pts_val >= 4 else "badge-white"
                log_html += f"""
                <div class="log-entry">
                  <span class="log-badge {badge_class}">+{pts_val}</span>
                  <span class="log-desc">{flag_em} {country_name} {label}</span>
                  <span class="log-date">{date_str}</span>
                </div>"""
        else:
            log_html = '<div class="log-empty">No points yet — the tournament is just getting started! ⚽</div>'

        leaderboard_rows += f"""
      <div class="player-card{first_class}" onclick="toggle('{name}')">
        <div class="card-header" id="header-{name}">
          <span class="rank">{rank_num}</span>
          <span class="medal">{medal}</span>
          <span class="player-name">{name.upper()}</span>
          <span class="points-badge">{total} pts</span>
          <span class="chevron" id="chev-{name}">▼</span>
        </div>
        <div class="card-body" id="body-{name}">
          <div class="section-label">Countries</div>
          <div class="countries-grid">
            {countries_html}
          </div>
          <div class="divider"></div>
          <div class="section-label">Points Log</div>
          <div class="log-list">
            {log_html}
          </div>
        </div>
      </div>"""

    # Recent results
    recent_results = scores.get("recentResults", [])
    recent_html = ""
    if recent_results:
        for res in recent_results[:10]:
            home = res.get("homeTeam", "")
            away = res.get("awayTeam", "")
            hs = res.get("homeScore")
            as_ = res.get("awayScore")
            date_str = res.get("date", "")
            stage_str = res.get("stage", "")
            hf = flag(home)
            af = flag(away)
            recent_html += f"""
          <div class="result-row">
            <span class="result-home">{hf} {home}</span>
            <span class="result-score">{f"{hs} – {as_}" if hs is not None and as_ is not None else "–"}</span>
            <span class="result-away">{away} {af}</span>
            <span class="result-meta">{stage_str} · {date_str}</span>
          </div>"""
    else:
        recent_html = '<div class="log-empty">No results yet — check back once the tournament begins! ⚽</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>McAndrew Family · World Cup 2026 Sweepstake</title>
  <style>
    /* ===================== RESET & BASE ===================== */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: #1a472a;
      color: #ffffff;
      min-height: 100vh;
      /* Horizontal pitch stripe pattern */
      background-image: repeating-linear-gradient(
        180deg,
        rgba(0,0,0,0) 0px,
        rgba(0,0,0,0) 48px,
        rgba(0,0,0,0.08) 48px,
        rgba(0,0,0,0.08) 96px
      );
    }}

    /* ===================== LAYOUT ===================== */
    .container {{
      max-width: 680px;
      margin: 0 auto;
      padding: 24px 16px 60px;
    }}

    /* ===================== HEADER ===================== */
    .site-header {{
      text-align: center;
      margin-bottom: 32px;
      padding-bottom: 20px;
      border-bottom: 2px solid rgba(245,197,24,0.3);
    }}
    .site-header h1 {{
      font-size: 1.6rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #ffffff;
    }}
    .site-header .subtitle {{
      font-size: 1rem;
      font-variant: small-caps;
      letter-spacing: 0.08em;
      color: #f5c518;
      margin-top: 4px;
    }}
    .site-header .updated {{
      font-size: 0.78rem;
      color: rgba(255,255,255,0.45);
      margin-top: 8px;
    }}
    .trophy-row {{
      font-size: 2.2rem;
      margin-bottom: 6px;
    }}

    /* ===================== SECTION TITLES ===================== */
    .section-title {{
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.5);
      margin: 28px 0 10px;
    }}

    /* ===================== PLAYER CARD ===================== */
    .player-card {{
      border-radius: 10px;
      margin-bottom: 10px;
      overflow: hidden;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.1);
      cursor: pointer;
      transition: background 0.15s;
    }}
    .player-card:hover {{
      background: rgba(255,255,255,0.09);
    }}
    .player-card.first-place {{
      border-left: 4px solid #f5c518;
      background: rgba(245,197,24,0.08);
    }}
    .player-card.first-place:hover {{
      background: rgba(245,197,24,0.12);
    }}

    /* Card header (always visible) */
    .card-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      user-select: none;
    }}
    .rank {{
      font-size: 0.85rem;
      font-weight: 700;
      color: rgba(255,255,255,0.5);
      width: 18px;
      text-align: center;
      flex-shrink: 0;
    }}
    .medal {{
      font-size: 1.3rem;
      flex-shrink: 0;
    }}
    .player-name {{
      flex: 1;
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}
    .points-badge {{
      background: rgba(245,197,24,0.15);
      color: #f5c518;
      font-weight: 700;
      font-size: 0.9rem;
      padding: 3px 10px;
      border-radius: 20px;
      border: 1px solid rgba(245,197,24,0.35);
      flex-shrink: 0;
    }}
    .chevron {{
      color: rgba(255,255,255,0.4);
      font-size: 0.8rem;
      flex-shrink: 0;
      transition: transform 0.2s;
    }}
    .chevron.open {{
      transform: rotate(180deg);
    }}

    /* Card body (collapsed by default) */
    .card-body {{
      display: none;
      padding: 0 16px 16px;
      border-top: 1px solid rgba(255,255,255,0.07);
    }}
    .card-body.open {{
      display: block;
    }}

    /* ===================== COUNTRIES GRID ===================== */
    .section-label {{
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.4);
      margin: 14px 0 8px;
    }}
    .countries-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px 12px;
    }}
    .country-cell {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.88rem;
      padding: 4px 0;
    }}
    .cflag {{
      font-size: 1.1rem;
      flex-shrink: 0;
    }}
    .cname {{
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .cpts {{
      font-size: 0.82rem;
      font-weight: 700;
      text-align: right;
      flex-shrink: 0;
      min-width: 28px;
    }}

    /* ===================== DIVIDER ===================== */
    .divider {{
      height: 1px;
      background: rgba(255,255,255,0.1);
      margin: 14px 0;
    }}

    /* ===================== POINTS LOG ===================== */
    .log-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .log-entry {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      font-size: 0.85rem;
    }}
    .log-badge {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 12px;
      flex-shrink: 0;
    }}
    .badge-gold {{
      background: rgba(245,197,24,0.2);
      color: #f5c518;
      border: 1px solid rgba(245,197,24,0.4);
    }}
    .badge-white {{
      background: rgba(255,255,255,0.1);
      color: #ffffff;
      border: 1px solid rgba(255,255,255,0.2);
    }}
    .log-desc {{
      flex: 1;
      color: rgba(255,255,255,0.85);
    }}
    .log-date {{
      font-size: 0.73rem;
      color: rgba(255,255,255,0.35);
      flex-shrink: 0;
      white-space: nowrap;
    }}
    .log-empty {{
      font-size: 0.85rem;
      color: rgba(255,255,255,0.35);
      font-style: italic;
      padding: 6px 0;
    }}

    /* ===================== RECENT RESULTS ===================== */
    .results-card {{
      border-radius: 10px;
      overflow: hidden;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .result-row {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      grid-template-rows: auto auto;
      align-items: center;
      gap: 4px 10px;
      padding: 10px 14px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      font-size: 0.88rem;
    }}
    .result-row:last-child {{
      border-bottom: none;
    }}
    .result-home {{
      text-align: right;
      color: rgba(255,255,255,0.85);
    }}
    .result-score {{
      font-weight: 800;
      font-size: 1rem;
      color: #f5c518;
      text-align: center;
      white-space: nowrap;
    }}
    .result-away {{
      text-align: left;
      color: rgba(255,255,255,0.85);
    }}
    .result-meta {{
      grid-column: 1 / -1;
      text-align: center;
      font-size: 0.72rem;
      color: rgba(255,255,255,0.3);
    }}

    /* ===================== FOOTER ===================== */
    .footer {{
      text-align: center;
      margin-top: 36px;
      font-size: 0.72rem;
      color: rgba(255,255,255,0.25);
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- HEADER -->
    <header class="site-header">
      <div class="trophy-row">⚽ 🏆 ⚽</div>
      <h1>McAndrew Family</h1>
      <div class="subtitle">World Cup 2026 · Sweepstake</div>
      <div class="updated">Updated: {last_run}</div>
    </header>

    <!-- LEADERBOARD -->
    <div class="section-title">Leaderboard</div>
    {leaderboard_rows}

    <!-- RECENT RESULTS -->
    <div class="section-title">Recent Results</div>
    <div class="results-card">
      {recent_html}
    </div>

    <div class="footer">
      McAndrew Family Sweepstake 2026 · Powered by football-data.org &amp; GitHub Pages
    </div>
  </div>

  <script>
    function toggle(name) {{
      var body = document.getElementById('body-' + name);
      var chev = document.getElementById('chev-' + name);
      if (body.classList.contains('open')) {{
        body.classList.remove('open');
        chev.classList.remove('open');
      }} else {{
        body.classList.add('open');
        chev.classList.add('open');
      }}
    }}
  </script>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Read scores.json from local file if available (written by update_scores.py in same run),
    # otherwise fall back to GitHub API. Avoids a race condition where the API briefly
    # returns a cached pre-update version when called within seconds of the write.
    import json as _json
    local_scores = os.path.join(os.path.dirname(__file__), "scores.json")
    if os.path.exists(local_scores):
        print("Reading scores.json from local file...")
        with open(local_scores, encoding="utf-8") as _f:
            scores = _json.load(_f)
    else:
        print("Reading scores.json from GitHub...")
        scores, _ = read_json("scores.json")

    print("Reading participants.json from GitHub...")
    participants, _ = read_json("participants.json")

    print("Building HTML...")
    html = build_html(scores, participants)

    # Write locally
    local_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written locally: {local_path} ({len(html):,} bytes)")

    # Get current SHA of index.html on GitHub (may not exist on first run)
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    r = __import__("requests").get(
        f"https://api.github.com/repos/{repo}/contents/index.html",
        headers={"Authorization": f"token {token}"},
    )
    html_sha = r.json().get("sha", "") if r.status_code == 200 else ""
    if html_sha:
        print(f"Existing index.html SHA: {html_sha[:12]}...")
    else:
        print("index.html does not exist on GitHub yet — will create.")

    # Upload to GitHub
    print("Uploading index.html to GitHub...")
    result = write_html("index.html", html, html_sha, "Regenerate leaderboard")
    new_sha = result.get("content", {}).get("sha", "?")
    print(f"Upload successful. New SHA: {new_sha[:12] if new_sha != '?' else '?'}...")
    print("Done! Visit https://BandyBarbecue.github.io/mcandrew-sweepstake-2026")


if __name__ == "__main__":
    main()
