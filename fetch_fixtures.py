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
