import sys
import os
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from agent.tools.mysql_tools import get_engine

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

LEAGUE_ID = 1
SEASON = 2026
POLL_INTERVAL = 60        # Sekunden zwischen Live-Updates
SNAPSHOT_INTERVAL = 900   # Sekunden zwischen Snapshots (15 Min)
CALL_LIMIT = 7500

engine = get_engine()


# api call tracker

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
        print(f"Tageslimit erreicht.")
        return None
 
    response = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS, params=params)
    increment_calls(1)
 
    if response.status_code == 429:
        print("Rate limit — warte 60s...")
        time.sleep(60)
        return None
 
    if response.status_code != 200:
        print(f"API Fehler {response.status_code}: {endpoint}")
        return None
 
    return response.json()


# help functions

def get_stat(statistics: list, team_index: int, stat_type: str):
    try:
        stats = statistics[team_index]["statistics"]
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
    
def get_next_kickoff() -> datetime | None:
    with engine.connect() as conn:
        result = conn.execute(text(""" 
        SELECT match_date FROM tournament_fixtures
        WHERE season = :season AND league_id = :league
        AND status = 'NS' AND match_date > NOW()
        ORDER BY match_date ASC
        LIMIT 1
        """), {"season": SEASON, "league": LEAGUE_ID}).fetchone()
    return result[0] if result else None

def get_live_fixture_ids() -> list[int]:
    data = api_get("fixtures", {
        "league": LEAGUE_ID,
        "season": SEASON,
        "status": "1H-HT-2H-ET-P-BT"
    })
    if not data:
        return []
    return [f["fixture"]["id"] for f in data.get("response", [])]

def is_match_day() -> bool:
    return len(get_live_fixture_ids()) > 0

#save data

def update_fixture(fixture: dict):
    """Updated tournament_fixtures mit aktuellem Stand."""
    fid = fixture["fixture"]["id"]
    stats = fixture.get("statistics", [])
 
    row = {
        "fixture_id":              fid,
        "status":                  fixture["fixture"]["status"]["short"],
        "home_score":              fixture["goals"]["home"],
        "away_score":              fixture["goals"]["away"],
        "home_possession":         get_stat(stats, 0, "Ball Possession"),
        "away_possession":         get_stat(stats, 1, "Ball Possession"),
        "home_shots_on_target":    get_stat(stats, 0, "Shots on Goal"),
        "away_shots_on_target":    get_stat(stats, 1, "Shots on Goal"),
        "home_shots_off_target":   get_stat(stats, 0, "Shots off Goal"),
        "away_shots_off_target":   get_stat(stats, 1, "Shots off Goal"),
        "home_total_shots":        get_stat(stats, 0, "Total Shots"),
        "away_total_shots":        get_stat(stats, 1, "Total Shots"),
        "home_blocked_shots":      get_stat(stats, 0, "Blocked Shots"),
        "away_blocked_shots":      get_stat(stats, 1, "Blocked Shots"),
        "home_shots_insidebox":    get_stat(stats, 0, "Shots insidebox"),
        "away_shots_insidebox":    get_stat(stats, 1, "Shots insidebox"),
        "home_shots_outsidebox":   get_stat(stats, 0, "Shots outsidebox"),
        "away_shots_outsidebox":   get_stat(stats, 1, "Shots outsidebox"),
        "home_saves":              get_stat(stats, 0, "Goalkeeper Saves"),
        "away_saves":              get_stat(stats, 1, "Goalkeeper Saves"),
        "home_fouls":              get_stat(stats, 0, "Fouls"),
        "away_fouls":              get_stat(stats, 1, "Fouls"),
        "home_corners":            get_stat(stats, 0, "Corner Kicks"),
        "away_corners":            get_stat(stats, 1, "Corner Kicks"),
        "home_offsides":           get_stat(stats, 0, "Offsides"),
        "away_offsides":           get_stat(stats, 1, "Offsides"),
        "home_yellow_cards":       get_stat(stats, 0, "Yellow Cards"),
        "away_yellow_cards":       get_stat(stats, 1, "Yellow Cards"),
        "home_red_cards":          get_stat(stats, 0, "Red Cards"),
        "away_red_cards":          get_stat(stats, 1, "Red Cards"),
        "home_total_passes":       get_stat(stats, 0, "Total passes"),
        "away_total_passes":       get_stat(stats, 1, "Total passes"),
        "home_passes_accurate":    get_stat(stats, 0, "Passes accurate"),
        "away_passes_accurate":    get_stat(stats, 1, "Passes accurate"),
        "home_passes_pct":         get_stat(stats, 0, "Passes %"),
        "away_passes_pct":         get_stat(stats, 1, "Passes %"),
    }
 
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE tournament_fixtures SET
                status = :status,
                home_score = :home_score,
                away_score = :away_score,
                home_possession = :home_possession,
                away_possession = :away_possession,
                home_shots_on_target = :home_shots_on_target,
                away_shots_on_target = :away_shots_on_target,
                home_shots_off_target = :home_shots_off_target,
                away_shots_off_target = :away_shots_off_target,
                home_total_shots = :home_total_shots,
                away_total_shots = :away_total_shots,
                home_blocked_shots = :home_blocked_shots,
                away_blocked_shots = :away_blocked_shots,
                home_shots_insidebox = :home_shots_insidebox,
                away_shots_insidebox = :away_shots_insidebox,
                home_shots_outsidebox = :home_shots_outsidebox,
                away_shots_outsidebox = :away_shots_outsidebox,
                home_saves = :home_saves,
                away_saves = :away_saves,
                home_fouls = :home_fouls,
                away_fouls = :away_fouls,
                home_corners = :home_corners,
                away_corners = :away_corners,
                home_offsides = :home_offsides,
                away_offsides = :away_offsides,
                home_yellow_cards = :home_yellow_cards,
                away_yellow_cards = :away_yellow_cards,
                home_red_cards = :home_red_cards,
                away_red_cards = :away_red_cards,
                home_total_passes = :home_total_passes,
                away_total_passes = :away_total_passes,
                home_passes_accurate = :home_passes_accurate,
                away_passes_accurate = :away_passes_accurate,
                home_passes_pct = :home_passes_pct,
                away_passes_pct = :away_passes_pct
            WHERE fixture_id = :fixture_id
        """), row)
        conn.commit()
 
 
def save_snapshot(fixture: dict):
    """Speichert einen Zeitpunkt-Snapshot in fixture_snapshots."""
    fid = fixture["fixture"]["id"]
    minute = fixture["fixture"]["status"].get("elapsed") or 0
    stats = fixture.get("statistics", [])
 
    row = {
        "fixture_id":              fid,
        "minute":                  minute,
        "home_team":               fixture["teams"]["home"]["name"],
        "away_team":               fixture["teams"]["away"]["name"],
        "home_score":              fixture["goals"]["home"],
        "away_score":              fixture["goals"]["away"],
        "home_possession":         get_stat(stats, 0, "Ball Possession"),
        "away_possession":         get_stat(stats, 1, "Ball Possession"),
        "home_shots_on_target":    get_stat(stats, 0, "Shots on Goal"),
        "away_shots_on_target":    get_stat(stats, 1, "Shots on Goal"),
        "home_shots_off_target":   get_stat(stats, 0, "Shots off Goal"),
        "away_shots_off_target":   get_stat(stats, 1, "Shots off Goal"),
        "home_shots_total":        get_stat(stats, 0, "Total Shots"),
        "away_shots_total":        get_stat(stats, 1, "Total Shots"),
        "home_shots_insidebox":    get_stat(stats, 0, "Shots insidebox"),
        "away_shots_insidebox":    get_stat(stats, 1, "Shots insidebox"),
        "home_shots_outsidebox":   get_stat(stats, 0, "Shots outsidebox"),
        "away_shots_outsidebox":   get_stat(stats, 1, "Shots outsidebox"),
        "home_blocked_shots":      get_stat(stats, 0, "Blocked Shots"),
        "away_blocked_shots":      get_stat(stats, 1, "Blocked Shots"),
        "home_corners":            get_stat(stats, 0, "Corner Kicks"),
        "away_corners":            get_stat(stats, 1, "Corner Kicks"),
        "home_fouls":              get_stat(stats, 0, "Fouls"),
        "away_fouls":              get_stat(stats, 1, "Fouls"),
        "home_offsides":           get_stat(stats, 0, "Offsides"),
        "away_offsides":           get_stat(stats, 1, "Offsides"),
        "home_yellow_cards":       get_stat(stats, 0, "Yellow Cards"),
        "away_yellow_cards":       get_stat(stats, 1, "Yellow Cards"),
        "home_red_cards":          get_stat(stats, 0, "Red Cards"),
        "away_red_cards":          get_stat(stats, 1, "Red Cards"),
        "home_saves":              get_stat(stats, 0, "Goalkeeper Saves"),
        "away_saves":              get_stat(stats, 1, "Goalkeeper Saves"),
        "home_total_passes":       get_stat(stats, 0, "Total passes"),
        "away_total_passes":       get_stat(stats, 1, "Total passes"),
        "home_passes_accurate":    get_stat(stats, 0, "Passes accurate"),
        "away_passes_accurate":    get_stat(stats, 1, "Passes accurate"),
        "home_passes_pct":         get_stat(stats, 0, "Passes %"),
        "away_passes_pct":         get_stat(stats, 1, "Passes %"),
    }
 
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO fixture_snapshots (
                fixture_id, minute, home_team, away_team,
                home_score, away_score,
                home_possession, away_possession,
                home_shots_on_target, away_shots_on_target,
                home_shots_off_target, away_shots_off_target,
                home_shots_total, away_shots_total,
                home_shots_insidebox, away_shots_insidebox,
                home_blocked_shots, away_blocked_shots,
                home_corners, away_corners,
                home_fouls, away_fouls,
                home_offsides, away_offsides,
                home_yellow_cards, away_yellow_cards,
                home_red_cards, away_red_cards,
                home_saves, away_saves,
                home_total_passes, away_total_passes,
                home_passes_accurate, away_passes_accurate,
                home_passes_pct, away_passes_pct
            ) VALUES (
                :fixture_id, :minute, :home_team, :away_team,
                :home_score, :away_score,
                :home_possession, :away_possession,
                :home_shots_on_target, :away_shots_on_target,
                :home_shots_off_target, :away_shots_off_target,
                :home_shots_total, :away_shots_total,
                :home_shots_insidebox, :away_shots_insidebox,
                :home_blocked_shots, :away_blocked_shots,
                :home_corners, :away_corners,
                :home_fouls, :away_fouls,
                :home_offsides, :away_offsides,
                :home_yellow_cards, :away_yellow_cards,
                :home_red_cards, :away_red_cards,
                :home_saves, :away_saves,
                :home_total_passes, :away_total_passes,
                :home_passes_accurate, :away_passes_accurate,
                :home_passes_pct, :away_passes_pct
            )
        """), row)
        conn.commit()


def update_standings():
    """Updated Gruppenranglisten nach Spielende."""
    data = api_get("standings", {"league": LEAGUE_ID, "season": SEASON})
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
                    INSERT INTO tournament_standings (
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
                    ON DUPLICATE KEY UPDATE
                        standing_rank = :standing_rank,
                        points        = :points,
                        played        = :played,
                        won           = :won,
                        drawn         = :drawn,
                        lost          = :lost,
                        goals_for     = :goals_for,
                        goals_against = :goals_against,
                        goal_diff     = :goal_diff,
                        form          = :form,
                        updated_at    = CURRENT_TIMESTAMP
                """), {
                    "league_id":     LEAGUE_ID,
                    "season":        SEASON,
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
    print(f"  Standings geupdated")

# live update

def run_live_update(last_snapshot_time: datetime) -> datetime:
    fixture_ids = get_live_fixture_ids()
    if not fixture_ids:
        return last_snapshot_time

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(fixture_ids)} Live-Spiel(e)")

    ids_str = "-".join(str(fid) for fid in fixture_ids)
    data = api_get("fixtures", {"ids": ids_str})
    if not data:
        return last_snapshot_time

    fixtures = data.get("response", [])
    now = datetime.now()
    do_snapshot = (now - last_snapshot_time).total_seconds() >= SNAPSHOT_INTERVAL
    standings_updated = False

    for fixture in fixtures:
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        hs = fixture["goals"]["home"]
        aws = fixture["goals"]["away"]
        minute = fixture["fixture"]["status"].get("elapsed", "?")
        status = fixture["fixture"]["status"]["short"]
        print(f"  {home} {hs}:{aws} {away} [{minute}']")

        update_fixture(fixture)

        if do_snapshot:
            save_snapshot(fixture)

        if status in ["FT", "AET", "PEN"] and not standings_updated:
            print(f"  Spiel beendet → Standings updaten")
            update_standings()
            standings_updated = True

    if do_snapshot:
        print(f"  Snapshot gespeichert")
        return now

    return last_snapshot_time

# main loop

def main():
    print("footballAI – fetch_live.py gestartet")
    print(f"Calls heute: {get_calls_today()}/{CALL_LIMIT}\n")
 
    last_snapshot_time = datetime.now() - timedelta(seconds=SNAPSHOT_INTERVAL)
 
    while True:
        # Läuft gerade ein Spiel?
        if is_match_day():
            last_snapshot_time = run_live_update(last_snapshot_time)
            time.sleep(POLL_INTERVAL)
            continue
 
        # Wann ist der nächste Anpfiff?
        next_kickoff = get_next_kickoff()
        if not next_kickoff:
            print("Keine weiteren WM 2026 Spiele — fertig.")
            break
 
        # Warten bis 2 Minuten vor Anpfiff
        wait_seconds = (next_kickoff - datetime.now()).total_seconds() - 120
        if wait_seconds > 60:
            wake_time = next_kickoff - timedelta(seconds=120)
            print(f"Nächstes Spiel: {next_kickoff.strftime('%d.%m. %H:%M')} "
                  f"— warte bis {wake_time.strftime('%H:%M')}")
            time.sleep(wait_seconds)
        else:
            # Kurz vor Anpfiff — alle 30 Sek prüfen
            time.sleep(30)
 
 
if __name__ == "__main__":
    main()