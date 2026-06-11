import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from github_utils import read_json, write_json

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

if not API_KEY:
    raise ValueError("FOOTBALL_DATA_API_KEY must be set in .env")

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"  # FIFA World Cup

STAGE_TO_EVENT = {
    "LAST_32": "LAST_32_WIN",
    "LAST_16": "LAST_16_WIN",
    "QUARTER_FINALS": "QUARTER_FINALS_WIN",
    "SEMI_FINALS": "SEMI_FINALS_WIN",
    "THIRD_PLACE": "THIRD_PLACE_WIN",
    "FINAL": "FINAL_WIN",
}

STAGE_LABELS = {
    "GROUP_STAGE": "Group Stage",
    "LAST_32": "Round of 32",
    "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-Final",
    "SEMI_FINALS": "Semi-Final",
    "THIRD_PLACE": "3rd Place Play-off",
    "FINAL": "Final",
}


def api_get(endpoint):
    r = requests.get(
        f"{API_BASE}/{endpoint}",
        headers={"X-Auth-Token": API_KEY}
    )
    r.raise_for_status()
    return r.json()


def normalize(name, aliases):
    return aliases.get(name, name)


def award(country, event_key, points, date, opponent, match_id, owner, scores, rules, new_events):
    scores["participants"][owner]["countries"][country]["points"] += points
    log_entry = {
        "country": country,
        "event": event_key,
        "points": points,
        "date": date,
        "opponent": opponent,
        "matchId": match_id,
    }
    scores["participants"][owner]["log"].insert(0, log_entry)
    scores["participants"][owner]["total"] += points
    new_events.append({"owner": owner, **log_entry})


def main():
    participants, _ = read_json("participants.json")
    rules, _ = read_json("scoring-rules.json")
    scores, scores_sha = read_json("scores.json")

    aliases = participants["apiNameAliases"]
    country_to_owner = participants["countryToOwner"]
    processed = set(scores["processedMatchIds"])
    new_events = []

    # --- Fetch finished matches ---
    data = api_get(f"competitions/{COMPETITION}/matches?status=FINISHED")
    matches = data.get("matches", [])

    print(f"Fetched {len(matches)} finished matches from API.")

    latest_match_date = max((m["utcDate"][:10] for m in matches), default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    for match in matches:
        mid = match["id"]
        if mid in processed:
            continue

        home_name = match["homeTeam"]["name"] or ""
        away_name = match["awayTeam"]["name"] or ""
        home = normalize(home_name, aliases)
        away = normalize(away_name, aliases)
        winner = match["score"]["winner"]  # HOME_TEAM | AWAY_TEAM | DRAW | null
        stage = match["stage"]
        date = match["utcDate"][:10]

        # Skip if winner is null (match not yet decided / extra time pending)
        if not winner:
            continue

        if stage == "GROUP_STAGE":
            if winner == "DRAW":
                for team, opp in [(home, away), (away, home)]:
                    if team in country_to_owner:
                        award(
                            team, "GROUP_STAGE_DRAW", rules["GROUP_STAGE_DRAW"],
                            date, opp, mid, country_to_owner[team], scores, rules, new_events
                        )
            else:
                win_team = home if winner == "HOME_TEAM" else away
                lose_team = away if winner == "HOME_TEAM" else home
                if win_team in country_to_owner:
                    award(
                        win_team, "GROUP_STAGE_WIN", rules["GROUP_STAGE_WIN"],
                        date, lose_team, mid, country_to_owner[win_team], scores, rules, new_events
                    )

        elif stage in STAGE_TO_EVENT:
            win_team = home if winner == "HOME_TEAM" else away
            lose_team = away if winner == "HOME_TEAM" else home
            if win_team in country_to_owner:
                event_key = STAGE_TO_EVENT[stage]
                award(
                    win_team, event_key, rules[event_key],
                    date, lose_team, mid, country_to_owner[win_team], scores, rules, new_events
                )

        processed.add(mid)

    # --- Qualification bonuses via standings ---
    try:
        standings_data = api_get(f"competitions/{COMPETITION}/standings")
        for group_standing in standings_data.get("standings", []):
            if group_standing.get("type") != "TOTAL":
                continue
            table = group_standing["table"]
            # Group is finished when all teams have played at least 3 games
            group_finished = all(t["playedGames"] >= 3 for t in table)
            if not group_finished:
                continue

            for entry in table:
                team = normalize(entry["team"]["name"], aliases)
                pos = entry["position"]
                if team not in country_to_owner:
                    continue
                if team in scores["qualificationAwarded"]:
                    continue
                if pos <= 2:
                    owner = country_to_owner[team]
                    award(
                        team, "QUALIFY_TOP_2", rules["QUALIFY_TOP_2"],
                        latest_match_date,
                        "Group qualification", f"qual_{team}",
                        owner, scores, rules, new_events
                    )
                    scores["qualificationAwarded"].append(team)

    except Exception as e:
        print(f"Standings check skipped: {e}")

    # --- Best 3rd place: infer from LAST_32 participants not awarded top-2 yet ---
    # Once LAST_32 matches exist, any team appearing there that wasn't top-2 qualified as best 3rd
    last_32_matches = [m for m in matches if m["stage"] == "LAST_32"]
    if last_32_matches:
        qualified_via_third = set()
        for m in last_32_matches:
            for team_data in [m["homeTeam"], m["awayTeam"]]:
                t_name = team_data["name"] or ""
                team = normalize(t_name, aliases)
                if team in country_to_owner and team not in scores["qualificationAwarded"]:
                    qualified_via_third.add(team)
        for team in qualified_via_third:
            owner = country_to_owner[team]
            award(
                team, "QUALIFY_BEST_THIRD", rules["QUALIFY_BEST_THIRD"],
                latest_match_date,
                "Best 3rd place", f"best3rd_{team}",
                owner, scores, rules, new_events
            )
            scores["qualificationAwarded"].append(team)

    # --- Recent results (last 10 finished matches, newest first) ---
    recent = []
    for match in sorted(matches, key=lambda m: m["utcDate"], reverse=True)[:10]:
        home = normalize(match["homeTeam"]["name"] or "", aliases)
        away = normalize(match["awayTeam"]["name"] or "", aliases)
        score_data = match["score"]["fullTime"]
        recent.append({
            "matchId": match["id"],
            "homeTeam": home,
            "awayTeam": away,
            "homeScore": score_data["home"],
            "awayScore": score_data["away"],
            "date": match["utcDate"][:10],
            "stage": STAGE_LABELS.get(match["stage"], match["stage"]),
        })

    scores["recentResults"] = recent
    scores["processedMatchIds"] = list(processed)
    scores["lastRunAt"] = datetime.now(timezone.utc).isoformat()

    write_json(
        "scores.json", scores, scores_sha,
        f"Update scores {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    )
    print(f"Run complete. {len(new_events)} new point events.")
    return new_events


if __name__ == "__main__":
    main()
