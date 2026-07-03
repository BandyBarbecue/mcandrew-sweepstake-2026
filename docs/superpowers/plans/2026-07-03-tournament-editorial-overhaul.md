# Tournament Editorial UX Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python-generated leaderboard page with a hand-authored static site ("Tournament Editorial" design) plus a matching redesigned daily email, without touching scoring logic.

**Architecture:** `index.html` + `assets/styles.css` + `assets/app.js` + `assets/derive.js` (ES modules, no framework, no build step) fetch `scores.json` / `participants.json` / `scoring-rules.json` / `fixtures.json` same-origin on GitHub Pages and render everything client-side. A new read-only `fetch_fixtures.py` writes `fixtures.json`. `send_digest.py`'s HTML builder is rewritten; its send/tracking logic is unchanged. `generate_html.py` is retired.

**Tech Stack:** Vanilla HTML/CSS/JS (ES modules), SVG charts, IntersectionObserver; Python 3 + requests for the fixtures fetcher and email; `node --test` (Node 24) for JS unit tests; pytest for Python tests; flag-icons artwork via flagcdn.com.

**User decisions (already made):**
- Visual direction: "Tournament Editorial" (approved mockup `direction-v3.html`) — Fraunces / Schibsted Grotesk / JetBrains Mono, dark green-black + parchment, gold/terracotta/sage accents, no emoji, no glassmorphism.
- Architecture: Approach A — static shell + client-side rendering; retire `generate_html.py`.
- Sections: hero, standings (with per-event log), points race chart, matchday timeline, knockout bracket, squad explorer (per-team points, e.g. "Cape Verde · 10"), records, recent results.
- Email: restyle + enrich (gap-to-leader, today's stakes), no emoji, table-based.
- Scoring logic untouched: `update_scores.py`, `scoring-rules.json`, `github_utils.py` must not change.

**Spec:** `docs/superpowers/specs/2026-07-03-ux-overhaul-design.md` (approved 3 Jul 2026).

**Environment notes for the engineer:**
- Windows 11; shell commands below are Git Bash / POSIX unless stated.
- `.env` in repo root provides `FOOTBALL_DATA_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`, `GMAIL_*`. Python modules load it via `dotenv`. Pytest runs on this machine therefore import-time env checks pass.
- The GitHub repo (`GITHUB_REPO`, currently `BandyBarbecue/mcandrew-sweepstake-2026`) is BOTH the Pages site and this local clone's remote. `update_scores.py` commits `scores.json` to it via the API, so **always `git pull --rebase origin main` before pushing**.
- Live site: `https://bandybarbecue.github.io/mcandrew-sweepstake-2026`.
- Player identity colors (fixed forever): Kenny `#d9a441` gold · Fiona `#7ea87f` sage · Alex `#8fa3c9` slate · Edward `#c9808f` rose.

**File map (end state):**

```
index.html                  # static shell (committed once, then edited directly)
assets/styles.css           # all site CSS
assets/app.js               # fetch + render + interactions (ES module)
assets/derive.js            # pure derivation functions (ES module, node-testable)
flags/<code>.svg            # 48 flags + _fallback.svg (site)
flags/png/<code>.png        # 40px PNGs (email)
flag-codes.json             # country name -> flagcdn code (single source of truth)
fetch_fixtures.py           # NEW read-only fixtures fetcher
send_digest.py              # build_email_html()/subject rewritten; send logic unchanged
scripts/download_flags.py   # dev-only, not in scheduled chain
tests/derive.test.mjs       # node --test
tests/test_fetch_fixtures.py
tests/test_send_digest.py
.nojekyll                   # skip Jekyll on Pages
(deleted: generate_html.py)
```

---

### Task 1: Flag assets + shared country-code map

**Goal:** Commit 48 SVG flags, 48 email PNGs, a fallback flag, and `flag-codes.json` as the single country→code source.

**Files:**
- Create: `flag-codes.json`
- Create: `scripts/download_flags.py`
- Create (generated): `flags/*.svg`, `flags/png/*.png`, `flags/_fallback.svg`

**Acceptance Criteria:**
- [ ] `flag-codes.json` maps all 48 countries in `participants.json` `countryToOwner` to flagcdn codes
- [ ] `flags/` contains 48 `.svg` + `_fallback.svg`; `flags/png/` contains 48 `.png`
- [ ] Download script validates completeness against `participants.json` and fails loudly on any miss

**Verify:** `python scripts/download_flags.py` → `OK: 48/48 flags downloaded` ; `ls flags/*.svg | wc -l` → 49 (48 + fallback)

**Steps:**

- [ ] **Step 1: Write `flag-codes.json`** (repo root)

```json
{
  "Qatar": "qa", "Uruguay": "uy", "Morocco": "ma", "Argentina": "ar",
  "Norway": "no", "Iran": "ir", "Croatia": "hr", "Spain": "es",
  "Belgium": "be", "Ivory Coast": "ci", "Mexico": "mx", "Czechia": "cz",
  "Bosnia & Herz.": "ba", "Japan": "jp", "Panama": "pa", "Senegal": "sn",
  "DR Congo": "cd", "Canada": "ca", "Cape Verde": "cv", "Jordan": "jo",
  "USA": "us", "South Africa": "za", "England": "gb-eng", "Colombia": "co",
  "Haiti": "ht", "Brazil": "br", "Sweden": "se", "France": "fr",
  "South Korea": "kr", "Ecuador": "ec", "New Zealand": "nz", "Saudi Arabia": "sa",
  "Netherlands": "nl", "Turkey": "tr", "Paraguay": "py", "Iraq": "iq",
  "Scotland": "gb-sct", "Egypt": "eg", "Australia": "au", "Curaçao": "cw",
  "Ghana": "gh", "Austria": "at", "Germany": "de", "Tunisia": "tn",
  "Algeria": "dz", "Portugal": "pt", "Switzerland": "ch", "Uzbekistan": "uz"
}
```

- [ ] **Step 2: Write `scripts/download_flags.py`**

```python
"""Dev-only: download flag SVGs (site) and 40px PNGs (email) from flagcdn.com.
Not part of the scheduled chain. Validates coverage against participants.json.
"""
import json
import os
import sys
import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")

def main():
    with open(os.path.join(ROOT, "flag-codes.json"), encoding="utf-8") as f:
        codes = json.load(f)
    with open(os.path.join(ROOT, "participants.json"), encoding="utf-8") as f:
        owners = json.load(f)["countryToOwner"]

    missing = sorted(set(owners) - set(codes))
    if missing:
        sys.exit(f"flag-codes.json is missing: {missing}")

    svg_dir = os.path.join(ROOT, "flags")
    png_dir = os.path.join(ROOT, "flags", "png")
    os.makedirs(png_dir, exist_ok=True)

    for country, code in sorted(codes.items()):
        svg = requests.get(f"https://flagcdn.com/{code}.svg", timeout=30)
        svg.raise_for_status()
        with open(os.path.join(svg_dir, f"{code}.svg"), "wb") as f:
            f.write(svg.content)
        png = requests.get(f"https://flagcdn.com/w40/{code}.png", timeout=30)
        png.raise_for_status()
        with open(os.path.join(png_dir, f"{code}.png"), "wb") as f:
            f.write(png.content)
        print(f"  {country} -> {code}")

    fallback = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3">'
                '<rect width="4" height="3" fill="#5a6b5e"/>'
                '<path d="M0 0h4L0 3z" fill="#6b7a6e"/></svg>')
    with open(os.path.join(svg_dir, "_fallback.svg"), "w", encoding="utf-8") as f:
        f.write(fallback)

    print(f"OK: {len(codes)}/48 flags downloaded")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it**

Run: `python scripts/download_flags.py`
Expected: 48 lines + `OK: 48/48 flags downloaded`

- [ ] **Step 4: Spot-check** — open `flags/gb-eng.svg` and `flags/png/es.png`; both non-empty, England shows St George cross.

- [ ] **Step 5: Commit**

```bash
git add flag-codes.json scripts/download_flags.py flags/
git commit -m "Add self-hosted flag assets and country-code map"
```

---

### Task 2: `fetch_fixtures.py` + tests

**Goal:** Read-only script that writes upcoming fixtures to `fixtures.json` in the GitHub repo; never blocks the chain.

**Files:**
- Create: `fetch_fixtures.py`
- Test: `tests/test_fetch_fixtures.py`

**Acceptance Criteria:**
- [ ] Extracts only `SCHEDULED`/`TIMED` matches, names mapped through `apiNameAliases`
- [ ] Writes `fixtures.json` `{"fetchedAt": iso-utc, "fixtures": [{matchId, homeTeam, awayTeam, utcDate, stage}]}` sorted by `utcDate`
- [ ] Any exception → prints warning, exits 0 (previous `fixtures.json` left in place)
- [ ] Does not import or modify scoring state (`scores.json` untouched)

**Verify:** `python -m pytest tests/test_fetch_fixtures.py -v` → all PASS; then `python fetch_fixtures.py` → `fixtures.json written (N fixtures)`

**Steps:**

- [ ] **Step 1: Write the failing tests** — `tests/test_fetch_fixtures.py`

```python
from fetch_fixtures import extract_fixtures

ALIASES = {"Korea Republic": "South Korea"}

SAMPLE = [
    {"id": 1, "status": "FINISHED", "stage": "LAST_32", "utcDate": "2026-07-02T16:00:00Z",
     "homeTeam": {"name": "Portugal"}, "awayTeam": {"name": "Croatia"}},
    {"id": 2, "status": "TIMED", "stage": "LAST_32", "utcDate": "2026-07-04T16:00:00Z",
     "homeTeam": {"name": "Spain"}, "awayTeam": {"name": "Korea Republic"}},
    {"id": 3, "status": "SCHEDULED", "stage": "LAST_16", "utcDate": "2026-07-05T20:00:00Z",
     "homeTeam": {"name": None}, "awayTeam": {"name": "France"}},
]

def test_only_upcoming_statuses():
    out = extract_fixtures(SAMPLE, ALIASES)
    assert [f["matchId"] for f in out] == [2, 3]

def test_names_aliased_and_null_safe():
    out = extract_fixtures(SAMPLE, ALIASES)
    assert out[0]["awayTeam"] == "South Korea"
    assert out[1]["homeTeam"] == "TBD"

def test_sorted_and_shaped():
    out = extract_fixtures(SAMPLE, ALIASES)
    assert out[0]["utcDate"] <= out[1]["utcDate"]
    assert set(out[0]) == {"matchId", "homeTeam", "awayTeam", "utcDate", "stage"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fetch_fixtures.py -v`
Expected: FAIL / import error ("No module named fetch_fixtures")

- [ ] **Step 3: Write `fetch_fixtures.py`**

```python
"""
fetch_fixtures.py — READ-ONLY fixtures fetcher.
Writes fixtures.json to the GitHub repo for the site's matchday/bracket
sections and the email's "today's stakes". Never touches scoring state.
On any failure it warns and exits 0 so the scheduled chain continues.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from github_utils import read_json, write_html

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"
UPCOMING_STATUSES = {"SCHEDULED", "TIMED"}


def extract_fixtures(matches, aliases):
    fixtures = []
    for m in matches:
        if m.get("status") not in UPCOMING_STATUSES:
            continue
        home = m["homeTeam"].get("name") or "TBD"
        away = m["awayTeam"].get("name") or "TBD"
        fixtures.append({
            "matchId": m["id"],
            "homeTeam": aliases.get(home, home),
            "awayTeam": aliases.get(away, away),
            "utcDate": m["utcDate"],
            "stage": m["stage"],
        })
    return sorted(fixtures, key=lambda f: f["utcDate"])


def main():
    try:
        participants, _ = read_json("participants.json")
        r = requests.get(
            f"{API_BASE}/competitions/{COMPETITION}/matches",
            headers={"X-Auth-Token": API_KEY}, timeout=30,
        )
        r.raise_for_status()
        fixtures = extract_fixtures(r.json().get("matches", []),
                                    participants["apiNameAliases"])
        payload = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "fixtures": fixtures,
        }
        try:
            _, sha = read_json("fixtures.json")
        except Exception:
            sha = ""  # first run: create
        write_html("fixtures.json",
                   json.dumps(payload, indent=2, ensure_ascii=False),
                   sha, "Update fixtures")
        print(f"fixtures.json written ({len(fixtures)} fixtures)")
    except Exception as e:
        print(f"WARNING: fixtures fetch skipped: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

(`write_html` is reused deliberately — it is a generic "PUT text content" helper that handles the empty-sha create case; `write_json` requires an existing sha.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fetch_fixtures.py -v`
Expected: 3 passed

- [ ] **Step 5: Run for real, inspect output**

Run: `python fetch_fixtures.py`
Expected: `fixtures.json written (N fixtures)`; check `https://api.github.com` commit exists or `read_json("fixtures.json")` returns fixtures with aliased names.

- [ ] **Step 6: Commit**

```bash
git add fetch_fixtures.py tests/test_fetch_fixtures.py
git commit -m "Add read-only fixtures fetcher writing fixtures.json"
```

---

### Task 3: `assets/derive.js` + node tests

**Goal:** All presentation-data derivations as pure, unit-tested ES module functions.

**Files:**
- Create: `assets/derive.js`
- Test: `tests/derive.test.mjs`

**Acceptance Criteria:**
- [ ] `cumulativeSeries` totals end exactly at each player's `total` (validated against the real `scores.json`)
- [ ] `teamStatus` marks knockout losers and non-qualifiers eliminated once knockouts began; all 48 covered
- [ ] `records` returns biggestDay, mostValuableTeam, knockoutKing, sharpestRise (3-date window)
- [ ] `fixtureStakes` produces derby / head-to-head sentences with points from `scoring-rules.json`
- [ ] `bracketData` pads rounds to expected tie counts (16/8/4/2/1/1) with TBD placeholders

**Verify:** `node --test tests/derive.test.mjs` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests** — `tests/derive.test.mjs`

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  allEvents, cumulativeSeries, teamStatus, records,
  fixtureStakes, bracketData, matchdayNumber,
} from '../assets/derive.js';

const scores = JSON.parse(readFileSync(new URL('../scores.json', import.meta.url)));
const participants = JSON.parse(readFileSync(new URL('../participants.json', import.meta.url)));
const rules = JSON.parse(readFileSync(new URL('../scoring-rules.json', import.meta.url)));

test('cumulativeSeries ends at each real total', () => {
  const { series } = cumulativeSeries(scores);
  for (const [player, data] of Object.entries(scores.participants)) {
    assert.equal(series[player].at(-1), data.total, player);
  }
});

test('cumulative filters partition the total', () => {
  const all = cumulativeSeries(scores).series;
  const grp = cumulativeSeries(scores, 'group').series;
  const ko = cumulativeSeries(scores, 'knockout').series;
  for (const p of Object.keys(scores.participants)) {
    assert.equal((grp[p].at(-1) ?? 0) + (ko[p].at(-1) ?? 0), all[p].at(-1));
  }
});

test('teamStatus covers all 48 and eliminates knockout losers', () => {
  const st = teamStatus(scores, participants);
  assert.equal(Object.keys(st).length, 48);
  // Croatia lost R32 to Portugal on 2 Jul (real data)
  assert.equal(st['Croatia'].alive, false);
  // A knockout winner is alive
  const someWin = allEvents(scores).find(e => e.event === 'LAST_32_WIN');
  assert.equal(st[someWin.country].alive, true);
});

test('records shape and sanity', () => {
  const r = records(scores);
  assert.ok(r.biggestDay.points > 0);
  assert.ok(r.mostValuableTeam.points > 0);
  assert.ok(r.knockoutKing.owner);
  assert.ok(r.sharpestRise.points >= r.biggestDay.points >= 0 || r.sharpestRise.points > 0);
});

test('fixtureStakes derby and head-to-head', () => {
  const owners = { Spain: 'Kenny', Belgium: 'Kenny', England: 'Fiona' };
  const derby = fixtureStakes(
    { homeTeam: 'Spain', awayTeam: 'Belgium', stage: 'LAST_16' }, owners, rules);
  assert.match(derby, /Kenny derby/);
  assert.match(derby, new RegExp(`\\+${rules.LAST_16_WIN}`));
  const h2h = fixtureStakes(
    { homeTeam: 'Spain', awayTeam: 'England', stage: 'FINAL' }, owners, rules);
  assert.match(h2h, /Kenny/); assert.match(h2h, /Fiona/);
});

test('bracketData pads to expected counts', () => {
  const rounds = bracketData(scores, { fixtures: [] });
  const byStage = Object.fromEntries(rounds.map(r => [r.stage, r.ties.length]));
  assert.deepEqual(byStage, {
    LAST_32: 16, LAST_16: 8, QUARTER_FINALS: 4,
    SEMI_FINALS: 2, THIRD_PLACE: 1, FINAL: 1,
  });
});

test('matchdayNumber', () => {
  assert.equal(matchdayNumber('2026-06-11'), 1);
  assert.equal(matchdayNumber('2026-07-03'), 23);
});
```

- [ ] **Step 2: Run to verify failure**

Run: `node --test tests/derive.test.mjs`
Expected: FAIL (cannot find `../assets/derive.js`)

- [ ] **Step 3: Write `assets/derive.js`**

```js
// Pure derivation functions. No DOM, no fetch — unit-testable under node --test.

export const KNOCKOUT_EVENTS = ['LAST_32_WIN', 'LAST_16_WIN', 'QUARTER_FINALS_WIN',
  'SEMI_FINALS_WIN', 'THIRD_PLACE_WIN', 'FINAL_WIN'];
export const QUALIFY_EVENTS = ['QUALIFY_TOP_2', 'QUALIFY_BEST_THIRD'];
export const STAGE_EVENT = {
  GROUP_STAGE: 'GROUP_STAGE_WIN', LAST_32: 'LAST_32_WIN', LAST_16: 'LAST_16_WIN',
  QUARTER_FINALS: 'QUARTER_FINALS_WIN', SEMI_FINALS: 'SEMI_FINALS_WIN',
  THIRD_PLACE: 'THIRD_PLACE_WIN', FINAL: 'FINAL_WIN',
};
export const STAGE_LABELS = {
  GROUP_STAGE: 'Group Stage', LAST_32: 'Round of 32', LAST_16: 'Round of 16',
  QUARTER_FINALS: 'Quarter-Final', SEMI_FINALS: 'Semi-Final',
  THIRD_PLACE: '3rd Place Play-off', FINAL: 'Final',
};
export const EVENT_LABELS = {
  GROUP_STAGE_WIN: 'won in the Group Stage', GROUP_STAGE_DRAW: 'drew in the Group Stage',
  QUALIFY_TOP_2: 'qualified from the group (top 2)',
  QUALIFY_BEST_THIRD: 'qualified as a best third',
  LAST_32_WIN: 'won the Round of 32', LAST_16_WIN: 'won the Round of 16',
  QUARTER_FINALS_WIN: 'won the Quarter-Final', SEMI_FINALS_WIN: 'won the Semi-Final',
  THIRD_PLACE_WIN: 'won the 3rd Place Play-off', FINAL_WIN: 'won the World Cup Final',
};
export const TOURNAMENT_START = '2026-06-11';

export function allEvents(scores) {
  return Object.entries(scores.participants)
    .flatMap(([owner, p]) => (p.log || []).map(e => ({ owner, ...e })));
}

export function matchdayNumber(dateISO) {
  const ms = new Date(dateISO + 'T00:00:00Z') - new Date(TOURNAMENT_START + 'T00:00:00Z');
  return Math.max(1, Math.round(ms / 86400000) + 1);
}

export function cumulativeSeries(scores, filter = 'all') {
  const evs = allEvents(scores).filter(e => {
    if (filter === 'group') return !KNOCKOUT_EVENTS.includes(e.event);
    if (filter === 'knockout') return KNOCKOUT_EVENTS.includes(e.event);
    return true;
  });
  const dates = [...new Set(evs.map(e => e.date))].sort();
  const players = Object.keys(scores.participants);
  const series = {};
  for (const pl of players) {
    let t = 0;
    series[pl] = dates.map(d => {
      t += evs.filter(e => e.owner === pl && e.date === d)
        .reduce((s, e) => s + e.points, 0);
      return t;
    });
  }
  return { dates, series };
}

export function teamStatus(scores, participants) {
  const evs = allEvents(scores);
  const knockoutBegan = evs.some(e => KNOCKOUT_EVENTS.includes(e.event));
  const qualified = new Set(evs.filter(e => QUALIFY_EVENTS.includes(e.event)).map(e => e.country));
  const koLosers = new Set(evs.filter(e => KNOCKOUT_EVENTS.includes(e.event)).map(e => e.opponent));
  const status = {};
  for (const [country, owner] of Object.entries(participants.countryToOwner)) {
    let alive = true;
    if (koLosers.has(country)) alive = false;
    else if (knockoutBegan && !qualified.has(country)) alive = false;
    status[country] = { owner, alive };
  }
  return status;
}

export function records(scores) {
  const evs = allEvents(scores);
  const dayTotals = {};
  for (const e of evs) {
    const k = `${e.owner}|${e.date}`;
    dayTotals[k] = (dayTotals[k] || 0) + e.points;
  }
  let biggestDay = { owner: '—', date: '', points: 0 };
  for (const [k, points] of Object.entries(dayTotals)) {
    if (points > biggestDay.points) {
      const [owner, date] = k.split('|');
      biggestDay = { owner, date, points };
    }
  }
  let mostValuableTeam = { country: '—', owner: '—', points: 0 };
  for (const [owner, p] of Object.entries(scores.participants)) {
    for (const [country, cd] of Object.entries(p.countries)) {
      if (cd.points > mostValuableTeam.points) {
        mostValuableTeam = { country, owner, points: cd.points };
      }
    }
  }
  const ko = {};
  for (const e of evs) {
    if (KNOCKOUT_EVENTS.includes(e.event)) ko[e.owner] = (ko[e.owner] || 0) + e.points;
  }
  const knockoutKing = Object.entries(ko)
    .map(([owner, points]) => ({ owner, points }))
    .sort((a, b) => b.points - a.points)[0] || { owner: '—', points: 0 };
  const { dates, series } = cumulativeSeries(scores);
  let sharpestRise = { owner: '—', endDate: '', points: 0 };
  for (const [owner, vals] of Object.entries(series)) {
    for (let i = 0; i < vals.length; i++) {
      const gain = vals[i] - (i >= 3 ? vals[i - 3] : 0);
      if (gain > sharpestRise.points) {
        sharpestRise = { owner, endDate: dates[i], points: gain };
      }
    }
  }
  return { biggestDay, mostValuableTeam, knockoutKing, sharpestRise };
}

export function fixtureStakes(fixture, countryToOwner, rules) {
  const ho = countryToOwner[fixture.homeTeam];
  const ao = countryToOwner[fixture.awayTeam];
  const evKey = STAGE_EVENT[fixture.stage];
  const pts = evKey ? rules[evKey] : null;
  const ptsTxt = pts ? ` +${pts} on the line.` : '';
  if (ho && ao && ho === ao) {
    return `${ho} derby — both teams are ${ho}'s. Guaranteed${pts ? ` +${pts}` : ' points'}.`;
  }
  if (ho && ao) {
    return `${ho}'s ${fixture.homeTeam} against ${ao}'s ${fixture.awayTeam}.${ptsTxt}`;
  }
  const owner = ho || ao;
  const team = ho ? fixture.homeTeam : fixture.awayTeam;
  if (owner) return `${owner}'s ${team} in action.${ptsTxt}`;
  return 'Neutral fixture — no family stake.';
}

export function upcomingFixtures(fixtures, nowISO, limit = 4) {
  return (fixtures?.fixtures || [])
    .filter(f => f.utcDate >= nowISO)
    .slice(0, limit);
}

const EXPECTED_TIES = {
  LAST_32: 16, LAST_16: 8, QUARTER_FINALS: 4, SEMI_FINALS: 2, THIRD_PLACE: 1, FINAL: 1,
};

export function bracketData(scores, fixtures) {
  const evs = allEvents(scores);
  return Object.keys(EXPECTED_TIES).map(stage => {
    const evKey = STAGE_EVENT[stage];
    const played = evs.filter(e => e.event === evKey).map(e => ({
      home: e.country, away: e.opponent, winner: e.country,
      date: e.date, matchId: e.matchId,
    }));
    const playedIds = new Set(played.map(t => t.matchId));
    const upcoming = (fixtures?.fixtures || [])
      .filter(f => f.stage === stage && !playedIds.has(f.matchId))
      .map(f => ({
        home: f.homeTeam, away: f.awayTeam, winner: null,
        utcDate: f.utcDate, matchId: f.matchId,
      }));
    const ties = [...played, ...upcoming];
    while (ties.length < EXPECTED_TIES[stage]) {
      ties.push({ home: 'TBD', away: 'TBD', winner: null, matchId: null });
    }
    return { stage, label: STAGE_LABELS[stage], ties };
  });
}
```

- [ ] **Step 4: Run tests until green**

Run: `node --test tests/derive.test.mjs`
Expected: all tests pass. If `records` sanity assertion is awkward against real data, simplify the assertion (records values must be > 0 and owners non-placeholder), not the implementation.

- [ ] **Step 5: Commit**

```bash
git add assets/derive.js tests/derive.test.mjs
git commit -m "Add pure derivation module with node tests"
```

---

### Task 4: Site shell — `index.html`, base CSS, data loading, hero, error state

**Goal:** The page loads all four JSON files, renders the hero with live stats, and shows a styled error state on fetch failure.

**Files:**
- Create: `index.html`
- Create: `assets/styles.css`
- Create: `assets/app.js`
- Create: `.nojekyll` (empty file)

**Acceptance Criteria:**
- [ ] `python -m http.server` + browser: hero renders with kicker, headline (word-by-word fade-up), stat strip showing real Matchday / Stage / Leader / Teams-alive values
- [ ] Renaming `scores.json` temporarily → styled error panel, no blank page, no console exception
- [ ] Fonts load (Fraunces serif visible); no emoji anywhere; Lighthouse-level basics: `lang`, `title`, meta viewport present

**Verify:** `python -m http.server 8010` then browser check of `http://localhost:8010` (hero + stats + error drill)

**Steps:**

- [ ] **Step 1: Write `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>McAndrew Family · World Cup 2026 Sweepstake</title>
  <meta name="description" content="Live standings for the McAndrew family World Cup 2026 sweepstake.">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230b120d'/%3E%3Ccircle cx='16' cy='13' r='7' fill='none' stroke='%23d9a441' stroke-width='2.5'/%3E%3Cpath d='M12 24h8M16 20v4' stroke='%23d9a441' stroke-width='2.5'/%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Schibsted+Grotesk:wght@400;500;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>

  <header class="topbar" id="topbar" data-hidden="true">
    <span class="topbar-wordmark serif">McAndrew <em>Sweepstake</em></span>
    <span class="topbar-scores mono" id="topbar-scores"></span>
    <nav class="topbar-nav" id="topbar-nav" aria-label="Sections">
      <a href="#standings">Standings</a><a href="#race">Race</a>
      <a href="#bracket">Bracket</a><a href="#squads">Squads</a>
    </nav>
    <button class="topbar-menu" id="topbar-menu" aria-expanded="false" aria-controls="topbar-nav" aria-label="Menu">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
    </button>
  </header>

  <main id="app" hidden>
    <section class="section dark hero" id="hero">
      <div class="container">
        <p class="kicker terra" id="hero-kicker">World Cup 2026 · USA · Canada · Mexico</p>
        <h1 class="hero-title serif" id="hero-title">One family, four rivals, <em class="gold">one cup.</em></h1>
        <p class="hero-sub" id="hero-sub">Forty-eight nations divided between Kenny, Fiona, Edward and Alex.
           Every goal counts. Every round doubles the stakes.</p>
        <dl class="stat-strip" id="stat-strip"></dl>
      </div>
      <div class="scroll-cue" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
      </div>
    </section>

    <section class="section dark" id="standings">
      <div class="container"><div id="standings-root"></div></div>
    </section>

    <section class="section deep" id="race">
      <div class="container"><div id="race-root"></div></div>
    </section>

    <section class="section cream" id="matchday">
      <div class="container"><div id="matchday-root"></div></div>
    </section>

    <section class="section dark" id="bracket">
      <div class="container wide"><div id="bracket-root"></div></div>
    </section>

    <section class="section dark" id="squads">
      <div class="container"><div id="squads-root"></div></div>
    </section>

    <section class="section cream" id="records">
      <div class="container"><div id="records-root"></div></div>
    </section>

    <section class="section deep" id="results">
      <div class="container"><div id="results-root"></div></div>
    </section>

    <footer class="footer">
      <p class="mono" id="footer-line"></p>
    </footer>
  </main>

  <div class="load-error" id="load-error" hidden>
    <div class="load-error-card">
      <p class="kicker terra">Own goal</p>
      <h2 class="serif">Couldn't load the latest scores</h2>
      <p>The data files didn't come through. Check your connection and refresh the page.</p>
      <button class="btn" onclick="location.reload()">Try again</button>
    </div>
  </div>

  <script type="module" src="assets/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `assets/styles.css`** (base + hero + error; later tasks append their own section blocks)

```css
/* ============ TOKENS ============ */
:root {
  --bg-deep: #0b120d;
  --bg: #0f1a14;
  --cream: #f2efe6;
  --cream-ink: #22301f;
  --cream-dim: #5a6b52;
  --ink: #e8e6df;
  --ink-dim: #9aa89c;
  --ink-faint: #6b7a6e;
  --gold: #d9a441;
  --terra: #c98a5b;
  --terra-deep: #b3763f;
  --sage: #7ea87f;
  --slate: #8fa3c9;
  --rose: #c9808f;
  --hairline: rgba(232, 230, 223, 0.12);
  --hairline-soft: rgba(232, 230, 223, 0.08);
  --cream-hairline: rgba(34, 48, 31, 0.14);
  --radius: 14px;
  --font-serif: 'Fraunces', Georgia, serif;
  --font-sans: 'Schibsted Grotesk', -apple-system, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { font-family: var(--font-sans); background: var(--bg); color: var(--ink);
       -webkit-font-smoothing: antialiased; }

.serif { font-family: var(--font-serif); font-weight: 500; letter-spacing: -0.01em; }
.serif em { font-style: italic; }
.mono { font-family: var(--font-mono); }
.gold { color: var(--gold); }
.terra { color: var(--terra); }
.kicker { font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.22em;
          text-transform: uppercase; font-weight: 600; }

.container { max-width: 720px; margin: 0 auto; padding: 0 20px; }
.container.wide { max-width: 1000px; }
.section { padding: 64px 0; }
.section.dark { background: var(--bg); }
.section.deep { background: var(--bg-deep); }
.section.cream { background: var(--cream); color: var(--cream-ink); }

.section-head { display: flex; justify-content: space-between; align-items: baseline;
                margin-bottom: 22px; }
.section-title { font-family: var(--font-serif); font-size: 1.7rem; font-weight: 500; }
.section-title em { font-style: italic; color: var(--terra); }
.section.cream .section-title em { color: var(--terra-deep); }

/* ============ TOPBAR ============ */
.topbar { position: fixed; inset: 0 0 auto 0; z-index: 50; display: flex;
          align-items: center; gap: 18px; padding: 10px 20px;
          background: rgba(11, 18, 13, 0.92); border-bottom: 1px solid var(--hairline);
          backdrop-filter: none; transition: transform 0.3s ease, opacity 0.3s ease; }
.topbar[data-hidden="true"] { transform: translateY(-100%); opacity: 0; pointer-events: none; }
.topbar-wordmark { font-size: 0.95rem; color: var(--ink); }
.topbar-wordmark em { color: var(--gold); }
.topbar-scores { font-size: 0.72rem; color: var(--ink-dim); flex: 1; white-space: nowrap;
                 overflow: hidden; text-overflow: ellipsis; }
.topbar-nav { display: flex; gap: 16px; }
.topbar-nav a { color: var(--ink-dim); text-decoration: none; font-size: 0.8rem;
                font-weight: 700; letter-spacing: 0.04em; }
.topbar-nav a:hover, .topbar-nav a:focus-visible { color: var(--gold); }
.topbar-menu { display: none; background: none; border: 1px solid var(--hairline);
               border-radius: 8px; color: var(--ink); padding: 5px 8px; cursor: pointer; }
@media (max-width: 640px) {
  .topbar-nav { display: none; position: absolute; top: 100%; right: 12px;
                flex-direction: column; gap: 0; background: var(--bg-deep);
                border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden;
                min-width: 160px; }
  .topbar-nav.open { display: flex; }
  .topbar-nav a { padding: 12px 16px; border-bottom: 1px solid var(--hairline-soft); }
  .topbar-menu { display: block; }
}

/* ============ HERO ============ */
.hero { min-height: 92vh; display: flex; flex-direction: column; justify-content: center;
        position: relative;
        background:
          radial-gradient(ellipse 90% 55% at 50% -12%, rgba(140, 190, 120, 0.13), transparent),
          var(--bg-deep); }
.hero .kicker { margin-bottom: 20px; }
.hero-title { font-size: clamp(2.4rem, 7.5vw, 4rem); line-height: 1.06; color: #f2f0e9;
              max-width: 14ch; }
.hero-title .w { display: inline-block; opacity: 0; transform: translateY(14px);
                 animation: word-in 0.6s cubic-bezier(0.2, 0.7, 0.3, 1) forwards;
                 animation-delay: calc(var(--i) * 90ms); }
@keyframes word-in { to { opacity: 1; transform: none; } }
.hero-sub { color: var(--ink-dim); max-width: 44ch; line-height: 1.65; margin-top: 20px;
            font-size: 1rem; }
.stat-strip { display: flex; flex-wrap: wrap; gap: 28px 40px; margin-top: 40px;
              border-top: 1px solid var(--hairline); padding-top: 22px; }
.stat-strip .stat dt { font-family: var(--font-mono); font-size: 0.6rem;
                       letter-spacing: 0.2em; text-transform: uppercase;
                       color: var(--ink-faint); margin-bottom: 4px; }
.stat-strip .stat dd { font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; }
.stat-strip .stat dd small { color: var(--ink-faint); font-size: 0.8rem; }
.scroll-cue { position: absolute; bottom: 26px; left: 50%; transform: translateX(-50%);
              color: var(--ink-faint); animation: cue 2.2s ease-in-out infinite; }
@keyframes cue { 0%, 100% { transform: translate(-50%, 0); } 50% { transform: translate(-50%, 8px); } }

/* ============ SHARED BITS ============ */
.flag { width: 20px; height: 15px; object-fit: cover; border-radius: 2px;
        outline: 1px solid var(--hairline); vertical-align: -2px; }
.section.cream .flag { outline-color: var(--cream-hairline); }
.btn { font-family: var(--font-sans); font-weight: 700; font-size: 0.9rem;
       background: var(--bg); color: var(--ink); border: 1px solid var(--hairline);
       padding: 12px 24px; border-radius: 10px; cursor: pointer; }
.btn:hover { border-color: var(--gold); color: var(--gold); }
:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
           clip: rect(0 0 0 0); white-space: nowrap; }

/* ============ LOAD ERROR ============ */
.load-error { min-height: 100vh; display: flex; align-items: center; justify-content: center;
              background: var(--bg-deep); padding: 20px; }
.load-error-card { max-width: 420px; text-align: center; border: 1px solid var(--hairline);
                   border-radius: var(--radius); padding: 40px 32px; }
.load-error-card h2 { font-size: 1.6rem; margin: 12px 0; }
.load-error-card p:not(.kicker) { color: var(--ink-dim); line-height: 1.6; margin-bottom: 22px; }

/* ============ FOOTER ============ */
.footer { background: var(--bg-deep); border-top: 1px solid var(--hairline-soft);
          padding: 28px 20px; text-align: center; }
.footer p { font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase;
            color: var(--ink-faint); }

/* ============ MOTION (elements opt in via data-reveal) ============ */
[data-reveal] { opacity: 0; transform: translateY(12px);
                transition: opacity 0.5s ease, transform 0.5s ease;
                transition-delay: calc(var(--stagger, 0) * 70ms); }
[data-reveal].in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  [data-reveal] { opacity: 1; transform: none; transition: none; }
  .hero-title .w { opacity: 1; transform: none; animation: none; }
  .scroll-cue { animation: none; }
}
```

- [ ] **Step 3: Write `assets/app.js`** (loader + hero + shared helpers; section renderers land in Tasks 5–10 inside the marked slots)

```js
import * as D from './derive.js';

export const PLAYER_COLORS = {
  Kenny: '#d9a441', Fiona: '#7ea87f', Alex: '#8fa3c9', Edward: '#c9808f',
};

let FLAG_CODES = {};

export function flagImg(country) {
  const code = FLAG_CODES[country];
  const src = code ? `flags/${code}.svg` : 'flags/_fallback.svg';
  return `<img class="flag" src="${src}" alt="" loading="lazy"
    onerror="this.onerror=null;this.src='flags/_fallback.svg'">`;
}

export function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c]);
}

export function fmtDate(iso) {
  const d = new Date(iso + (iso.length === 10 ? 'T12:00:00Z' : ''));
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export function fmtKickoff(utcISO) {
  const d = new Date(utcISO);
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London',
  }) + ' BST';
}

async function getJSON(path, { optional = false } = {}) {
  try {
    const r = await fetch(`${path}?v=${Date.now()}`);
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    if (optional) return null;
    throw e;
  }
}

function renderHero(scores, participants, status) {
  const ranked = Object.entries(scores.participants)
    .sort((a, b) => b[1].total - a[1].total);
  const leader = ranked[0][0];
  const alive = Object.values(status).filter(s => s.alive).length;
  const lastResult = (scores.recentResults || [])[0];
  const stage = lastResult ? lastResult.stage : 'Group Stage';
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('stat-strip').innerHTML = `
    <div class="stat"><dt>Matchday</dt><dd>${D.matchdayNumber(today)}</dd></div>
    <div class="stat"><dt>Stage</dt><dd>${esc(stage)}</dd></div>
    <div class="stat"><dt>Leader</dt><dd class="gold">${esc(leader)}</dd></div>
    <div class="stat"><dt>Teams alive</dt><dd>${alive}<small>/48</small></dd></div>`;

  // Word-by-word reveal: wrap words, keep the <em> intact
  const h1 = document.getElementById('hero-title');
  let i = 0;
  h1.innerHTML = h1.innerHTML.replace(/(<em[^>]*>.*?<\/em>)|(\S+)/g, (m) =>
    `<span class="w" style="--i:${i++}">${m}</span>`);
}

function renderTopbar(scores) {
  const ranked = Object.entries(scores.participants)
    .sort((a, b) => b[1].total - a[1].total);
  document.getElementById('topbar-scores').innerHTML = ranked
    .map(([n, p]) => `${esc(n[0])} ${p.total}`).join(' · ');
}

function initTopbarBehavior() {
  const topbar = document.getElementById('topbar');
  const hero = document.getElementById('hero');
  new IntersectionObserver(([entry]) => {
    topbar.dataset.hidden = entry.isIntersecting ? 'true' : 'false';
  }, { threshold: 0.05 }).observe(hero);

  const btn = document.getElementById('topbar-menu');
  const nav = document.getElementById('topbar-nav');
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', () => {
    nav.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  });
}

function initReveals() {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('[data-reveal]').forEach(el => io.observe(el));
}

function renderFooter(scores) {
  let updated = '—';
  if (scores.lastRunAt) {
    const d = new Date(scores.lastRunAt);
    updated = d.toLocaleString('en-GB', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      timeZone: 'Europe/London',
    }) + ' BST';
  }
  document.getElementById('footer-line').textContent =
    `Updated ${updated} · Data: football-data.org · Powered by GitHub Pages`;
}

async function main() {
  let scores, participants, rules;
  let fixtures = null;
  try {
    [scores, participants, rules, FLAG_CODES, fixtures] = await Promise.all([
      getJSON('scores.json'),
      getJSON('participants.json'),
      getJSON('scoring-rules.json'),
      getJSON('flag-codes.json'),
      getJSON('fixtures.json', { optional: true }),
    ]);
  } catch (e) {
    console.error(e);
    document.getElementById('load-error').hidden = false;
    return;
  }

  const status = D.teamStatus(scores, participants);
  document.getElementById('app').hidden = false;

  renderTopbar(scores);
  renderHero(scores, participants, status);
  // SECTION RENDERERS — added by later tasks:
  // renderStandings(scores, participants, status);   (Task 5)
  // renderRace(scores);                                (Task 6)
  // renderMatchday(scores, participants, rules, fixtures); (Task 7)
  // renderBracket(scores, participants, fixtures, status); (Task 8)
  // renderSquads(scores, participants, status);       (Task 9)
  // renderRecords(scores);                             (Task 9)
  // renderResults(scores);                             (Task 9)
  renderFooter(scores);

  initTopbarBehavior();
  initReveals();
}

main();
```

- [ ] **Step 4: Create `.nojekyll`** (empty file at repo root)

- [ ] **Step 5: Verify in browser**

Run: `python -m http.server 8010` (from repo root, background)
Browser: `http://localhost:8010` → hero renders, words animate in, stat strip shows `Matchday 23 · Round of 32 · Kenny · 23/48`-style real values (alive count comes from real data). No console errors.
Error drill: `mv scores.json scores.json.bak` → refresh → styled error card; `mv` back.

- [ ] **Step 6: Commit**

```bash
git add index.html assets/styles.css assets/app.js .nojekyll
git commit -m "Add static site shell: data loading, hero, error state"
```

---

### Task 5: Standings section (expandable event logs)

**Goal:** Editorial standings — gold leader card, hairline rows, per-player sparkline, click-to-expand full points log.

**Files:**
- Modify: `assets/app.js` (add `renderStandings`, un-comment its call in `main()`)
- Modify: `assets/styles.css` (append standings block)

**Acceptance Criteria:**
- [ ] Leader card gold-tinted with points-composition bar and "▲ N today" chip when they scored today
- [ ] Rows 2–4 show sparkline of that player's cumulative series
- [ ] Every row is a `<button>`-driven expander (`aria-expanded`, chevron rotates, animated open) revealing the full event log: `+4 · [flag] Spain won the Round of 32 vs Austria · 2 Jul`
- [ ] Log is newest-first and matches `scores.json` log content exactly

**Verify:** browser at `http://localhost:8010#standings` — expand each player, cross-check 2–3 log entries against `scores.json`

**Steps:**

- [ ] **Step 1: Append CSS** to `assets/styles.css`

```css
/* ============ STANDINGS ============ */
.leader-card { background: linear-gradient(120deg, rgba(217, 164, 65, 0.14),
               rgba(217, 164, 65, 0.04) 60%); border: 1px solid rgba(217, 164, 65, 0.3);
               border-radius: var(--radius); margin-bottom: 6px; }
.standing-row { border-bottom: 1px solid var(--hairline-soft); }
.standing-row:last-child { border-bottom: none; }
.standing-head { display: flex; align-items: center; gap: 14px; width: 100%;
                 padding: 16px 18px; background: none; border: none; color: inherit;
                 font: inherit; text-align: left; cursor: pointer; }
.standing-rank { font-family: var(--font-serif); font-style: italic; font-size: 1.35rem;
                 color: var(--ink-faint); width: 24px; flex-shrink: 0; }
.leader-card .standing-rank { color: var(--gold); font-size: 1.6rem; }
.standing-name { font-weight: 800; font-size: 1rem; flex: 1; min-width: 0; }
.standing-meta { font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.16em;
                 text-transform: uppercase; color: var(--ink-dim); display: block;
                 margin-top: 3px; font-weight: 400; }
.standing-spark { flex-shrink: 0; opacity: 0.75; }
.standing-pts { font-family: var(--font-mono); font-size: 1.3rem; font-weight: 600;
                text-align: right; }
.leader-card .standing-pts { color: var(--gold); font-size: 1.5rem; }
.gain-chip { font-family: var(--font-mono); font-size: 0.66rem; color: var(--sage);
             font-weight: 600; display: block; text-align: right; }
.standing-chev { color: var(--ink-faint); transition: transform 0.25s ease; flex-shrink: 0; }
.standing-head[aria-expanded="true"] .standing-chev { transform: rotate(180deg); }
.comp-bar { display: flex; height: 4px; border-radius: 2px; overflow: hidden;
            margin: 0 18px 14px; background: var(--hairline-soft); }
.comp-bar span { height: 100%; }
.standing-body { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.35s ease; }
.standing-body > div { overflow: hidden; }
.standing-body.open { grid-template-rows: 1fr; }
.log-list { padding: 4px 18px 18px; display: flex; flex-direction: column; gap: 9px; }
.log-row { display: flex; align-items: baseline; gap: 10px; font-size: 0.85rem; }
.log-pts { font-family: var(--font-mono); font-weight: 600; font-size: 0.75rem;
           padding: 1px 7px; border-radius: 4px; flex-shrink: 0;
           background: var(--hairline-soft); color: var(--ink); }
.log-pts.big { background: rgba(217, 164, 65, 0.16); color: var(--gold); }
.log-text { flex: 1; min-width: 0; color: var(--ink-dim); overflow-wrap: anywhere; }
.log-text strong { color: var(--ink); font-weight: 700; }
.log-date { font-family: var(--font-mono); font-size: 0.66rem; color: var(--ink-faint);
            flex-shrink: 0; }
@media (prefers-reduced-motion: reduce) {
  .standing-body { transition: none; }
  .standing-chev { transition: none; }
}
```

- [ ] **Step 2: Add renderer to `assets/app.js`** (before `main()`; un-comment the call)

```js
function sparklineSVG(values, color) {
  if (!values.length) return '';
  const max = Math.max(...values, 1);
  const pts = values.map((v, i) =>
    `${(i / Math.max(values.length - 1, 1)) * 64},${18 - (v / max) * 16}`).join(' ');
  return `<svg class="standing-spark" viewBox="0 0 64 20" width="64" height="20"
    aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${color}"
    stroke-width="1.5" stroke-linecap="round"/></svg>`;
}

function logRowHTML(e) {
  const big = e.points >= 4 ? ' big' : '';
  const label = D.EVENT_LABELS[e.event] || e.event;
  const isQual = D.QUALIFY_EVENTS.includes(e.event);
  const opp = e.opponent && !isQual ? ` vs ${esc(e.opponent)}` : '';
  return `<div class="log-row">
    <span class="log-pts${big}">+${e.points}</span>
    <span class="log-text">${flagImg(e.country)} <strong>${esc(e.country)}</strong>
      ${esc(label)}${opp}</span>
    <span class="log-date">${fmtDate(e.date)}</span></div>`;
}

function renderStandings(scores, participants, status) {
  const today = new Date().toISOString().slice(0, 10);
  const { series } = D.cumulativeSeries(scores);
  const ranked = Object.entries(scores.participants)
    .sort((a, b) => b[1].total - a[1].total);

  const rows = ranked.map(([name, p], idx) => {
    const rank = idx + 1;
    const isLeader = rank === 1;
    const aliveCount = Object.keys(p.countries)
      .filter(c => status[c] && status[c].alive).length;
    const todayGain = (p.log || []).filter(e => e.date === today)
      .reduce((s, e) => s + e.points, 0);
    const log = [...(p.log || [])].sort((a, b) => b.date.localeCompare(a.date));

    // Composition bar: share of points per round bucket (group+qual vs knockout)
    const grpPts = (p.log || []).filter(e => !D.KNOCKOUT_EVENTS.includes(e.event))
      .reduce((s, e) => s + e.points, 0);
    const koPts = p.total - grpPts;
    const compBar = isLeader && p.total > 0 ? `<div class="comp-bar" aria-hidden="true">
        <span style="width:${(grpPts / p.total) * 100}%;background:var(--terra-deep)"></span>
        <span style="width:${(koPts / p.total) * 100}%;background:var(--gold)"></span>
      </div>` : '';

    return `<div class="standing-row ${isLeader ? 'leader-card' : ''}" data-reveal
        style="--stagger:${idx}">
      <button class="standing-head" aria-expanded="false" aria-controls="log-${rank}">
        <span class="standing-rank" aria-hidden="true">${rank}</span>
        <span class="standing-name">${esc(name)}
          <span class="standing-meta">${aliveCount} of ${Object.keys(p.countries).length} teams alive</span>
        </span>
        ${!isLeader ? sparklineSVG(series[name] || [], PLAYER_COLORS[name] || '#888') : ''}
        <span class="standing-pts">${p.total}
          ${todayGain > 0 ? `<span class="gain-chip">▲ ${todayGain} today</span>` : ''}
        </span>
        <svg class="standing-chev" viewBox="0 0 24 24" width="16" height="16" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M6 9l6 6 6-6"/></svg>
      </button>
      ${compBar}
      <div class="standing-body" id="log-${rank}">
        <div><div class="log-list">
          ${log.length ? log.map(logRowHTML).join('') :
            '<p class="log-text">No points yet.</p>'}
        </div></div>
      </div>
    </div>`;
  }).join('');

  document.getElementById('standings-root').innerHTML = `
    <div class="section-head">
      <h2 class="section-title">The <em>standings</em></h2>
      <span class="kicker" style="color:var(--ink-faint)">Leaderboard</span>
    </div>${rows}`;

  document.querySelectorAll('.standing-head').forEach(btn => {
    btn.addEventListener('click', () => {
      const body = document.getElementById(btn.getAttribute('aria-controls'));
      const open = body.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
  });
}
```

In `main()`, replace the comment line with `renderStandings(scores, participants, status);`

- [ ] **Step 3: Verify in browser** — expand all four players; confirm totals (Kenny 89 etc.), a `+4 Spain won the Round of 32 vs Austria` entry under Kenny, chevron rotation, keyboard operability (Tab + Enter).

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "Add standings section with expandable event logs"
```

---

### Task 6: Points race chart

**Goal:** Cumulative SVG line chart that draws on scroll, with annotations, filters, and hover/tap player highlight.

**Files:**
- Modify: `assets/app.js` (add `renderRace` + call)
- Modify: `assets/styles.css` (append race block)

**Acceptance Criteria:**
- [ ] One line per player in identity colors; end labels `Kenny · 89`
- [ ] Lines animate via stroke-dashoffset when scrolled into view (skipped under reduced motion)
- [ ] Two largest single-day swings annotated (`SPAIN WIN R32 · +4` style, terracotta mono)
- [ ] Filter chips All / Group stage / Knockouts re-render the chart
- [ ] Hovering/tapping a legend chip dims other lines
- [ ] sr-only table mirrors final totals per player

**Verify:** browser at `#race` — draw animation runs once, filters change the lines, annotation text matches real data

**Steps:**

- [ ] **Step 1: Append CSS**

```css
/* ============ POINTS RACE ============ */
.race-svg { width: 100%; height: auto; display: block; }
.race-line { transition: opacity 0.25s ease; }
.race-svg.dimming .race-line:not(.hot) { opacity: 0.18; }
.race-svg .draw { stroke-dasharray: var(--len); stroke-dashoffset: var(--len);
                  transition: stroke-dashoffset 1.2s ease-out; }
.race-svg.in .draw { stroke-dashoffset: 0; }
.race-anno { font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.08em;
             fill: var(--terra); }
.race-axis { font-family: var(--font-mono); font-size: 9px; fill: var(--ink-faint); }
.race-chips { display: flex; gap: 8px; margin-top: 18px; flex-wrap: wrap; }
.race-chip { font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.18em;
             text-transform: uppercase; padding: 7px 14px; border-radius: 999px;
             border: 1px solid transparent; background: none; color: var(--ink-faint);
             cursor: pointer; }
.race-chip[aria-pressed="true"] { background: var(--hairline-soft);
             border-color: var(--hairline); color: var(--ink); }
.race-legend { display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap; }
.race-key { display: flex; align-items: center; gap: 7px; font-size: 0.78rem;
            color: var(--ink-dim); background: none; border: none; cursor: pointer;
            font-family: var(--font-sans); }
.race-key i { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
@media (prefers-reduced-motion: reduce) {
  .race-svg .draw { stroke-dasharray: none; stroke-dashoffset: 0; transition: none; }
}
```

- [ ] **Step 2: Add renderer** to `assets/app.js`

```js
let raceFilter = 'all';

function biggestSwings(scores, n = 2) {
  const evs = D.allEvents(scores).filter(e => e.points >= 4);
  return [...evs].sort((a, b) => b.points - a.points).slice(0, n);
}

function renderRace(scores) {
  const root = document.getElementById('race-root');
  const { dates, series } = D.cumulativeSeries(scores, raceFilter);
  const players = Object.keys(series);
  const W = 640, H = 240, PAD_L = 34, PAD_B = 22, PAD_T = 26, PAD_R = 74;
  const maxVal = Math.max(1, ...players.flatMap(p => series[p]));
  const x = i => PAD_L + (i / Math.max(dates.length - 1, 1)) * (W - PAD_L - PAD_R);
  const y = v => H - PAD_B - (v / maxVal) * (H - PAD_B - PAD_T);

  const lines = players.map(p => {
    const pts = series[p].map((v, i) => `${x(i)},${y(v)}`).join(' ');
    const end = series[p].at(-1) ?? 0;
    return `<g class="race-line" data-player="${esc(p)}">
      <polyline class="draw" points="${pts}" fill="none"
        stroke="${PLAYER_COLORS[p]}" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="${x(series[p].length - 1)}" cy="${y(end)}" r="3" fill="${PLAYER_COLORS[p]}"/>
      <text class="race-axis" x="${x(series[p].length - 1) + 7}" y="${y(end) + 3}"
        fill="${PLAYER_COLORS[p]}">${esc(p)} · ${end}</text></g>`;
  }).join('');

  const annos = raceFilter === 'all' ? biggestSwings(scores).map(e => {
    const di = dates.indexOf(e.date);
    if (di < 0) return '';
    const val = series[e.owner][di];
    const stageShort = { LAST_32_WIN: 'R32', LAST_16_WIN: 'R16', QUARTER_FINALS_WIN: 'QF',
      SEMI_FINALS_WIN: 'SF', THIRD_PLACE_WIN: '3RD', FINAL_WIN: 'FINAL' }[e.event] || 'GRP';
    return `<line x1="${x(di)}" y1="${y(val)}" x2="${x(di)}" y2="${PAD_T - 8}"
        stroke="rgba(201,138,91,0.45)" stroke-width="1" stroke-dasharray="2,3"/>
      <text class="race-anno" x="${Math.min(x(di), W - 150)}" y="${PAD_T - 12}">
        ${esc(e.country.toUpperCase())} ${stageShort} · +${e.points}</text>`;
  }).join('') : '';

  const gridY = [0, Math.round(maxVal / 2), maxVal];
  const grid = gridY.map(v => `<line x1="${PAD_L}" y1="${y(v)}" x2="${W - PAD_R}" y2="${y(v)}"
      stroke="var(--hairline-soft)" stroke-width="1"/>
    <text class="race-axis" x="${PAD_L - 6}" y="${y(v) + 3}" text-anchor="end">${v}</text>`).join('');
  const xLabels = dates.length ? `<text class="race-axis" x="${PAD_L}" y="${H - 6}">${fmtDate(dates[0]).toUpperCase()}</text>
    <text class="race-axis" x="${W - PAD_R}" y="${H - 6}" text-anchor="end">${fmtDate(dates.at(-1)).toUpperCase()}</text>` : '';

  root.innerHTML = `
    <div class="section-head">
      <h2 class="section-title">The points <em>race</em></h2>
      <span class="kicker terra">The story so far</span>
    </div>
    <svg class="race-svg" viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Cumulative points per player over the tournament">
      ${grid}${xLabels}${annos}${lines}</svg>
    <div class="race-legend">${players.map(p =>
      `<button class="race-key" data-player="${esc(p)}">
        <i style="background:${PLAYER_COLORS[p]}"></i>${esc(p)}</button>`).join('')}</div>
    <div class="race-chips" role="group" aria-label="Filter chart">
      ${[['all', 'All'], ['group', 'Group stage'], ['knockout', 'Knockouts']].map(([k, lbl]) =>
        `<button class="race-chip" data-filter="${k}"
          aria-pressed="${k === raceFilter}">${lbl}</button>`).join('')}</div>
    <table class="sr-only"><caption>Current totals</caption>
      ${Object.entries(scores.participants).map(([n, p]) =>
        `<tr><th scope="row">${esc(n)}</th><td>${p.total} points</td></tr>`).join('')}</table>`;

  const svg = root.querySelector('.race-svg');
  svg.querySelectorAll('.draw').forEach(pl => {
    const len = pl.getTotalLength();
    pl.style.setProperty('--len', len);
  });
  new IntersectionObserver(([e], io) => {
    if (e.isIntersecting) { svg.classList.add('in'); io.disconnect(); }
  }, { threshold: 0.3 }).observe(svg);

  root.querySelectorAll('.race-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      raceFilter = chip.dataset.filter;
      renderRace(scores);
      root.querySelector('.race-svg').classList.add('in');
    });
  });
  root.querySelectorAll('.race-key').forEach(key => {
    const hot = () => {
      svg.classList.add('dimming');
      svg.querySelectorAll('.race-line').forEach(l =>
        l.classList.toggle('hot', l.dataset.player === key.dataset.player));
    };
    const cool = () => {
      svg.classList.remove('dimming');
      svg.querySelectorAll('.race-line').forEach(l => l.classList.remove('hot'));
    };
    key.addEventListener('mouseenter', hot);
    key.addEventListener('mouseleave', cool);
    key.addEventListener('focus', hot);
    key.addEventListener('blur', cool);
  });
}
```

In `main()`, replace the comment with `renderRace(scores);`

- [ ] **Step 3: Verify in browser** — scroll to `#race`; lines draw; switch filters; hover legend keys; check Kenny's line ends at 89 on "All".

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "Add scroll-drawn points race chart with filters and annotations"
```

---

### Task 7: Matchday timeline (cream section)

**Goal:** Today/next fixtures as a vertical timeline with kickoff chips and family-stake lines; falls back to recent results without fixtures data.

**Files:**
- Modify: `assets/app.js` (add `renderMatchday` + call)
- Modify: `assets/styles.css` (append matchday block)

**Acceptance Criteria:**
- [ ] With `fixtures.json` present: up to 4 upcoming fixtures, kickoff shown in BST, stake sentence per fixture (derby / head-to-head), owner identity-color dots
- [ ] Without fixtures (rename file to test): section shows the 4 most recent results with the same layout, header switches to "Latest results"
- [ ] Cream section styling matches spec (parchment bg, dark ink, terracotta accents)

**Verify:** browser at `#matchday` with and without `fixtures.json` present

**Steps:**

- [ ] **Step 1: Append CSS**

```css
/* ============ MATCHDAY (cream) ============ */
.timeline { border-left: 2px solid var(--cream-hairline); padding-left: 22px;
            display: flex; flex-direction: column; gap: 22px; margin-top: 6px; }
.timeline-item { position: relative; }
.timeline-item::before { content: ''; position: absolute; left: -28px; top: 5px;
            width: 10px; height: 10px; border-radius: 50%; background: var(--dot, var(--sage)); }
.timeline-when { font-family: var(--font-mono); font-size: 0.64rem; letter-spacing: 0.18em;
            text-transform: uppercase; color: var(--cream-dim); font-weight: 600; }
.timeline-tie { font-weight: 800; font-size: 1.05rem; margin-top: 3px;
            display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.timeline-score { font-family: var(--font-mono); font-weight: 600; }
.timeline-stake { font-size: 0.85rem; color: var(--cream-dim); margin-top: 3px;
            line-height: 1.5; }
.owner-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
```

- [ ] **Step 2: Add renderer**

```js
function ownerDot(owner) {
  return owner ? `<span class="owner-dot" title="${esc(owner)}"
    style="background:${PLAYER_COLORS[owner] || '#888'}"></span>` : '';
}

function renderMatchday(scores, participants, rules, fixtures) {
  const owners = participants.countryToOwner;
  const nowISO = new Date().toISOString();
  const upcoming = D.upcomingFixtures(fixtures, nowISO, 4);
  const root = document.getElementById('matchday-root');
  const today = new Date().toISOString().slice(0, 10);

  let title, kicker, items;
  if (upcoming.length) {
    title = `Matchday <em>${D.matchdayNumber(today)}</em>`;
    kicker = `Next up`;
    items = upcoming.map((f, i) => {
      const stake = D.fixtureStakes(f, owners, rules);
      const dotOwner = owners[f.homeTeam] || owners[f.awayTeam];
      return `<div class="timeline-item" data-reveal style="--stagger:${i};
          --dot:${PLAYER_COLORS[dotOwner] || 'var(--sage)'}">
        <div class="timeline-when">${fmtKickoff(f.utcDate)} ·
          ${esc(D.STAGE_LABELS[f.stage] || f.stage)} · ${fmtDate(f.utcDate.slice(0, 10))}</div>
        <div class="timeline-tie">${ownerDot(owners[f.homeTeam])} ${flagImg(f.homeTeam)}
          ${esc(f.homeTeam)} <span class="timeline-score">v</span>
          ${esc(f.awayTeam)} ${flagImg(f.awayTeam)} ${ownerDot(owners[f.awayTeam])}</div>
        <div class="timeline-stake">${esc(stake)}</div></div>`;
    }).join('');
  } else {
    title = `Latest <em>results</em>`;
    kicker = 'Fixtures unavailable';
    items = (scores.recentResults || []).slice(0, 4).map((r, i) =>
      `<div class="timeline-item" data-reveal style="--stagger:${i};
          --dot:${PLAYER_COLORS[owners[r.homeTeam]] || 'var(--sage)'}">
        <div class="timeline-when">${esc(r.stage)} · ${fmtDate(r.date)}</div>
        <div class="timeline-tie">${ownerDot(owners[r.homeTeam])} ${flagImg(r.homeTeam)}
          ${esc(r.homeTeam)} <span class="timeline-score">${r.homeScore ?? '–'}–${r.awayScore ?? '–'}</span>
          ${esc(r.awayTeam)} ${flagImg(r.awayTeam)} ${ownerDot(owners[r.awayTeam])}</div>
      </div>`).join('');
  }

  root.innerHTML = `<div class="section-head">
      <h2 class="section-title">${title}</h2>
      <span class="kicker" style="color:var(--terra-deep)">${esc(kicker)}</span>
    </div><div class="timeline">${items}</div>`;
}
```

In `main()`, replace the comment with `renderMatchday(scores, participants, rules, fixtures);`

- [ ] **Step 3: Verify in browser** — fixtures present: stake lines correct (spot-check a same-owner fixture if one exists); rename `fixtures.json` locally → fallback shows recent results; restore.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "Add matchday timeline with family stakes and results fallback"
```

---

### Task 8: Knockout bracket

**Goal:** Horizontally scrollable R32→Final columns with flags, owner dots, winners bold, losers faded, gold champion slot.

**Files:**
- Modify: `assets/app.js` (add `renderBracket` + call)
- Modify: `assets/styles.css` (append bracket block)

**Acceptance Criteria:**
- [ ] Six columns (R32, R16, QF, SF, 3rd place, Final) with 16/8/4/2/1/1 tie cards
- [ ] Played ties: winner bold with identity dot, loser faded; upcoming ties from fixtures show kickoff date; unknown ties show TBD
- [ ] Champion slot after the Final column: gold-outlined, empty ("To be won") until a FINAL_WIN event exists
- [ ] Column area scrolls horizontally inside its own container on small screens

**Verify:** browser at `#bracket` — R32 column shows real played ties (e.g. Portugal beat Croatia), horizontal scroll works at mobile width

**Steps:**

- [ ] **Step 1: Append CSS**

```css
/* ============ BRACKET ============ */
.bracket-scroll { overflow-x: auto; padding-bottom: 12px; }
.bracket { display: flex; gap: 18px; min-width: max-content; align-items: flex-start; }
.bracket-col { width: 190px; flex-shrink: 0; }
.bracket-col h3 { font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.2em;
            text-transform: uppercase; color: var(--ink-faint); font-weight: 600;
            margin-bottom: 10px; }
.tie { border: 1px solid var(--hairline); border-radius: 10px; padding: 8px 10px;
       margin-bottom: 8px; background: var(--bg-deep); }
.tie-team { display: flex; align-items: center; gap: 7px; font-size: 0.8rem;
            padding: 3px 0; color: var(--ink-dim); }
.tie-team.won { color: var(--ink); font-weight: 800; }
.tie-team.lost { opacity: 0.38; }
.tie-team .flag { width: 18px; height: 13px; }
.tie-when { font-family: var(--font-mono); font-size: 0.58rem; color: var(--ink-faint);
            letter-spacing: 0.12em; text-transform: uppercase; margin-top: 4px; }
.champion-slot { width: 190px; flex-shrink: 0; border: 1.5px solid var(--gold);
            border-radius: var(--radius); padding: 18px 14px; text-align: center;
            align-self: center; }
.champion-slot .kicker { color: var(--gold); margin-bottom: 8px; }
.champion-name { font-family: var(--font-serif); font-size: 1.15rem; font-style: italic; }
```

- [ ] **Step 2: Add renderer**

```js
function renderBracket(scores, participants, fixtures, status) {
  const owners = participants.countryToOwner;
  const rounds = D.bracketData(scores, fixtures);
  const finalWin = D.allEvents(scores).find(e => e.event === 'FINAL_WIN');

  const teamRow = (team, tie) => {
    const cls = tie.winner ? (tie.winner === team ? 'won' : 'lost') : '';
    const known = team && team !== 'TBD';
    return `<div class="tie-team ${cls}">
      ${known ? ownerDot(owners[team]) : ''} ${known ? flagImg(team) : ''}
      <span>${esc(team || 'TBD')}</span></div>`;
  };

  const cols = rounds.map(r => `<div class="bracket-col">
      <h3>${esc(r.label)}</h3>
      ${r.ties.map(t => `<div class="tie">
        ${teamRow(t.home, t)}${teamRow(t.away, t)}
        ${t.utcDate ? `<div class="tie-when">${fmtDate(t.utcDate.slice(0, 10))} ·
          ${fmtKickoff(t.utcDate)}</div>` : ''}
      </div>`).join('')}</div>`).join('');

  document.getElementById('bracket-root').innerHTML = `
    <div class="section-head">
      <h2 class="section-title">The <em>road</em> to the final</h2>
      <span class="kicker" style="color:var(--ink-faint)">Knockouts</span>
    </div>
    <div class="bracket-scroll"><div class="bracket">
      ${cols}
      <div class="champion-slot">
        <p class="kicker">Champion</p>
        <p class="champion-name">${finalWin ?
          `${flagImg(finalWin.country)} ${esc(finalWin.country)}` : 'To be won'}</p>
        ${finalWin ? `<p class="tie-when">${esc(finalWin.owner)} takes the sweepstake glory</p>` : ''}
      </div>
    </div></div>`;
}
```

In `main()`, replace the comment with `renderBracket(scores, participants, fixtures, status);`

- [ ] **Step 3: Verify in browser** — R32 column: Portugal bold / Croatia faded with owner dots; Switzerland bold / Algeria faded; upcoming ties show dates; champion slot reads "To be won"; DevTools mobile width → horizontal scroll confined to bracket.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "Add knockout bracket with owner dots and champion slot"
```

---

### Task 9: Squad explorer, records, recent results, footer polish

**Goal:** Remaining content sections: accordion squads with per-team points, stat-card records, restyled recent results.

**Files:**
- Modify: `assets/app.js` (add `renderSquads`, `renderRecords`, `renderResults` + calls)
- Modify: `assets/styles.css` (append blocks)

**Acceptance Criteria:**
- [ ] Squads: one accordion panel per player (one open at a time); each of the 12 countries shows flag, name, points contributed (e.g. "Cape Verde · 10"); eliminated teams struck through + desaturated; alive/out counts in the header
- [ ] Clicking a country in a squad scrolls to standings, opens that owner's log, and briefly highlights that team's entries
- [ ] Records: four stat cards (Biggest single day / Most valuable team / Knockout king / Sharpest rise) with huge serif numbers, staggered reveal
- [ ] Recent results: last 10 with flags + stage chips

**Verify:** browser — accordion behavior, Cape Verde shows Fiona's actual total for it, records values match `node --test` derivations

**Steps:**

- [ ] **Step 1: Append CSS**

```css
/* ============ SQUADS ============ */
.squad { border: 1px solid var(--hairline); border-radius: var(--radius);
         margin-bottom: 10px; overflow: hidden; }
.squad-head { display: flex; align-items: center; gap: 12px; width: 100%;
              padding: 14px 18px; background: rgba(232, 230, 223, 0.04); border: none;
              color: inherit; font: inherit; cursor: pointer; text-align: left; }
.squad-name { font-weight: 800; font-size: 0.95rem; flex: 1; }
.squad-counts { font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.14em;
              text-transform: uppercase; }
.squad-counts .alive { color: var(--sage); } .squad-counts .out { color: var(--ink-faint); }
.squad-body { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.35s ease; }
.squad-body > div { overflow: hidden; }
.squad-body.open { grid-template-rows: 1fr; }
.squad-grid { padding: 14px 18px; display: grid;
              grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px 20px;
              border-top: 1px solid var(--hairline-soft); }
.squad-team { display: flex; align-items: center; gap: 9px; font-size: 0.85rem;
              background: none; border: none; color: var(--ink); cursor: pointer;
              font-family: var(--font-sans); padding: 3px 0; text-align: left; }
.squad-team .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
              white-space: nowrap; }
.squad-team.out { opacity: 0.38; }
.squad-team.out .name { text-decoration: line-through; }
.squad-team.out .flag { filter: grayscale(1); }
.squad-team .pts { font-family: var(--font-mono); font-size: 0.78rem; color: var(--gold); }
.squad-team.out .pts { color: var(--ink-faint); }
.log-row.hl { background: rgba(217, 164, 65, 0.12); border-radius: 6px; }

/* ============ RECORDS (cream) ============ */
.records-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 14px; }
.record-card { background: #fff; border: 1px solid var(--cream-hairline); border-radius: 12px;
               padding: 18px 16px; }
.record-num { font-family: var(--font-serif); font-size: 2.4rem; font-weight: 600;
              color: var(--cream-ink); line-height: 1; }
.record-num small { font-size: 1rem; color: var(--terra-deep); }
.record-cap { font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.16em;
              text-transform: uppercase; color: var(--cream-dim); margin-top: 8px;
              line-height: 1.7; }

/* ============ RESULTS ============ */
.result-line { display: flex; align-items: center; gap: 10px; padding: 11px 4px;
               border-bottom: 1px solid var(--hairline-soft); font-size: 0.88rem; }
.result-line:last-child { border-bottom: none; }
.result-line .home { flex: 1; text-align: right; display: flex; justify-content: flex-end;
               align-items: center; gap: 8px; min-width: 0; }
.result-line .away { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
.result-line .score { font-family: var(--font-mono); font-weight: 600; color: var(--gold);
               white-space: nowrap; }
.result-line .stage-chip { font-family: var(--font-mono); font-size: 0.56rem;
               letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-faint);
               border: 1px solid var(--hairline); border-radius: 999px; padding: 2px 8px;
               white-space: nowrap; }
@media (max-width: 560px) { .result-line .stage-chip { display: none; } }
```

- [ ] **Step 2: Add the three renderers**

```js
function renderSquads(scores, participants, status) {
  const ranked = Object.entries(scores.participants)
    .sort((a, b) => b[1].total - a[1].total);
  const panels = ranked.map(([name, p], idx) => {
    const teams = Object.entries(p.countries);
    const alive = teams.filter(([c]) => status[c]?.alive).length;
    const rows = teams
      .sort((a, b) => b[1].points - a[1].points)
      .map(([c, cd]) => `<button class="squad-team ${status[c]?.alive ? '' : 'out'}"
          data-owner="${esc(name)}" data-country="${esc(c)}">
        ${flagImg(c)} <span class="name">${esc(c)}</span>
        <span class="pts">${cd.points}</span></button>`).join('');
    return `<div class="squad" data-reveal style="--stagger:${idx}">
      <button class="squad-head" aria-expanded="false" aria-controls="squad-${idx}">
        <span class="owner-dot" style="background:${PLAYER_COLORS[name]}"></span>
        <span class="squad-name">${esc(name)}'s twelve</span>
        <span class="squad-counts"><span class="alive">${alive} alive</span> ·
          <span class="out">${teams.length - alive} out</span></span>
        <svg class="standing-chev" viewBox="0 0 24 24" width="16" height="16" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M6 9l6 6 6-6"/></svg>
      </button>
      <div class="squad-body" id="squad-${idx}"><div>
        <div class="squad-grid">${rows}</div></div></div></div>`;
  }).join('');

  document.getElementById('squads-root').innerHTML = `
    <div class="section-head">
      <h2 class="section-title">The <em>squads</em></h2>
      <span class="kicker" style="color:var(--ink-faint)">Who owns whom</span>
    </div>${panels}`;

  const heads = document.querySelectorAll('.squad-head');
  heads.forEach(btn => btn.addEventListener('click', () => {
    heads.forEach(other => {
      const body = document.getElementById(other.getAttribute('aria-controls'));
      const open = other === btn && other.getAttribute('aria-expanded') !== 'true';
      body.classList.toggle('open', open);
      other.setAttribute('aria-expanded', String(open));
    });
  }));

  document.querySelectorAll('.squad-team').forEach(btn =>
    btn.addEventListener('click', () => {
      const owner = btn.dataset.owner, country = btn.dataset.country;
      const ranked2 = Object.entries(scores.participants)
        .sort((a, b) => b[1].total - a[1].total);
      const rank = ranked2.findIndex(([n]) => n === owner) + 1;
      const head = document.querySelector(`.standing-head[aria-controls="log-${rank}"]`);
      const body = document.getElementById(`log-${rank}`);
      body.classList.add('open');
      head.setAttribute('aria-expanded', 'true');
      head.scrollIntoView({ behavior: 'smooth', block: 'start' });
      body.querySelectorAll('.log-row').forEach(row => {
        if (row.textContent.includes(country)) {
          row.classList.add('hl');
          setTimeout(() => row.classList.remove('hl'), 2600);
        }
      });
    }));
}

function renderRecords(scores) {
  const r = D.records(scores);
  const cards = [
    { num: `+${r.biggestDay.points}`, cap: `Biggest single day —
        ${esc(r.biggestDay.owner)}, ${fmtDate(r.biggestDay.date || '2026-06-11')}` },
    { num: `${r.mostValuableTeam.points}`, cap: `Most valuable team —
        ${esc(r.mostValuableTeam.country)} (${esc(r.mostValuableTeam.owner)})` },
    { num: `${r.knockoutKing.points}`, cap: `Knockout king —
        ${esc(r.knockoutKing.owner)}, knockout points` },
    { num: `+${r.sharpestRise.points}`, cap: `Sharpest rise —
        ${esc(r.sharpestRise.owner)}, three matchdays` },
  ];
  document.getElementById('records-root').innerHTML = `
    <div class="section-head">
      <h2 class="section-title">The record <em>books</em></h2>
      <span class="kicker" style="color:var(--terra-deep)">Tournament so far</span>
    </div>
    <div class="records-grid">${cards.map((c, i) =>
      `<div class="record-card" data-reveal style="--stagger:${i}">
        <div class="record-num">${c.num}</div>
        <div class="record-cap">${c.cap}</div></div>`).join('')}</div>`;
}

function renderResults(scores) {
  const rows = (scores.recentResults || []).map(r => `<div class="result-line">
      <span class="home">${esc(r.homeTeam)} ${flagImg(r.homeTeam)}</span>
      <span class="score">${r.homeScore ?? '–'} – ${r.awayScore ?? '–'}</span>
      <span class="away">${flagImg(r.awayTeam)} ${esc(r.awayTeam)}</span>
      <span class="stage-chip">${esc(r.stage)}</span></div>`).join('');
  document.getElementById('results-root').innerHTML = `
    <div class="section-head">
      <h2 class="section-title">Recent <em>results</em></h2>
      <span class="kicker" style="color:var(--ink-faint)">Last ten</span>
    </div>${rows || '<p class="log-text">No results yet.</p>'}`;
}
```

In `main()`, replace the remaining comments with the three calls.

- [ ] **Step 3: Verify in browser** — accordion one-at-a-time; Fiona's Cape Verde points match `scores.json`; clicking Cape Verde scrolls to Fiona's log and highlights entries; records cards render; results list matches previous site data.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "Add squads, records, and recent results sections"
```

---

### Task 10: Cross-cutting polish pass (motion, responsive, a11y)

**Goal:** Systematic verification and fixes across devices and accessibility, now all sections exist.

**Files:**
- Modify: `assets/styles.css` / `assets/app.js` / `index.html` (fixes only)

**Acceptance Criteria:**
- [ ] Mobile 375px: no horizontal page scroll (bracket scrolls internally), topbar dropdown works, tap targets ≥ 40px
- [ ] Keyboard-only walkthrough: every expander/chip/menu reachable and operable, visible focus
- [ ] `prefers-reduced-motion`: no animations, content all visible immediately
- [ ] All `data-reveal` elements appear on scroll exactly once; nothing stays invisible if IntersectionObserver misses (add a 3s failsafe that adds `.in` to all)
- [ ] No console errors or 404s in Network tab (all flags resolve)

**Verify:** browser DevTools — device toolbar at 375px, "Emulate CSS prefers-reduced-motion", keyboard-only navigation, Network tab filter for 404s

**Steps:**

- [ ] **Step 1: Add the reveal failsafe** to `initReveals()` in `assets/app.js`:

```js
  setTimeout(() =>
    document.querySelectorAll('[data-reveal]:not(.in)')
      .forEach(el => el.classList.add('in')), 3000);
```

- [ ] **Step 2: Run the four verification sweeps** listed in the AC. Fix whatever they surface directly in the three files (spacing overflows, missing focus styles, flag 404s from name mismatches — check every country in `participants.json` resolves via `flag-codes.json`).

- [ ] **Step 3: Re-run unit tests** (regression): `node --test tests/derive.test.mjs` → pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Polish pass: responsive, keyboard, reduced-motion, reveal failsafe"
```

---

### Task 11: Daily email redesign

**Goal:** Rewrite `build_email_html()` and the subject line in the Tournament Editorial brand; add "today's stakes"; add a `--test` flag for safe solo sends. Send/tracking logic otherwise unchanged.

**Files:**
- Modify: `send_digest.py` (replace `build_email_html`, `RANK_EMOJI`, `COUNTRY_FLAGS`, `EVENT_LABELS` usage, subject; add `--test` flag and fixtures/stakes helpers)
- Test: `tests/test_send_digest.py`

**Acceptance Criteria:**
- [ ] Zero emoji in HTML and subject (regex-verified in tests)
- [ ] Table-based, inline styles only; Georgia/serif + Courier/mono stacks; brand colors `#0b120d`/`#f2efe6`/`#d9a441`/`#c98a5b`
- [ ] Standings show leader on gold tint with "▲ N today"; gap-to-leader line under header; flags as `<img>` from `SITE_URL/flags/png/<code>.png` with alt text
- [ ] "Today's stakes" block renders when `fixtures.json` has fixtures for today (London time), silently omitted otherwise
- [ ] Subject: `Sweepstake — {leader} leads by {gap} (Matchday {N})`, or `Sweepstake — {A} and {B} level at the top (Matchday {N})` when tied
- [ ] `python send_digest.py --test` sends ONLY to `GMAIL_SENDER` and does NOT update `emailedEvents`/`lastEmailAt`; normal runs behave exactly as before

**Verify:** `python -m pytest tests/test_send_digest.py -v` → pass; render preview file opens correctly in browser

**Steps:**

- [ ] **Step 1: Write failing tests** — `tests/test_send_digest.py`

```python
import re
import send_digest as sd

SCORES = {
    "participants": {
        "Kenny": {"total": 89, "countries": {"Spain": {"points": 18}},
                  "log": [{"country": "Spain", "event": "LAST_32_WIN", "points": 4,
                           "date": "2026-07-02", "opponent": "Austria", "matchId": 1}]},
        "Fiona": {"total": 74, "countries": {}, "log": []},
        "Alex": {"total": 60, "countries": {}, "log": []},
        "Edward": {"total": 59, "countries": {}, "log": []},
    },
}
NEW_EVENTS = [{"owner": "Kenny", "country": "Spain", "event": "LAST_32_WIN",
               "points": 4, "date": "2026-07-02", "opponent": "Austria", "matchId": 1}]
FLAG_CODES = {"Spain": "es", "Austria": "at", "England": "gb-eng", "Japan": "jp"}
FIXTURES = {"fixtures": [{"matchId": 9, "homeTeam": "England", "awayTeam": "Japan",
                          "utcDate": "2026-07-03T16:00:00Z", "stage": "LAST_32"}]}
OWNERS = {"England": "Fiona", "Japan": "Fiona", "Spain": "Kenny", "Austria": "Alex"}

EMOJI_RX = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⚽]")

def _html(**kw):
    return sd.build_email_html(SCORES, NEW_EVENTS, flag_codes=FLAG_CODES,
                               fixtures=FIXTURES, owners=OWNERS, **kw)

def test_no_emoji_anywhere():
    html = _html()
    assert not EMOJI_RX.search(html)
    assert not EMOJI_RX.search(sd.build_subject(SCORES))

def test_brand_and_content():
    html = _html()
    assert "#0b120d" in html
    assert "Kenny" in html and "89" in html
    assert "flags/png/es.png" in html
    assert "won the Round of 32" in html

def test_gap_line_and_subject():
    assert "leads by 15" in sd.build_subject(SCORES)
    assert "Matchday" in sd.build_subject(SCORES)

def test_stakes_block_present_and_absent():
    assert "England" in _html(today="2026-07-03")
    html_no = sd.build_email_html(SCORES, NEW_EVENTS, flag_codes=FLAG_CODES,
                                  fixtures=None, owners=OWNERS, today="2026-07-03")
    assert "stake" not in html_no.lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_send_digest.py -v`
Expected: FAIL (`build_subject` doesn't exist, signature mismatch)

- [ ] **Step 3: Rewrite the presentation half of `send_digest.py`.** Delete `RANK_EMOJI` and `COUNTRY_FLAGS`; keep `event_key`, `all_log_events`, `new_events_since_last_email`, `record_emailed`, `format_day`, `send_email` EXACTLY as they are. Replace `EVENT_LABELS`, `build_email_html`, and `main` per below.

```python
EVENT_LABELS = {
    "GROUP_STAGE_WIN": "won in the Group Stage",
    "GROUP_STAGE_DRAW": "drew in the Group Stage",
    "QUALIFY_TOP_2": "qualified from the group (top 2)",
    "QUALIFY_BEST_THIRD": "qualified as a best third",
    "LAST_32_WIN": "won the Round of 32",
    "LAST_16_WIN": "won the Round of 16",
    "QUARTER_FINALS_WIN": "won the Quarter-Final",
    "SEMI_FINALS_WIN": "won the Semi-Final",
    "THIRD_PLACE_WIN": "won the 3rd Place Play-off",
    "FINAL_WIN": "won the World Cup Final",
}

STAGE_LABELS = {
    "GROUP_STAGE": "Group Stage", "LAST_32": "Round of 32", "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-Final", "SEMI_FINALS": "Semi-Final",
    "THIRD_PLACE": "3rd Place Play-off", "FINAL": "Final",
}

TOURNAMENT_START = "2026-06-11"

INK, CREAM, GOLD, TERRA, DEEP = "#22301f", "#f2efe6", "#d9a441", "#c98a5b", "#0b120d"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,'Segoe UI',Arial,sans-serif"
MONO = "'Courier New',Courier,monospace"


def matchday_number(date_iso):
    from datetime import date
    d0 = date.fromisoformat(TOURNAMENT_START)
    d1 = date.fromisoformat(date_iso)
    return max(1, (d1 - d0).days + 1)


def build_subject(scores, today=None):
    from datetime import datetime, timezone
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ranked = sorted(scores["participants"].items(), key=lambda x: x[1]["total"], reverse=True)
    md = matchday_number(today)
    (n1, p1), (n2, p2) = ranked[0], ranked[1]
    gap = p1["total"] - p2["total"]
    if gap == 0:
        return f"Sweepstake — {n1} and {n2} level at the top (Matchday {md})"
    return f"Sweepstake — {n1} leads by {gap} (Matchday {md})"


def _flag_img(country, flag_codes):
    code = flag_codes.get(country)
    if not code:
        return ""
    return (f'<img src="{SITE_URL}/flags/png/{code}.png" width="18" height="13" '
            f'alt="{country} flag" style="vertical-align:-2px;border:0">')


def _stakes_rows(fixtures, owners, today, flag_codes):
    if not fixtures:
        return ""
    todays = [f for f in fixtures.get("fixtures", []) if f["utcDate"][:10] == today]
    if not todays:
        return ""
    rows = ""
    for f in todays[:4]:
        ho, ao = owners.get(f["homeTeam"]), owners.get(f["awayTeam"])
        if ho and ao and ho == ao:
            stake = f"{ho} derby — both teams are {ho}'s"
        elif ho and ao:
            stake = f"{ho}'s {f['homeTeam']} against {ao}'s {f['awayTeam']}"
        elif ho or ao:
            stake = f"{(ho or ao)}'s {(f['homeTeam'] if ho else f['awayTeam'])} in action"
        else:
            stake = "Neutral fixture"
        stage = STAGE_LABELS.get(f["stage"], f["stage"])
        rows += (
            f'<tr><td style="padding:9px 14px;border-bottom:1px solid #e5e0d1">'
            f'<div style="font-family:{MONO};font-size:0.68rem;letter-spacing:2px;'
            f'text-transform:uppercase;color:#8a9284">{stage}</div>'
            f'<div style="font-family:{SANS};font-weight:700;font-size:0.92rem;color:{INK};'
            f'padding-top:2px">{_flag_img(f["homeTeam"], flag_codes)} {f["homeTeam"]} v '
            f'{f["awayTeam"]} {_flag_img(f["awayTeam"], flag_codes)}</div>'
            f'<div style="font-family:{SANS};font-size:0.8rem;color:#5a6b52;padding-top:2px">'
            f'What\'s at stake: {stake}</div></td></tr>')
    return (
        f'<h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;'
        f'margin:26px 0 10px">Today\'s <em style="color:{TERRA}">stakes</em></h2>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{CREAM};border-radius:8px;border-collapse:separate;'
        f'overflow:hidden">{rows}</table>')


def build_email_html(scores, new_events, flag_codes=None, fixtures=None,
                     owners=None, today=None):
    from datetime import datetime, timezone
    flag_codes = flag_codes or {}
    owners = owners or {}
    now = datetime.now(timezone.utc)
    today = today or now.strftime("%Y-%m-%d")
    ranked = sorted(scores["participants"].items(), key=lambda x: x[1]["total"], reverse=True)
    md = matchday_number(today)
    leader_name, leader = ranked[0]
    gap = leader["total"] - ranked[1][1]["total"]

    gains = {}
    for e in new_events:
        gains[e["owner"]] = gains.get(e["owner"], 0) + e.get("points", 0)

    standings_rows = ""
    for rank, (name, data) in enumerate(ranked, 1):
        is_leader = rank == 1
        bg = "#faf3e0" if is_leader else "#ffffff"
        border = f'border-left:3px solid {GOLD};' if is_leader else ''
        gain = gains.get(name, 0)
        chip = (f' <span style="font-family:{MONO};font-size:0.7rem;color:#4a7d4f;'
                f'font-weight:700">&#9650; {gain} today</span>') if gain > 0 else ""
        standings_rows += (
            f'<tr style="background:{bg}">'
            f'<td style="{border}padding:12px 14px;font-family:{SERIF};font-style:italic;'
            f'font-size:1.05rem;color:{"#b3763f" if is_leader else "#8a9284"};width:26px">{rank}</td>'
            f'<td style="padding:12px 6px;font-family:{SANS};font-weight:700;'
            f'font-size:0.95rem;color:{INK}">{name}{chip}</td>'
            f'<td style="padding:12px 14px;font-family:{MONO};font-weight:700;'
            f'font-size:1.05rem;text-align:right;color:'
            f'{"#9a7118" if is_leader else INK}">{data["total"]}</td></tr>')

    events_rows = ""
    for e in new_events[:20]:
        label = EVENT_LABELS.get(e["event"], e["event"])
        is_qual = e["event"] in ("QUALIFY_TOP_2", "QUALIFY_BEST_THIRD")
        opp = f' vs {e["opponent"]}' if e.get("opponent") and not is_qual else ""
        events_rows += (
            f'<tr><td style="padding:9px 0 9px 14px;width:44px;vertical-align:top;'
            f'border-bottom:1px solid #f0ede4">'
            f'<span style="font-family:{MONO};background:{DEEP};color:#f2f0e9;'
            f'font-weight:700;padding:2px 7px;font-size:0.8rem">+{e["points"]}</span></td>'
            f'<td style="padding:9px 14px;font-family:{SANS};font-size:0.88rem;color:{INK};'
            f'border-bottom:1px solid #f0ede4"><strong>{e["owner"]}</strong> — '
            f'{_flag_img(e["country"], flag_codes)} {e["country"]} {label}{opp}'
            f'<span style="font-family:{MONO};font-size:0.7rem;color:#8a9284"> · '
            f'{e.get("date", "")}</span></td></tr>')
    if not events_rows:
        events_rows = (f'<tr><td style="padding:12px 14px;font-family:{SANS};color:#8a9284;'
                       f'font-style:italic;font-size:0.85rem">No new points since the last '
                       f'update.</td></tr>')

    stakes_html = _stakes_rows(fixtures, owners, today, flag_codes)
    day = format_day(now)
    gap_line = (f"{leader_name} leads by {gap}" if gap
                else f"{leader_name} level at the top")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:24px 12px;background:#e8e4d8">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
    style="max-width:540px;margin:0 auto;background:#ffffff;border-collapse:separate;
    border-radius:12px;overflow:hidden">
    <tr><td style="background:{DEEP};padding:30px 28px">
      <div style="font-family:{MONO};font-size:0.66rem;letter-spacing:4px;
        text-transform:uppercase;color:{TERRA}">World Cup 2026 · Matchday {md}</div>
      <div style="font-family:{SERIF};font-size:1.5rem;color:#f2f0e9;padding-top:8px">
        McAndrew <em style="color:{GOLD}">Sweepstake</em></div>
      <div style="font-family:{MONO};font-size:0.7rem;color:#9aa89c;padding-top:8px;
        text-transform:uppercase;letter-spacing:2px">{day} {now.strftime('%B %Y')} ·
        {gap_line}</div>
    </td></tr>
    <tr><td style="padding:26px 28px">
      <h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;
        margin:0 0 10px">The <em style="color:{TERRA}">standings</em></h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
        style="border:1px solid #e5e0d1;border-radius:8px;border-collapse:separate;
        overflow:hidden">{standings_rows}</table>
      <h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;
        margin:26px 0 10px">New <em style="color:{TERRA}">points</em></h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{events_rows}</table>
      {stakes_html}
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding-top:30px">
          <a href="{SITE_URL}" style="display:inline-block;background:{DEEP};color:#f2f0e9;
            font-family:{SANS};font-weight:700;font-size:0.92rem;padding:14px 30px;
            border-radius:8px;text-decoration:none">View the live leaderboard &#8594;</a>
        </td></tr></table>
    </td></tr>
    <tr><td style="background:{CREAM};padding:14px 28px;text-align:center">
      <span style="font-family:{MONO};font-size:0.62rem;letter-spacing:2px;
        text-transform:uppercase;color:#8a9284">McAndrew Family · World Cup 2026</span>
    </td></tr>
  </table>
</body>
</html>"""
```

And `main()` becomes (send/tracking logic identical; additions marked):

```python
def main():
    force = "--force" in sys.argv
    test_mode = "--test" in sys.argv                     # NEW
    participants, _ = read_json("participants.json")
    scores, scores_sha = read_json("scores.json")

    try:                                                  # NEW (all optional data)
        flag_codes, _ = read_json("flag-codes.json")
    except Exception:
        flag_codes = {}
    try:
        fixtures, _ = read_json("fixtures.json")
    except Exception:
        fixtures = None

    new_events = new_events_since_last_email(scores)

    if not new_events and not (force or test_mode):
        print("No new points since last email. Skipping.")
        return

    subject = build_subject(scores)
    if test_mode:
        subject = f"[TEST] {subject}"

    recipients = [GMAIL_SENDER] if test_mode else list(participants["emails"].values())
    if not recipients:
        raise ValueError("No recipients found in participants.json emails")
    html_body = build_email_html(
        scores, new_events if new_events else [],
        flag_codes=flag_codes, fixtures=fixtures,
        owners=participants["countryToOwner"])
    send_email(subject, html_body, recipients)

    if test_mode:                                         # NEW: no state updates
        print(f"TEST email sent to {GMAIL_SENDER} only. State not updated.")
        return

    record_emailed(scores, new_events)
    scores["lastEmailAt"] = datetime.now(timezone.utc).isoformat()
    write_json("scores.json", scores, scores_sha, "Record email sent timestamp")
    print(f"Email sent to {len(recipients)} recipients.")
```

- [ ] **Step 4: Run tests until green**

Run: `python -m pytest tests/test_send_digest.py tests/test_fetch_fixtures.py -v`
Expected: all pass

- [ ] **Step 5: Render a preview** — quick throwaway command (repo root):

```bash
python -c "
import json, send_digest as sd
scores = json.load(open('scores.json', encoding='utf-8'))
parts = json.load(open('participants.json', encoding='utf-8'))
codes = json.load(open('flag-codes.json', encoding='utf-8'))
html = sd.build_email_html(scores, sd.new_events_since_last_email(scores),
                           flag_codes=codes, owners=parts['countryToOwner'])
open('email_preview.html', 'w', encoding='utf-8').write(html)
print('email_preview.html written; subject:', sd.build_subject(scores))
"
```

Open `email_preview.html` in browser — brand check. Delete the preview file after (`rm email_preview.html`).

- [ ] **Step 6: Test send to self**

Run: `python send_digest.py --test`
Expected: `TEST email sent to edward.mcandrew20@gmail.com only. State not updated.` Verify in inbox (Gmail app/web): header, standings, flags render.

- [ ] **Step 7: Commit**

```bash
git add send_digest.py tests/test_send_digest.py
git commit -m "Redesign daily email in Tournament Editorial brand with stakes block"
```

---

### Task 12: Retire generator, deploy, verify live

**Goal:** Delete `generate_html.py`, push everything, verify the live Pages site and full pipeline.

**Files:**
- Delete: `generate_html.py`
- Modify: none (deployment)

**Acceptance Criteria:**
- [ ] `generate_html.py` deleted; `grep -ri generate_html . --include=*.py` returns nothing
- [ ] All tests green: `node --test tests/derive.test.mjs` and `python -m pytest tests/ -v`
- [ ] `git pull --rebase origin main` then push succeeds; Pages serves the new site with all sections working
- [ ] `python fetch_fixtures.py` and `python update_scores.py` still run cleanly after the push (pipeline unbroken)
- [ ] User informed to update the scheduled chain: replace the `generate_html.py` step with `fetch_fixtures.py` (order: `update_scores.py` → `fetch_fixtures.py` → `send_digest.py`)

**Verify:** live URL `https://bandybarbecue.github.io/mcandrew-sweepstake-2026` renders the new site (hard-refresh; Pages deploys can take 1–3 min)

**Steps:**

- [ ] **Step 1: Delete the generator**

```bash
git rm generate_html.py
grep -ri generate_html . --include=*.py || echo CLEAN
```

- [ ] **Step 2: Full test sweep**

```bash
node --test tests/derive.test.mjs
python -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 3: Sync and push**

```bash
git pull --rebase origin main
git push origin main
```

(If the rebase hits conflicts on `scores.json`/`index.html` from API commits, take the REMOTE version of `scores.json` and OUR version of `index.html`.)

- [ ] **Step 4: Verify live** — wait ~2 min, then load the live URL with a hard refresh. Walk all sections on desktop + phone-width. Confirm `scores.json` fetch in Network tab is 200 with cache-buster.

- [ ] **Step 5: Confirm pipeline end-to-end**

```bash
python update_scores.py
python fetch_fixtures.py
```

Expected: both complete; site reflects any new data after Pages redeploys.

- [ ] **Step 6: Tell the user** (checkpoint — requires their action): update the scheduled task so the chain is `update_scores.py` → `fetch_fixtures.py` → `send_digest.py` (drop `generate_html.py`).

- [ ] **Step 7: Commit anything outstanding & final push**

```bash
git status --short   # should be clean
```

---

## Self-Review (completed)

- **Spec coverage:** architecture→T4/T12, flags→T1, fixtures→T2, derivations→T3, hero/topbar→T4, standings+log→T5, race chart→T6, matchday→T7, bracket→T8, squads/records/results→T9, motion/a11y→T10, email→T11, retirement/deploy→T12. Error handling in T2/T4/T7/T11. Testing spread across all tasks. No gaps found.
- **Placeholder scan:** no TBD/TODO items; all steps carry complete code or exact commands.
- **Type consistency:** `derive.js` exports match `app.js` imports (`D.*` namespace); `PLAYER_COLORS`/`flagImg`/`esc`/`fmtDate`/`fmtKickoff`/`ownerDot` defined in T4/T7 before use in T5–T9; `build_email_html(scores, new_events, flag_codes=, fixtures=, owners=, today=)` signature consistent between T11 code and tests; `write_html` reuse for `fixtures.json` matches its actual signature in `github_utils.py`.
