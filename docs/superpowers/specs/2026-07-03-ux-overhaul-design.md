# UX/UI Overhaul — "Tournament Editorial" Design Spec

**Date:** 3 July 2026
**Status:** Approved by Edward (brainstorming session, visual companion mockup `direction-v3.html`)
**Scope:** Complete visual redesign of the sweepstake site and daily email. Backend scoring logic is untouched.

---

## 1. Goals & constraints

- Professionally designed look — editorial sports storytelling, not a generic dashboard and not the rounded-glassy "AI look". Reference: banff.tips (studied live; tokens extracted from its DOM).
- Fancy visuals: scroll-driven chart animation, staggered reveals, expandable rows, dropdown/accordion panels, horizontal bracket.
- Professional inline SVG icons (Lucide) and real SVG flags. **No emoji anywhere** on site or email.
- Still warm and family-friendly (McAndrew Family sweepstake, 4 players).
- Must work with the existing GitHub repo + GitHub Pages deployment.
- **Must not change scoring logic**: `update_scores.py`, `scoring-rules.json`, `github_utils.py` untouched.

## 2. Architecture (Approach A — static shell + client-side rendering)

| File | Role |
|---|---|
| `index.html` | Hand-authored static page (HTML + CSS + vanilla JS, no framework, no build step). Committed once; edited directly thereafter. Fetches JSON on load with cache-buster (`scores.json?v=<Date.now()>`). |
| `flags/*.svg`, `flags/png/*.png` | 48 flag SVGs from the open-source `flag-icons` set + 1 fallback flag (site use), plus 40px-wide PNG renders of the same flags (email use — Gmail/Outlook do not render SVG images). Committed once, served by Pages. |
| `fetch_fixtures.py` | **New, read-only.** Fetches upcoming WC fixtures (football-data.org, existing API key), maps names through existing `apiNameAliases`, writes `fixtures.json` via `github_utils.write_json`. Runs after `update_scores.py` in the scheduled chain. On API failure: leaves previous `fixtures.json`, exits 0. |
| `send_digest.py` | Only `build_email_html()` + subject line rewritten. Send/tracking logic (`emailedEvents`, `--force`, recipients, `lastEmailAt`) byte-for-byte unchanged. |
| `generate_html.py` | Retired — deleted from working tree (preserved in git history); removed from the scheduled chain. |
| `update_scores.py`, `scoring-rules.json`, `github_utils.py` | **Untouched.** |

**Data flow:** `update_scores.py` → `scores.json` (unchanged) → browser fetches `scores.json`, `participants.json`, `fixtures.json` (same-origin on Pages — no CORS, no keys) and derives all presentation data client-side.

**Error handling:**
- JSON fetch failure → styled "couldn't load the latest scores — pull to refresh" state, never a blank page.
- `fixtures.json` missing/stale → bracket omits upcoming pairings; matchday section falls back to recent results; email omits "today's stakes". Graceful, no crash.

## 3. Visual system

**Typography** (Google Fonts, `font-display: swap`):
- **Fraunces** — display serif: headlines, rank numerals, *italic accent words* ("The *standings*")
- **Schibsted Grotesk** — body, names, buttons (fallback: system sans)
- **JetBrains Mono** — data voice: scores, timestamps, letterspaced small-caps kickers (`MATCHDAY 19 · ROUND OF 32`) (fallback: Courier)

**Palette:**

| Token | Value | Use |
|---|---|---|
| Pitch black-green | `#0b120d` / `#0f1a14` | Dark section backgrounds (majority of page) |
| Parchment | `#f2efe6` | Alternating light sections |
| Old gold | `#d9a441` | Leader, points emphasis, player 1 chart line |
| Terracotta | `#c98a5b` / `#b3763f` | Kickers, italic accents, chart annotations |
| Sage | `#7ea87f` | Positive deltas, "alive" states, player 2 chart line |
| Slate blue | `#8fa3c9` | Player 3 chart line |
| Dusty rose | `#c9808f` | Player 4 chart line |

Gold plays two distinct roles: as a **positional** treatment (the leader's standings card and leader references always use gold, whoever leads) and as **Kenny's fixed identity color** in the chart/bracket/timeline. Player identity colors are assigned once at implementation time (Kenny gold, Fiona sage, Alex slate blue, Edward dusty rose) and never change with rank; if the lead changes, the leader-card treatment moves but identity colors stay put.

**Iconography:** inline Lucide SVG paths (trophy, chevron, calendar, arrow-up-right, etc.). Medals replaced by typographic italic Fraunces rank numerals.

**Flags:** self-hosted `flag-icons` SVGs, small rounded-2px rectangles with subtle border. Eliminated teams: desaturated flag + struck-through name.

**Depth & texture:** alternating dark/cream sections; one soft radial wash behind hero; 12–16px radii on cards only; hairline rules `rgba(232,230,223,0.08–0.14)`; no glassmorphism, no neon glow, no heavy shadows.

## 4. Page structure (single scroll, mobile-first, ~720px column)

1. **Sticky header** — appears after hero: slim dark bar, wordmark, top-3 mini scores (mono), anchor links (Standings · Race · Bracket · Squads) with smooth scroll; collapses to dropdown on mobile.
2. **Hero** — full-viewport dark: terracotta kicker `WORLD CUP 2026 · USA · CANADA · MEXICO`; Fraunces headline "One family, four rivals, *one cup.*" (staggered word fade-up on load); live stat strip: Matchday · Stage · Leader · Teams alive; scroll cue.
3. **Standings** — gold leader card (points-composition bar, "▲ N today" chip) + hairline rows with per-player sparklines. Rows expand on click (animated height, rotating chevron, `<button>` semantics) to show the full event log: `+4 · Spain won Round of 32 vs Austria · 2 Jul` with flags and mono dates.
4. **Points race** — cumulative SVG line chart, fixed player colors; lines draw on scroll-into-view (stroke-dashoffset, ~1.2s ease-out); terracotta mono annotations on big swings; pill filters All / Group stage / Knockouts; hover/tap highlights one player, dims others; sr-only data table mirror.
5. **Matchday timeline** *(cream)* — today/next fixtures as vertical timeline with time chips (`17:00 BST · ROUND OF 32`) and family-stake lines generated from ownership ("Kenny derby — he owns both. Guaranteed +5."). Fallback: recent results.
6. **Knockout bracket** — horizontally scrollable R32→Final; each tie: two flags + owner player-color dots; winners bold, losers faded; champion slot gold-outlined and empty until the final.
7. **Squad explorer** — accordion, one panel per player: 12 countries with flags, per-team points contributed (e.g. "Cape Verde · 10"), alive/out counts; eliminated struck through. Clicking a country highlights/filters that team's events in the standings log.
8. **Records** *(cream)* — stagger-revealed stat cards: Biggest single day · Most valuable team · Points by round · Fastest climber. Huge Fraunces number + mono caption.
9. **Recent results** — last 10, restyled with flags and stage chips.
10. **Footer** — mono line: data source, last-updated (BST), "Powered by GitHub Pages".

**Motion rules:** single IntersectionObserver; reveals = fade-up + 12px translate, 500ms, staggered children; all motion gated behind `prefers-reduced-motion` (instant if set). No parallax, no scroll-jacking.

**Accessibility:** semantic headings; expanders are `<button>` with `aria-expanded`; gold `:focus-visible` outlines; chart has sr-only table; color never sole meaning carrier (strike-through + fade for eliminated).

## 5. Client-side derivations (all from existing data)

- **Cumulative series:** group each player's `log` by date, running total per date → chart lines. Must end exactly at each player's `total`.
- **Alive/eliminated:** a team is eliminated iff (a) the knockout stage has begun (any `LAST_32_WIN` event exists in any log) and the team has no `QUALIFY_TOP_2` / `QUALIFY_BEST_THIRD` event, or (b) it appears as `opponent` in any knockout win event. Alive otherwise. (Per-group completion is not derivable from the data; the global knockout-began check is sufficient because all qualification events are awarded before the R32 starts.)
- **Records:** max points-per-day per player; max per-team contribution; per-round sums; biggest day-over-day rank climb.
- **Today's stakes:** fixtures where ≥1 team is family-owned → template sentences (same-owner derby, head-to-head between players, single-owner match).

## 6. Daily email (table-based, inline styles, Outlook-safe)

- **Header:** solid `#0b120d`, "McANDREW SWEEPSTAKE" in Georgia serif, terracotta kicker `WORLD CUP 2026 · MATCHDAY N`, date in Courier-family gray caps. Typography only — no emoji, no images required for the header.
- **Standings:** leader row warm-gold tint + "▲ N today" chip; others white with hairline rules; points Courier-bold; italic Georgia rank numerals; 20px flag images via absolute Pages URLs with alt text (degrades to text if images blocked).
- **Points update:** `+N` chip (dark green square) · "**Owner** — Team won Round vs Opponent" · mono date.
- **Today's stakes** *(new)*: cream block from `fixtures.json` with owner stakes; silently omitted when unavailable.
- **CTA:** rectangular dark-green button "View the live leaderboard →", full-width on mobile.
- **Subject:** no emoji — pattern: `Sweepstake — Kenny leads by 15 (Matchday 19)`.

## 7. Testing & verification

- **Dev-only Python check script** (not in scheduled chain): validates alive-team inference against known results, and that cumulative chart series end at each `total`.
- **Site:** serve repo locally (`python -m http.server`); verify against real JSON; synthetic cases: empty logs (pre-tournament), missing `fixtures.json`, fetch failure → each shows its designed graceful state.
- **Email:** render `build_email_html()` to file for browser check; `--force` test send to Edward only before family delivery.
- **Cross-device:** Chrome desktop + mobile emulation; keyboard nav; `prefers-reduced-motion`.

## 8. Out of scope

- Any change to scoring rules, score computation, or event tracking.
- Frameworks, bundlers, GitHub Actions, or changes to the deploy mechanism.
- Dark/light theme toggle (site is inherently dual-tone by section).
- Historical data backfill beyond what `scores.json` logs already contain.
