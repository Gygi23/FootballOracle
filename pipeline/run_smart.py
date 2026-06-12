"""
run_smart.py — Intelligenter Pipeline-Scheduler

Wird alle 5 Minuten via Cron ausgeführt und entscheidet selbst was zu tun ist:

  Immer (alle 4h)        → Voller Run (Odds, Standings, Predictions, KPIs)
  2h vor Anpfiff         → Odds refresh (Markt öffnet sich)
  30min vor Anpfiff      → Odds refresh (Aufstellungen bekannt, Quoten bewegen sich)
  Spiel läuft            → Scores updaten (alle 2min via Cron)
  Spiel gerade beendet   → Standings + KPIs sofort aktualisieren

Setup (macOS/Linux crontab):
    crontab -e
    */5 * * * * cd /pfad/zu/footballAI && .venv/bin/python pipeline/run_smart.py >> logs/smart.log 2>&1

Railway Cron Schedule: */5 * * * *  (Railway minimum = 5 Min)
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

# Sowohl Projekt-Root als auch pipeline/-Verzeichnis zum Path hinzufügen
# (nötig damit 'from run_daily import ...' funktioniert, egal von wo das Script gestartet wird)
_this_dir    = os.path.dirname(os.path.abspath(__file__))          # .../pipeline/
_project_root = os.path.dirname(_this_dir)                          # .../footballAI/
sys.path.insert(0, _this_dir)
sys.path.insert(0, _project_root)

from agent.tools.mysql_tools import get_engine
engine = get_engine()

LEAGUE_ID = 1
SEASON    = 2026

# Statuses die bedeuten "Spiel läuft noch"
LIVE_STATUSES     = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE'}
# Statuses die bedeuten "Spiel beendet"
FINISHED_STATUSES = {'FT', 'AET', 'PEN'}

FULL_UPDATE_INTERVAL_HOURS = 4   # Voller Run alle N Stunden
LOG_ENDPOINT = 'smart_runner'


# ─── DB-Abfragen (0 API Calls) ────────────────────────────────────────────────

def get_live_fixtures() -> list[dict]:
    """Spiele die gerade laufen (Status = live) ODER deren Anpfiff laut Spielplan bereits war."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT fixture_id, home_team, away_team, status, match_date
            FROM tournament_fixtures
            WHERE league_id = :league AND season = :season
              AND (
                -- Bereits im Live-Status in der DB
                status IN ('1H','HT','2H','ET','BT','P','INT','LIVE')
                -- ODER: Anpfiff war vor ≤110 Minuten, DB-Status noch NS
                OR (status = 'NS'
                    AND match_date < NOW()
                    AND match_date > NOW() - INTERVAL 110 MINUTE)
              )
        """), {"league": LEAGUE_ID, "season": SEASON}).fetchall()
    return [dict(r._mapping) for r in rows]


def get_upcoming_fixtures(within_minutes: int) -> list[dict]:
    """Spiele die in den nächsten N Minuten beginnen (Status = NS)."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT fixture_id, home_team, away_team, match_date
            FROM tournament_fixtures
            WHERE league_id = :league AND season = :season
              AND status = 'NS'
              AND match_date BETWEEN NOW() AND NOW() + INTERVAL :minutes MINUTE
        """), {"league": LEAGUE_ID, "season": SEASON, "minutes": within_minutes}).fetchall()
    return [dict(r._mapping) for r in rows]


def get_missed_fixtures() -> list[dict]:
    """
    Spiele deren Anpfiff >115 Min zurückliegt aber Status noch NS ist.
    → Passiert wenn der Cron während des Spiels nicht lief oder den Kickoff verpasst hat.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT fixture_id, home_team, away_team, status, match_date
            FROM tournament_fixtures
            WHERE league_id = :league AND season = :season
              AND status = 'NS'
              AND match_date < NOW() - INTERVAL 115 MINUTE
        """), {"league": LEAGUE_ID, "season": SEASON}).fetchall()
    return [dict(r._mapping) for r in rows]


def get_just_finished_fixtures() -> list[dict]:
    """
    Spiele die heute beendet wurden und deren KPIs noch nicht aktualisiert wurden.
    Erkennung: status IN (FT/AET/PEN) UND updated_at nach letztem KPI-Run.
    """
    last_kpi_run = get_last_run_time('kpi_update')
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT fixture_id, home_team, away_team, status
            FROM tournament_fixtures
            WHERE league_id  = :league AND season = :season
              AND status     IN ('FT', 'AET', 'PEN')
              AND DATE(match_date) = CURDATE()
              AND updated_at > :last_kpi
        """), {
            "league":   LEAGUE_ID,
            "season":   SEASON,
            "last_kpi": last_kpi_run,
        }).fetchall()
    return [dict(r._mapping) for r in rows]


def get_last_run_time(endpoint: str) -> datetime:
    """Letzten Ausführungszeitpunkt aus api_log lesen (immer naive UTC)."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT last_called FROM api_log
            WHERE endpoint = :ep
            ORDER BY last_called DESC LIMIT 1
        """), {"ep": endpoint}).fetchone()
    if row:
        ts = row[0]
        # Immer naive datetime zurückgeben (DB speichert naive UTC)
        if isinstance(ts, datetime):
            return ts.replace(tzinfo=None)
        return ts
    # Noch nie gelaufen → sehr alter Zeitpunkt (naive)
    return datetime(2000, 1, 1)


def log_run(endpoint: str):
    """Ausführungszeitpunkt in api_log speichern."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO api_log (endpoint, calls_today, last_called)
            VALUES (:ep, 0, NOW())
            ON DUPLICATE KEY UPDATE last_called = NOW()
        """), {"ep": endpoint})
        conn.commit()


def hours_since_last_full_run() -> float:
    last = get_last_run_time('full_pipeline')           # naive UTC
    now  = datetime.now(timezone.utc).replace(tzinfo=None)  # auch naive UTC
    return (now - last).total_seconds() / 3600


# ─── Pipeline-Aktionen ────────────────────────────────────────────────────────

def run_full_pipeline():
    """Voller Run: Standings, Fixtures, Predictions, Odds, KPIs."""
    print("[smart] Voller Pipeline-Run...")
    from run_daily import main as daily_main
    daily_main()
    log_run('full_pipeline')
    log_run('kpi_update')


def run_odds_refresh():
    """Nur Odds und Predictions updaten."""
    print("[smart] Odds-Refresh (pre-game)...")
    import requests, time as _time
    from run_daily import api_get, fetch_upcoming_predictions
    from odds_extractor import fetch_upcoming_odds
    fetch_upcoming_predictions()
    fetch_upcoming_odds(api_get)


def run_scores_update():
    """Scores + alle Spielstatistiken laufender Spiele updaten."""
    from fetch_live import run_live_update
    last_snapshot = get_last_run_time('last_snapshot')
    new_snapshot_time = run_live_update(last_snapshot)
    if new_snapshot_time != last_snapshot:
        log_run('last_snapshot')


def run_post_game_update():
    """Nach Spielende: Standings + KPIs + ELO aktualisieren."""
    print("[smart] Post-Game-Update (Standings + KPIs + ELO)...")
    from run_daily import update_standings
    from compute_kpis import run as update_kpis
    from compute_elo import run as update_elo
    update_standings()
    update_kpis()
    update_elo()
    log_run('kpi_update')


# ─── Haupt-Entscheidungslogik ─────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    print(f"[smart] {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # 0. Verpasste Spiele: Anpfiff >115min her, DB-Status noch NS → Nachzug
    missed = get_missed_fixtures()
    if missed:
        names = ', '.join(f"{f['home_team']} vs {f['away_team']}" for f in missed)
        print(f"[smart] Verpasst (nie getrackt): {names} → Fixture-Update")
        from run_daily import update_today_fixtures
        update_today_fixtures()
        run_post_game_update()

    # 1. Spiele gerade live? → Scores sofort updaten
    live = get_live_fixtures()
    if live:
        names = ', '.join(f"{f['home_team']} vs {f['away_team']}" for f in live)
        print(f"[smart] Live: {names}")
        run_scores_update()

    # 2. Spiele gerade beendet? → Standings + KPIs updaten
    just_finished = get_just_finished_fixtures()
    if just_finished:
        names = ', '.join(f"{f['home_team']} vs {f['away_team']} ({f['status']})" for f in just_finished)
        print(f"[smart] Gerade beendet: {names}")
        run_post_game_update()

    # 3. Spiele in <30min? → Odds refresh (Aufstellungen bekannt)
    kickoff_30min = get_upcoming_fixtures(within_minutes=30)
    if kickoff_30min and not live:
        names = ', '.join(f"{f['home_team']} vs {f['away_team']}" for f in kickoff_30min)
        print(f"[smart] Anpfiff in <30min: {names} → Odds refresh")
        run_odds_refresh()
        return

    # 4. Spiele in <2h? → Odds refresh (Markt öffnet sich), nur alle 30min
    kickoff_2h = get_upcoming_fixtures(within_minutes=120)
    if kickoff_2h and not live:
        last_odds = get_last_run_time('odds_refresh_2h')  # naive UTC
        now_naive = now.replace(tzinfo=None)
        if (now_naive - last_odds).total_seconds() > 1800:
            names = ', '.join(f"{f['home_team']} vs {f['away_team']}" for f in kickoff_2h)
            print(f"[smart] Anpfiff in <2h: {names} → Odds refresh")
            run_odds_refresh()
            log_run('odds_refresh_2h')
            return  # nur return wenn tatsächlich ein Refresh lief

    # 5. Voller Run alle 4 Stunden (ruhige Phase)
    if not live and hours_since_last_full_run() >= FULL_UPDATE_INTERVAL_HOURS:
        print(f"[smart] {FULL_UPDATE_INTERVAL_HOURS}h-Intervall erreicht → voller Run")
        run_full_pipeline()
        return

    print("[smart] Nichts zu tun.")


if __name__ == "__main__":
    main()
