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
    // () => renderStandings(scores, participants, status),   (Task 5)
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
