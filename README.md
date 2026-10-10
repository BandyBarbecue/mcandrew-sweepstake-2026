# World Cup 2026 Family Sweepstake

A fully automated tracker for a four-player family World Cup 2026 sweepstake. Each player owned 12 of the 48 teams. Every day a GitHub Actions job pulled the latest results, applied our custom scoring rules, updated the leaderboard site and emailed everyone a branded digest. It ran unattended for the whole tournament.

**Live site:** https://bandybarbecue.github.io/mcandrew-sweepstake-2026

## How it works

```
GitHub Actions (daily cron)
  ├─ update_scores.py   football-data.org API → scoring engine → scores.json
  ├─ fetch_fixtures.py  upcoming fixtures → fixtures.json (read-only, fails soft)
  ├─ send_digest.py     HTML email digest of new points via Gmail
  └─ Pages rebuild      explicit rebuild request so the site never serves stale data
GitHub Pages
  └─ index.html + assets/  static page; fetches the JSON and renders everything client-side
```

- **Scoring engine** (`update_scores.py`, `scoring-rules.json`): it awards points for group wins and draws, qualification (top-two and best third-place), and each knockout round won. It is idempotent: re-running it never double-awards, and qualification bonuses are tracked separately.
- **Front end** (`index.html`, `assets/app.js`, `assets/derive.js`): vanilla HTML, CSS and JS with no framework and no build step. All presentation data is derived client-side by a pure module (`derive.js`) that has its own Node tests. The page has:
  - standings with expandable per-player event logs;
  - a scroll-drawn SVG **points-race chart** with filters and collision-free labels;
  - a matchday timeline showing "family stakes", such as when one player owns both teams;
  - a horizontally scrollable **knockout bracket**, a squad explorer, records, and recent results;
  - self-hosted SVG flags;
  - accessibility support: semantic buttons with `aria-expanded`, `prefers-reduced-motion`, 40px tap targets, and a screen-reader table mirroring the chart.
- **Email** (`send_digest.py`): announces each scoring event exactly once by tracking events by identity rather than by date. Recipients come from a repository secret, so no addresses are stored in the repo.

## Problems solved along the way

- **Team-name mismatches:** the API wrote "Bosnia-Herzegovina" and "Cape Verde Islands", so one player silently missed 11 points. Fixed with name aliases and a guarded backfill.
- **Dropped email events:** a "since last email" date cutoff skipped results processed the morning after a match. Replaced it with per-event identity tracking.
- **Stale site:** three quick commits per run triggered racing Pages builds, and if the last one failed the site stayed stale for a day. The workflow now requests a final rebuild.
- **Email rendering:** Gmail and Outlook don't render SVG, so the email uses PNG versions of the flags.
- **Verification:** a full sandboxed test recomputed all 85 real matches from scratch and reproduced the live system's 129 scoring events exactly.

## Running it

```bash
pip install -r requirements.txt
# env: FOOTBALL_DATA_API_KEY, GITHUB_TOKEN, GITHUB_REPO, GMAIL_APP_PASSWORD, DIGEST_RECIPIENTS (comma-separated)
python update_scores.py
python fetch_fixtures.py
python send_digest.py --test     # sends only to the sender, without updating state
python -m pytest tests           # Python tests
node --test tests/derive.test.mjs
```

## How it was built

I built this with **Claude Code**. The first working version went live in one evening at the start of the tournament. The July redesign ("Tournament Editorial") followed a spec-driven process: brainstorming with browser mockups, an approved design spec, a 12-task plan, and test-first implementation. The spec and plan are in [`docs/superpowers/`](docs/superpowers/).

I ran the sweepstake, set the scoring rules, chose the design direction, and set up the API, Gmail and Actions secrets. Claude Code wrote most of the code.
