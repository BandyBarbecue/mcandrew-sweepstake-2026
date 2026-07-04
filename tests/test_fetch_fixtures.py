import pytest

import fetch_fixtures
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

def test_main_warns_and_exits_zero_on_failure(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    # Fail at the very first step; also stub requests.get so the test can
    # never hit the real API even if main()'s ordering changes.
    monkeypatch.setattr(fetch_fixtures, "read_json", boom)
    monkeypatch.setattr(fetch_fixtures.requests, "get", boom)
    with pytest.raises(SystemExit) as exc:
        fetch_fixtures.main()
    assert exc.value.code == 0
    assert "WARNING: fixtures fetch skipped" in capsys.readouterr().out
