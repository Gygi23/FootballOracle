import requests
import time
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# API Konfiguration

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CALL_LIMIT = 7500

TOURNAMENTS = [
    {"league_id": 1, "season": 2026, "name": "World Cup 2026"},
    {"league_id": 1, "season": 2018, "name": "World Cup 2018"},
    {"league_id": 1, "season": 2022, "name": "World Cup 2022"},
    {"league_id": 4, "season": 2020, "name": "UEFA Euro 2020"},
    {"league_id": 4, "season": 2024, "name": "UEFA Euro 2024"},
    {"league_id": 9, "season": 2021, "name": "Copa América 2021"},
    {"league_id": 9, "season": 2024, "name": "Copa América 2024"},
    {"league_id": 6, "season": 2021, "name": "Africa Cup 2021"},
    {"league_id": 6, "season": 2023, "name": "Africa Cup 2023"},
    {"league_id": 7, "season": 2019, "name": "AFC Asian Cup 2019"},
    {"league_id": 7, "season": 2023, "name": "AFC Asian Cup 2023"},
]

engine = create_engine(
   f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}" 
)

# API call tracker

def get_calls_today() -> int:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT calls_today FROM api_log
            WHERE endpoint = 'daily_total'
            AND DATE(last_called) = CURDATE()
        """)).fetchone()
        return result[0] if result else 0
    
def increment_calls(n: int = 1):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO api_log (endpoint, calls_today, last_called)
            VALUES ('daily_total', :n, NOW())
            ON DUPLICATE KEY UPDATE
                calls_today = IF(DATE(last_called) = CURDATE(), calls_today + :n, :n),
                last_called = NOW()
        """), {"n": n})
        conn.commit()

def api_get(endpoint: str, params: dict) -> dict | None:
    if get_calls_today() >= CALL_LIMIT:
        print(f"Tageslimit von {CALL_LIMIT} Calls erreicht. Morgen weitermachen.")
        return None

    response = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS, params=params)
    increment_calls(1) 
    time.sleep(8)

    if response.status_code == 429:
        print(f"Rate limit getroffen — warte 90 Sekunden...")
        time.sleep(90)
        response = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS, params=params)
        increment_calls(1)
        if response.status_code != 200:
            print(f"Immer noch Fehler nach Warten: {response.status_code}")
            return None

    if response.status_code != 200:
        print(f"API Fehler {response.status_code}: {endpoint}")
        return None

    return response.json()

# Help functions

def get_stat(statistic: list, team_index: int, stat_type: str):
    try:
        stats = statistic[team_index]["statistics"]
        for s in stats:
            if s["type"] == stat_type:
                val = s["value"]
                if val is None:
                    return None
                if isinstance(val, str) and "%" in val:
                    return float(val.replace("%", ""))
                return int(val) if isinstance(val, int) else float(val)
    except (IndexError, KeyError, TypeError):
        return None
    
def fixture_exists(fixture_id: int) -> bool:
    """Prüft ob ein Fixture bereits in der DB ist."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT id FROM tournament_fixtures WHERE fixture_id = :fid"
        ), {"fid": fixture_id}).fetchone()
        return result is not None
 
def standing_exists(league_id: int, season: int, team_id: int) -> bool:
    """Prüft ob ein Standing bereits in der DB ist."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id FROM tournament_standings
            WHERE league_id = :lid AND season = :s AND team_id = :tid
        """), {"lid": league_id, "s": season, "tid": team_id}).fetchone()
        return result is not None
    
# laod data

def load_fixtures(league_id: int, season: int) -> list:
    data = api_get("fixtures", {"league": league_id, "season": season})
    if not data:
        return []
    return data.get("response", [])

def load_statistics(fixture_id: int) -> list:
    """Lädt Statistiken für ein einzelnes Fixture."""
    data = api_get("fixtures/statistics", {"fixture": fixture_id})
    if not data:
        return []
    return data.get("response", [])

def save_fixtures(fixture: dict, statistics: list, league_id: int, season: int):
    fid = fixture["fixture"]["id"]

    row = {
        "fixture_id":   fid,
        "league_id":    league_id,
        "season":       season,
        "home_team":    fixture["teams"]["home"]["name"],
        "away_team":    fixture["teams"]["away"]["name"],
        "match_date":   fixture["fixture"]["date"],
        "stage":        fixture["league"]["round"],
        "status":       fixture["fixture"]["status"]["short"],
        "home_score":   fixture["goals"]["home"],
        "away_score":   fixture["goals"]["away"],
        # Ballbesitz
        "home_possession":          get_stat(statistics, 0, "Ball Possession"),
        "away_possession":          get_stat(statistics, 1, "Ball Possession"),
        # Schüsse
        "home_shots_on_target":     get_stat(statistics, 0, "Shots on Goal"),
        "away_shots_on_target":     get_stat(statistics, 1, "Shots on Goal"),
        "home_shots_off_target":    get_stat(statistics, 0, "Shots off Goal"),
        "away_shots_off_target":    get_stat(statistics, 1, "Shots off Goal"),
        "home_total_shots":         get_stat(statistics, 0, "Total Shots"),
        "away_total_shots":         get_stat(statistics, 1, "Total Shots"),
        "home_blocked_shots":       get_stat(statistics, 0, "Blocked Shots"),
        "away_blocked_shots":       get_stat(statistics, 1, "Blocked Shots"),
        "home_shots_insidebox":     get_stat(statistics, 0, "Shots insidebox"),
        "away_shots_insidebox":     get_stat(statistics, 1, "Shots insidebox"),
        # Defensiv
        "home_saves":               get_stat(statistics, 0, "Goalkeeper Saves"),
        "away_saves":               get_stat(statistics, 1, "Goalkeeper Saves"),
        # Pässe
        "home_total_passes":        get_stat(statistics, 0, "Total passes"),
        "away_total_passes":        get_stat(statistics, 1, "Total passes"),
        "home_passes_accurate":     get_stat(statistics, 0, "Passes accurate"),
        "away_passes_accurate":     get_stat(statistics, 1, "Passes accurate"),
        "home_passes_pct":          get_stat(statistics, 0, "Passes %"),
        "away_passes_pct":          get_stat(statistics, 1, "Passes %"),
        # Disziplin
        "home_fouls":               get_stat(statistics, 0, "Fouls"),
        "away_fouls":               get_stat(statistics, 1, "Fouls"),
        "home_yellow_cards":        get_stat(statistics, 0, "Yellow Cards"),
        "away_yellow_cards":        get_stat(statistics, 1, "Yellow Cards"),
        "home_red_cards":           get_stat(statistics, 0, "Red Cards"),
        "away_red_cards":           get_stat(statistics, 1, "Red Cards"),
        # Weitere
        "home_corners":             get_stat(statistics, 0, "Corner Kicks"),
        "away_corners":             get_stat(statistics, 1, "Corner Kicks"),
        "home_offsides":            get_stat(statistics, 0, "Offsides"),
        "away_offsides":            get_stat(statistics, 1, "Offsides"),
    }

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO tournament_fixtures (
                fixture_id, league_id, season, home_team, away_team,
                match_date, stage, status, home_score, away_score,
                home_possession, away_possession,
                home_shots_on_target, away_shots_on_target,
                home_shots_off_target, away_shots_off_target,
                home_total_shots, away_total_shots,
                home_blocked_shots, away_blocked_shots,
                home_shots_insidebox, away_shots_insidebox,
                home_saves, away_saves,
                home_total_passes, away_total_passes,
                home_passes_accurate, away_passes_accurate,
                home_passes_pct, away_passes_pct,
                home_fouls, away_fouls,
                home_yellow_cards, away_yellow_cards,
                home_red_cards, away_red_cards,
                home_corners, away_corners,
                home_offsides, away_offsides
            ) VALUES (
                :fixture_id, :league_id, :season, :home_team, :away_team,
                :match_date, :stage, :status, :home_score, :away_score,
                :home_possession, :away_possession,
                :home_shots_on_target, :away_shots_on_target,
                :home_shots_off_target, :away_shots_off_target,
                :home_total_shots, :away_total_shots,
                :home_blocked_shots, :away_blocked_shots,
                :home_shots_insidebox, :away_shots_insidebox,
                :home_saves, :away_saves,
                :home_total_passes, :away_total_passes,
                :home_passes_accurate, :away_passes_accurate,
                :home_passes_pct, :away_passes_pct,
                :home_fouls, :away_fouls,
                :home_yellow_cards, :away_yellow_cards,
                :home_red_cards, :away_red_cards,
                :home_corners, :away_corners,
                :home_offsides, :away_offsides
            )
        """), row)
        conn.commit()

def load_standings(league_id: int, season: int):
    data = api_get("standings", {"league": league_id, "season": season})
    if not data:
        return
    
    groups = data.get("response", [])
    if not groups:
        return
    
    standings = groups[0]["league"]["standings"]

    with engine.connect() as conn:
        for group in standings:
            for entry in group:
                conn.execute(text("""
                    INSERT IGNORE INTO tournament_standings (
                        league_id, season, team_name, team_id,
                        group_name, standing_rank, points,
                        played, won, drawn, lost,
                        goals_for, goals_against, goal_diff, form
                    ) VALUES (
                        :league_id, :season, :team_name, :team_id,
                        :group_name, :standing_rank, :points,
                        :played, :won, :drawn, :lost,
                        :goals_for, :goals_against, :goal_diff, :form
                    )
                """), {
                    "league_id":     league_id,
                    "season":        season,
                    "team_name":     entry["team"]["name"],
                    "team_id":       entry["team"]["id"],
                    "group_name":    entry.get("group", ""),
                    "standing_rank": entry["rank"],
                    "points":        entry["points"],
                    "played":        entry["all"]["played"],
                    "won":           entry["all"]["win"],
                    "drawn":         entry["all"]["draw"],
                    "lost":          entry["all"]["lose"],
                    "goals_for":     entry["all"]["goals"]["for"],
                    "goals_against": entry["all"]["goals"]["against"],
                    "goal_diff":     entry["goalsDiff"],
                    "form":          entry.get("form", ""),
                })
        conn.commit()
    print(f"Standings gespeichert")


# main app
def main():
    print("starte historischen Daten-Load")
    print(f"Calls heute: {get_calls_today()}/{CALL_LIMIT}\n")

    for tournament in TOURNAMENTS:
        league_id = tournament["league_id"]
        season = tournament["season"]
        name = tournament["name"]

        print(f"{name} (league_id={league_id}, season={season})")

        # check limit
        if get_calls_today() >= CALL_LIMIT:
            print(f"Tageslimit erreicht. Morgen weitermachen.")
            break

        # load fixtures
        fixtures = load_fixtures(league_id, season)
        if not fixtures:
            print(f"Keine Fixtures gefunden")
            continue

        print(f" {len(fixtures)} Fixtures gefunden")

        # load standings
        load_standings(league_id, season)

        # load stats for every fixture
        saved = 0 
        skipped = 0

        for fixture in fixtures:
            if get_calls_today() >= CALL_LIMIT:
                print(f"Tageslimit erreicht. Bisher {saved} Fixtures gespeichert.")
                break

            fid = fixture["fixture"]["id"]

            # skip if already loaded
            if fixture_exists(fid):
                skipped += 1
                continue

            statistics = load_statistics(fid)
            save_fixtures(fixture, statistics, league_id, season)
            saved += 1

        print(f" {saved} Fixtures gespeichert, {skipped} übersprungen")
        print(f" Calls heute: {get_calls_today()}/{CALL_LIMIT}\n")

    print(f" Fertig. Calls heute total_ {get_calls_today()}")

if __name__ == "__main__":
    main()