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

export function teamStatus(scores, participants, fixtures = null) {
  const evs = allEvents(scores);
  const aliases = participants.apiNameAliases || {};
  const norm = n => aliases[n] || n;
  const knockoutBegan = evs.some(e => KNOCKOUT_EVENTS.includes(e.event));
  const qualified = new Set(evs.filter(e => QUALIFY_EVENTS.includes(e.event)).map(e => e.country));
  const koLosers = new Set(
    evs.filter(e => KNOCKOUT_EVENTS.includes(e.event)).map(e => norm(e.opponent)));
  // A team with an upcoming knockout fixture is alive even if its QUALIFY_*
  // award hasn't landed yet (best-third bonuses are only awarded when the
  // team's R32 match finishes).
  const inUpcomingKO = new Set((fixtures?.fixtures || [])
    .filter(f => f.stage !== 'GROUP_STAGE')
    .flatMap(f => [norm(f.homeTeam), norm(f.awayTeam)]));
  const status = {};
  for (const [country, owner] of Object.entries(participants.countryToOwner)) {
    let alive = true;
    if (koLosers.has(country)) alive = false;
    else if (knockoutBegan && !qualified.has(country) && !inUpcomingKO.has(country)) alive = false;
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

export function bracketData(scores, fixtures, aliases = {}) {
  const evs = allEvents(scores);
  const norm = n => aliases[n] || n;
  return Object.keys(EXPECTED_TIES).map(stage => {
    const evKey = STAGE_EVENT[stage];
    const played = evs.filter(e => e.event === evKey).map(e => ({
      home: e.country, away: norm(e.opponent), winner: e.country,
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
