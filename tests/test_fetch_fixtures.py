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
