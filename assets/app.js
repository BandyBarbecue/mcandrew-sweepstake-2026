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

  const status = D.teamStatus(scores, participants, fixtures);
  document.getElementById('app').hidden = false;

  const renderers = [
    () => renderTopbar(scores),
    () => renderHero(scores, participants, status),
    // SECTION RENDERERS — added by later tasks:
    () => renderStandings(scores, participants, status),
    // () => renderRace(scores),                               (Task 6)
    // () => renderMatchday(scores, participants, rules, fixtures), (Task 7)
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
