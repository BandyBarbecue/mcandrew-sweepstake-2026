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
  // Regression: log entries can carry un-normalized API names (pre-alias-fix data).
  // USA beat "Bosnia-Herzegovina" (raw) in the R32; canonical key is "Bosnia & Herz."
  assert.equal(st['Bosnia & Herz.'].alive, false);
});

test('records shape and sanity', () => {
  const r = records(scores);
  assert.ok(r.biggestDay.points > 0);
  assert.ok(r.biggestDay.owner && r.biggestDay.owner !== '—');
  assert.ok(r.mostValuableTeam.points > 0);
  assert.ok(r.knockoutKing.owner && r.knockoutKing.owner !== '—');
  assert.ok(r.sharpestRise.points > 0);
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
  const rounds = bracketData(scores, { fixtures: [] }, participants.apiNameAliases);
  const byStage = Object.fromEntries(rounds.map(r => [r.stage, r.ties.length]));
  assert.deepEqual(byStage, {
    LAST_32: 16, LAST_16: 8, QUARTER_FINALS: 4,
    SEMI_FINALS: 2, THIRD_PLACE: 1, FINAL: 1,
  });
  // Regression: raw API opponent names are normalized for display/lookup
  const r32 = rounds.find(r => r.stage === 'LAST_32');
  assert.ok(r32.ties.some(t => t.away === 'Bosnia & Herz.'));
  assert.ok(!r32.ties.some(t => t.away === 'Bosnia-Herzegovina'));
});

test('teamStatus keeps un-awarded best-thirds alive when they have an upcoming KO fixture', () => {
  const synthScores = { participants: {
    A: { total: 4, countries: { X: { points: 4 } },
         log: [{ country: 'X', event: 'LAST_32_WIN', points: 4, date: '2026-07-01', opponent: 'Z', matchId: 1 }] },
    B: { total: 0, countries: { Y: { points: 0 } }, log: [] },
  } };
  const synthParts = { countryToOwner: { X: 'A', Y: 'B', Z: 'B' }, apiNameAliases: {} };
  const fixturesStub = { fixtures: [
    { matchId: 2, homeTeam: 'Y', awayTeam: 'X', utcDate: '2026-07-05T16:00:00Z', stage: 'LAST_32' },
  ] };
  // Without fixtures: Y eliminated (knockouts began, no qualify event)
  assert.equal(teamStatus(synthScores, synthParts).Y.alive, false);
  // With fixtures: Y alive (upcoming KO fixture)
  assert.equal(teamStatus(synthScores, synthParts, fixturesStub).Y.alive, true);
  // koLosers still wins: Z lost to X, stays eliminated even if in a fixture
  const zFix = { fixtures: [{ matchId: 3, homeTeam: 'Z', awayTeam: 'X', utcDate: '2026-07-06T16:00:00Z', stage: 'LAST_16' }] };
  assert.equal(teamStatus(synthScores, synthParts, zFix).Z.alive, false);
});

test('matchdayNumber', () => {
  assert.equal(matchdayNumber('2026-06-11'), 1);
  assert.equal(matchdayNumber('2026-07-03'), 23);
});
