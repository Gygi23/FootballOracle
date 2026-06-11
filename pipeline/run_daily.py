import os
import sys
import time
import requests
from datetime import date, timedelta
from sqlalchemy import text
from dotenv import load_dotenv
from odds_extractor import fetch_upcoming_odds
from compute_kpis import run as update_team_stats
from compute_elo import run as update_elo

load_dotenv()

# Projekt-Root zum Path hinzufügen damit agent-Package findbar ist
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools.mysql_tools import get_engine

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

LEAGUE_ID = 1
SEASON = 2026
CALL_LIMIT = 7500
LOOKAHEAD_DAYS = 3  # Predictions + Odds für nächste 3 Tage

engine = get_engine()


# ─── API Call Tracker ─────────────────────────────────────────────────────────

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
        print("  Tageslimit erreicht.")
        return None

    response = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS, params=params)
    increment_calls(1)
    time.sleep(2)

    if response.status_code == 429:
        print("  Rate limit — warte 60s...")
        time.sleep(60)
        return None

    if response.status_code != 200:
        print(f"  API Fehler {response.status_code}: {endpoint}")
        return None

    return response.json()


# ─── Standings ────────────────────────────────────────────────────────────────

def update_standings():
    print("Standings updaten...")
    data = api_get("standings", {"league": LEAGUE_ID, "season": SEASON})
    if not data:
        return

    groups = data.get("response", [])
    if not groups:
        print("  Keine Standings gefunden")
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
    print("  Standings gespeichert")


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def update_today_fixtures():
    """Scores, Status und Spielstatistiken heutiger Spiele updaten."""
    print("Heutige Fixtures updaten...")
    today = date.today().isoformat()

    data = api_get("fixtures", {
        "league": LEAGUE_ID,
        "season": SEASON,
        "date":   today,
    })
    if not data:
        return

    fixtures = data.get("response", [])
    if not fixtures:
        print("  Keine Spiele heute")
        return

    # Fixture IDs holen und mit Stats neu laden (1 Call für alle)
    ids_str = "-".join(str(fx["fixture"]["id"]) for fx in fixtures)
    data_with_stats = api_get("fixtures", {"ids": ids_str})
    if data_with_stats:
        fixtures = data_with_stats.get("response", fixtures)

    from fetch_live import update_fixture
    for fx in fixtures:
        update_fixture(fx)

    print(f"  {len(fixtures)} Fixtures + Statistiken geupdated")


def ensure_upcoming_fixtures():
    """
    Fixtures der nächsten LOOKAHEAD_DAYS Tage in DB sicherstellen.
    Fängt den Fall ab dass load_tournament_data.py noch nicht alle
    zukünftigen Spiele geladen hat (z.B. KO-Phase wird erst generiert
    wenn Gruppenphase abgeschlossen ist).
    """
    print(f"Upcoming Fixtures prüfen (nächste {LOOKAHEAD_DAYS} Tage)...")
    today  = date.today()
    cutoff = today + timedelta(days=LOOKAHEAD_DAYS)

    data = api_get("fixtures", {
        "league": LEAGUE_ID,
        "season": SEASON,
        "from":   today.isoformat(),
        "to":     cutoff.isoformat(),
    })
    if not data:
        return

    fixtures = data.get("response", [])
    if not fixtures:
        print("  Keine kommenden Spiele in diesem Zeitraum")
        return

    inserted = 0
    with engine.connect() as conn:
        for fx in fixtures:
            result = conn.execute(text("""
                INSERT IGNORE INTO tournament_fixtures (
                    fixture_id, league_id, season,
                    home_team, away_team, match_date, stage, status
                ) VALUES (
                    :fixture_id, :league_id, :season,
                    :home_team, :away_team, :match_date, :stage, :status
                )
            """), {
                "fixture_id": fx["fixture"]["id"],
                "league_id":  LEAGUE_ID,
                "season":     SEASON,
                "home_team":  fx["teams"]["home"]["name"],
                "away_team":  fx["teams"]["away"]["name"],
                "match_date": fx["fixture"]["date"],
                "stage":      fx["league"].get("round", ""),
                "status":     fx["fixture"]["status"]["short"],
            })
            if result.rowcount > 0:
                inserted += 1
        conn.commit()

    if inserted:
        print(f"  {inserted} neue Fixtures eingefügt")
    else:
        print(f"  Alle {len(fixtures)} Fixtures bereits in DB")


# ─── Predictions ──────────────────────────────────────────────────────────────

def fetch_upcoming_predictions():
    """
    Predictions für Spiele der nächsten LOOKAHEAD_DAYS Tage.
    Nur Spiele ohne Prediction oder mit Update älter als 24h.
    """
    print(f"Predictions für nächste {LOOKAHEAD_DAYS} Tage abrufen...")
    today  = date.today()
    cutoff = today + timedelta(days=LOOKAHEAD_DAYS)

    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT tf.fixture_id, tf.home_team, tf.away_team
            FROM tournament_fixtures tf
            LEFT JOIN api_predictions ap ON tf.fixture_id = ap.fixture_id
            WHERE tf.season    = :season
              AND tf.league_id = :league
              AND DATE(tf.match_date) BETWEEN :today AND :cutoff
              AND tf.status NOT IN ('FT', 'AET', 'PEN')
              AND (
                  ap.fixture_id IS NULL
                  OR ap.home_win_pct IS NULL
                  OR ap.updated_at < NOW() - INTERVAL 24 HOUR
              )
        """), {
            "season": SEASON,
            "league": LEAGUE_ID,
            "today":  today.isoformat(),
            "cutoff": cutoff.isoformat(),
        }).fetchall()

    if not results:
        print("  Alle Predictions aktuell")
        return

    print(f"  {len(results)} Spiele brauchen Predictions")
    saved = 0

    for fixture_id, home_team, away_team in results:
        data = api_get("predictions", {"fixture": fixture_id})
        if not data:
            continue

        response = data.get("response", [])
        if not response:
            continue

        pred = response[0].get("predictions", {})

        if pred.get("advice") in ("No predictions available", None):
            print(f"  {home_team} vs {away_team}: noch keine Prediction")
            continue

        percent = pred.get("percent", {})
        home_pct = float(percent.get("home", "0%").replace("%", ""))
        draw_pct = float(percent.get("draw", "0%").replace("%", ""))
        away_pct = float(percent.get("away", "0%").replace("%", ""))
        winner   = pred.get("winner", {})

        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO api_predictions (
                    fixture_id, predicted_winner,
                    home_win_pct, draw_pct, away_win_pct, advice
                ) VALUES (
                    :fixture_id, :predicted_winner,
                    :home_win_pct, :draw_pct, :away_win_pct, :advice
                )
                ON DUPLICATE KEY UPDATE
                    predicted_winner = :predicted_winner,
                    home_win_pct     = :home_win_pct,
                    draw_pct         = :draw_pct,
                    away_win_pct     = :away_win_pct,
                    advice           = :advice,
                    updated_at       = CURRENT_TIMESTAMP
            """), {
                "fixture_id":       fixture_id,
                "predicted_winner": winner.get("name") if winner else None,
                "home_win_pct":     home_pct,
                "draw_pct":         draw_pct,
                "away_win_pct":     away_pct,
                "advice":           pred.get("advice"),
            })
            conn.commit()
        saved += 1
        print(f"  {home_team} vs {away_team}: {home_pct:.0f}% / {draw_pct:.0f}% / {away_pct:.0f}%")

    print(f"  {saved} Predictions gespeichert")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"footballAI – run_daily.py [{date.today()}]")
    print(f"Calls heute: {get_calls_today()}/{CALL_LIMIT}\n")

    # 1. Gruppenstandings
    update_standings()
    print()

    # 2. Heutige Scores updaten
    update_today_fixtures()
    print()

    # 3. Sicherstellen dass kommende Fixtures in DB sind
    ensure_upcoming_fixtures()
    print()

    # 4. Predictions für nächste 3 Tage
    fetch_upcoming_predictions()
    print()

    # 5. Odds für nächste 3 Tage (via odds_extractor.py)
    fetch_upcoming_odds(api_get)
    print()

    # 6. Team-KPIs aktualisieren (historisch + abgeschlossene WM-2026-Spiele)
    update_team_stats()
    print()

    # 7. ELO-Ratings neu berechnen
    update_elo()
    print()

    print(f"Fertig. Calls heute total: {get_calls_today()}")


if __name__ == "__main__":
    main()