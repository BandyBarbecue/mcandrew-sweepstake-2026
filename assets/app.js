import * as D from './derive.js';

// Mirrors --gold/--sage/--slate/--rose in styles.css — keep in sync
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

function fmtKickoffDate(utcISO) {
  return new Date(utcISO).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', timeZone: 'Europe/London',
  });
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
    <div class="stat"><dt>Teams alive</dt><dd>${alive}<small>/${Object.keys(status).length}</small></dd></div>`;

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
  const closeMenu = () => {
    nav.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  };
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', closeMenu);
  document.addEventListener('click', (e) => {
    if (!nav.contains(e.target) && !btn.contains(e.target)) closeMenu();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMenu();
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

let raceFilter = 'all';
let raceRevealed = false;

function biggestSwings(scores, n = 2) {
  const evs = D.allEvents(scores).filter(e => e.points >= 4);
  return [...evs].sort((a, b) => b.points - a.points).slice(0, n);
}

function renderRace(scores) {
  const root = document.getElementById('race-root');
  const { dates, series } = D.cumulativeSeries(scores, raceFilter);
  if (!dates.length) {
    root.innerHTML = `
      <div class="section-head">
        <h2 class="section-title">The points <em>race</em></h2>
        <span class="kicker terra">The story so far</span>
      </div>
      <p class="race-empty">No points in this phase yet — check back after the next matchday.</p>
      <div class="race-chips" role="group" aria-label="Filter chart">
        ${[['all', 'All'], ['group', 'Group stage'], ['knockout', 'Knockouts']].map(([k, lbl]) =>
          `<button class="race-chip" data-filter="${k}" aria-pressed="${k === raceFilter}">${lbl}</button>`).join('')}
      </div>`;
    root.querySelectorAll('.race-chip').forEach(chip => {
      chip.addEventListener('click', () => { raceFilter = chip.dataset.filter; renderRace(scores); });
    });
    return;
  }
  const players = Object.keys(series);
  const W = 640, H = 240, PAD_L = 34, PAD_B = 22, PAD_T = 44, PAD_R = 74;
  const maxVal = Math.max(1, ...players.flatMap(p => series[p]));
  const x = i => PAD_L + (i / Math.max(dates.length - 1, 1)) * (W - PAD_L - PAD_R);
  const y = v => H - PAD_B - (v / maxVal) * (H - PAD_B - PAD_T);

  // Resolve end-label collisions: sort by y, enforce min 13-unit separation
  const labelYs = players.map(p => ({ p, y: y(series[p].at(-1) ?? 0) + 3 }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < labelYs.length; i++) {
    if (labelYs[i].y - labelYs[i - 1].y < 13) labelYs[i].y = labelYs[i - 1].y + 13;
  }
  // Clamp: if the cascade pushed past the bottom, shift the stack back up
  const maxY = H - 6;
  if (labelYs.length && labelYs[labelYs.length - 1].y > maxY) {
    labelYs[labelYs.length - 1].y = maxY;
    for (let i = labelYs.length - 2; i >= 0; i--) {
      if (labelYs[i + 1].y - labelYs[i].y < 13) labelYs[i].y = labelYs[i + 1].y - 13;
    }
  }
  const labelY = Object.fromEntries(labelYs.map(({ p, y }) => [p, y]));

  const lines = players.map(p => {
    const pts = series[p].map((v, i) => `${x(i)},${y(v)}`).join(' ');
    const end = series[p].at(-1) ?? 0;
    return `<g class="race-line" data-player="${esc(p)}">
      <polyline class="draw" points="${pts}" fill="none"
        stroke="${PLAYER_COLORS[p]}" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="${x(series[p].length - 1)}" cy="${y(end)}" r="3" fill="${PLAYER_COLORS[p]}"/>
      <text class="race-axis" x="${x(series[p].length - 1) + 7}" y="${labelY[p]}"
        fill="${PLAYER_COLORS[p]}">${esc(p)} · ${end}</text></g>`;
  }).join('');

  const annos = raceFilter === 'all' ? biggestSwings(scores).map((e, idx) => {
    const di = dates.indexOf(e.date);
    if (di < 0) return '';
    const val = series[e.owner][di];
    const stageShort = { LAST_32_WIN: 'R32', LAST_16_WIN: 'R16', QUARTER_FINALS_WIN: 'QF',
      SEMI_FINALS_WIN: 'SF', THIRD_PLACE_WIN: '3RD', FINAL_WIN: 'FINAL' }[e.event] || 'GRP';
    const annoY = 14 + idx * 13;
    return `<line x1="${x(di)}" y1="${y(val)}" x2="${x(di)}" y2="${annoY + 3}"
        stroke="rgba(201,138,91,0.45)" stroke-width="1" stroke-dasharray="2,3"/>
      <text class="race-anno" x="${Math.min(x(di), W - 150)}" y="${annoY}">
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
  if (raceRevealed) {
    svg.classList.add('in');
  } else {
    new IntersectionObserver(([e], io) => {
      if (e.isIntersecting) { raceRevealed = true; svg.classList.add('in'); io.disconnect(); }
    }, { threshold: 0.3 }).observe(svg);
  }

  root.querySelectorAll('.race-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      raceFilter = chip.dataset.filter;
      renderRace(scores);
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

function ownerDot(owner) {
  return owner ? `<span class="owner-dot" title="${esc(owner)}"
    style="background:${PLAYER_COLORS[owner] || '#888'}"></span>` : '';
}

function renderMatchday(scores, participants, rules, fixtures) {
  const owners = participants.countryToOwner;
  const aliases = participants.apiNameAliases || {};
  const norm = n => aliases[n] || n;
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
      const dotOwner = owners[norm(f.homeTeam)] || owners[norm(f.awayTeam)];
      return `<div class="timeline-item" data-reveal style="--stagger:${i};
          --dot:${PLAYER_COLORS[dotOwner] || 'var(--sage)'}">
        <div class="timeline-when">${fmtKickoff(f.utcDate)} ·
          ${esc(D.STAGE_LABELS[f.stage] || f.stage)} · ${fmtKickoffDate(f.utcDate)}</div>
        <div class="timeline-tie">${ownerDot(owners[norm(f.homeTeam)])} ${flagImg(f.homeTeam)}
          ${esc(f.homeTeam)} <span class="timeline-score">v</span>
          ${esc(f.awayTeam)} ${flagImg(f.awayTeam)} ${ownerDot(owners[norm(f.awayTeam)])}</div>
        <div class="timeline-stake">${esc(stake)}</div></div>`;
    }).join('');
  } else {
    title = `Latest <em>results</em>`;
    kicker = 'Fixtures unavailable';
    items = (scores.recentResults || []).slice(0, 4).map((r, i) =>
      `<div class="timeline-item" data-reveal style="--stagger:${i};
          --dot:${PLAYER_COLORS[owners[norm(r.homeTeam)]] || 'var(--sage)'}">
        <div class="timeline-when">${esc(r.stage)} · ${fmtDate(r.date)}</div>
        <div class="timeline-tie">${ownerDot(owners[norm(r.homeTeam)])} ${flagImg(r.homeTeam)}
          ${esc(r.homeTeam)} <span class="timeline-score">${r.homeScore ?? '–'}–${r.awayScore ?? '–'}</span>
          ${esc(r.awayTeam)} ${flagImg(r.awayTeam)} ${ownerDot(owners[norm(r.awayTeam)])}</div>
      </div>`).join('');
  }

  root.innerHTML = `<div class="section-head">
      <h2 class="section-title">${title}</h2>
      <span class="kicker" style="color:var(--terra-deep)">${esc(kicker)}</span>
    </div><div class="timeline">${items}</div>`;
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

  const status = D.teamStatus(scores, participants, fixtures);
  document.getElementById('app').hidden = false;

  const renderers = [
    () => renderTopbar(scores),
    () => renderHero(scores, participants, status),
    // SECTION RENDERERS — added by later tasks:
    () => renderStandings(scores, participants, status),
    () => renderRace(scores),
    () => renderMatchday(scores, participants, rules, fixtures),
    // () => renderBracket(scores, participants, fixtures, status), (Task 8)
    // () => renderSquads(scores, participants, status),      (Task 9)
    // () => renderRecords(scores),                            (Task 9)
    // () => renderResults(scores),                            (Task 9)
    () => renderFooter(scores),
  ];
  for (const render of renderers) {
    try { render(); } catch (e) { console.error('Section render failed:', e); }
  }
  initTopbarBehavior();
  initReveals();
}

main();
