import os
import time
import requests
from datetime import date
from statistics import mean
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

LEAGUE_ID = 1
SEASON = 2026
CALL_LIMIT = 7500
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

# ─── Bookmaker Config ─────────────────────────────────────────────────────────

# Whitelist: seriöse, WM-relevante Bookmaker
# Kein Parameter an API → alle kommen zurück → lokal filtern (kein extra Call)
BOOKMAKER_WHITELIST = {
    2:  "Marathonbet",   # Sharp-ish, hohe Limits
    3:  "Betfair",       # Exchange, kein Margin — beste Referenz
    4:  "Pinnacle",      # Schärfster klassischer BM, ~2% Margin
    6:  "Bwin",          # EU-Standard
    7:  "William Hill",  # UK-Standard
    8:  "Bet365",        # Grösste Reichweite
    11: "1xBet",         # Hohe Limits
    16: "Unibet",        # EU-Standard
}

# Sharp References separat speichern (niedrigster Margin = fairste Quoten)
SHARP_BOOKMAKERS = {4, 3}  # Pinnacle + Betfair

# Confidence-Schwellenwerte basierend auf Durchschnitts-Margin
MARGIN_HIGH    = 0.05   # < 5%  → Markt sehr sicher
MARGIN_MEDIUM  = 0.09   # 5-9%  → Normal
                        # > 9%  → Markt unsicher


# ─── Odds Extraction ──────────────────────────────────────────────────────────

def _normalize(home_odd: float, draw_odd: float, away_odd: float) -> dict:
    """
    Berechnet margin-bereinigte Wahrscheinlichkeiten und Margin für einen Bookmaker.
    
    Beispiel:
        Bet365: 2.10 / 3.40 / 3.20
        raw:    0.476 + 0.294 + 0.313 = 1.083  (8.3% Margin)
        norm:   43.9% / 27.1% / 28.9%          (summe = 100%)
    """
    raw_home = 1 / home_odd
    raw_draw = 1 / draw_odd
    raw_away = 1 / away_odd
    total    = raw_home + raw_draw + raw_away
    margin   = total - 1

    return {
        "prob_home": raw_home / total,
        "prob_draw": raw_draw / total,
        "prob_away": raw_away / total,
        "margin":    margin,
    }


def _extract_match_winner(bets: list) -> tuple[float, float, float] | tuple[None, None, None]:
    """Extrahiert Home/Draw/Away Quoten aus der Bets-Liste eines Bookmakers."""
    for bet in bets:
        if bet.get("name") == "Match Winner":
            home = draw = away = None
            for val in bet.get("values", []):
                v = val["value"]
                o = val["odd"]
                if v == "Home":
                    home = float(o)
                elif v == "Draw":
                    draw = float(o)
                elif v == "Away":
                    away = float(o)
            if home is not None and draw is not None and away is not None:
                return home, draw, away
    return None, None, None


def _classify_confidence(margin_avg: float) -> str:
    """Übersetzt Durchschnitts-Margin in ein lesbares Konfidenz-Label."""
    if margin_avg < MARGIN_HIGH:
        return "HIGH"
    elif margin_avg < MARGIN_MEDIUM:
        return "MEDIUM"
    else:
        return "LOW"


def extract_odds(bookmakers_response: list) -> dict | None:
    """
    Verarbeitet die vollständige Bookmaker-Response eines Fixtures.
    
    Gibt zurück:
    - home_odds / draw_odds / away_odds          Rohe Konsens-Quoten (Durchschnitt)
    - home_win_implied / draw_implied / away_win_implied  Margin-bereinigte Konsens-Wahrsch.
    - home_odds_pinnacle / draw_odds_pinnacle / away_odds_pinnacle
    - home_odds_betfair  / draw_odds_betfair  / away_odds_betfair
    - margin_avg / margin_min / margin_max
    - odds_bookmaker_count
    - market_confidence  HIGH / MEDIUM / LOW
    
    Gibt None zurück wenn keine Whitelist-BMs Daten geliefert haben.
    """
    # Gesammelte Daten pro Bookmaker
    normalized_probs = []   # margin-bereinigte Wahrscheinlichkeiten
    raw_odds_list    = []   # rohe Quoten für Durchschnitts-Quote
    margins          = []   # Margin pro BM
    pinnacle_odds    = None
    betfair_odds     = None

    for bm in bookmakers_response:
        bm_id = bm.get("id")

        if bm_id not in BOOKMAKER_WHITELIST:
            continue

        home, draw, away = _extract_match_winner(bm.get("bets", []))
        if home is None:
            continue

        norm = _normalize(home, draw, away)

        normalized_probs.append(norm)
        raw_odds_list.append((home, draw, away))
        margins.append(norm["margin"])

        # Sharp References separat merken
        if bm_id == 4:  # Pinnacle
            pinnacle_odds = (home, draw, away)
        elif bm_id == 3:  # Betfair
            betfair_odds = (home, draw, away)

    if not normalized_probs:
        return None

    count = len(normalized_probs)

    # Konsens: Durchschnitt der margin-bereinigten Wahrscheinlichkeiten
    konsens_home = mean(p["prob_home"] for p in normalized_probs)
    konsens_draw = mean(p["prob_draw"] for p in normalized_probs)
    konsens_away = mean(p["prob_away"] for p in normalized_probs)

    # Rohe Konsens-Quoten (Durchschnitt der Quoten, für Anzeige im Dashboard)
    avg_home_odd = mean(o[0] for o in raw_odds_list)
    avg_draw_odd = mean(o[1] for o in raw_odds_list)
    avg_away_odd = mean(o[2] for o in raw_odds_list)

    # Margin-Statistiken
    margin_avg = mean(margins)
    margin_min = min(margins)
    margin_max = max(margins)

    return {
        # Konsens-Quoten (Anzeige)
        "home_odds":             round(avg_home_odd, 3),
        "draw_odds":             round(avg_draw_odd, 3),
        "away_odds":             round(avg_away_odd, 3),

        # Implizite Wahrscheinlichkeiten (margin-bereinigt, für Agent)
        "home_win_implied":      round(konsens_home, 4),
        "draw_implied":          round(konsens_draw, 4),
        "away_win_implied":      round(konsens_away, 4),

        # Sharp References
        "home_odds_pinnacle":    pinnacle_odds[0] if pinnacle_odds else None,
        "draw_odds_pinnacle":    pinnacle_odds[1] if pinnacle_odds else None,
        "away_odds_pinnacle":    pinnacle_odds[2] if pinnacle_odds else None,
        "home_odds_betfair":     betfair_odds[0]  if betfair_odds  else None,
        "draw_odds_betfair":     betfair_odds[1]  if betfair_odds  else None,
        "away_odds_betfair":     betfair_odds[2]  if betfair_odds  else None,

        # Margin
        "margin_avg":            round(margin_avg, 4),
        "margin_min":            round(margin_min, 4),
        "margin_max":            round(margin_max, 4),

        # Qualität
        "odds_bookmaker_count":  count,
        "market_confidence":     _classify_confidence(margin_avg),
    }


# ─── Fetch Function ───────────────────────────────────────────────────────────

def fetch_upcoming_odds(api_get_func):
    """
    Odds für alle zukünftigen Spiele laden — kein Zeitlimit.
    Holt Quoten sobald Bookmaker sie gestellt haben.
    Nur Spiele ohne Odds oder mit Update älter als 6h.

    api_get_func: die api_get() Funktion aus run_daily.py
    """
    print("Odds für alle ausstehenden Spiele abrufen...")
    today = date.today()

    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT tf.fixture_id, tf.home_team, tf.away_team
            FROM tournament_fixtures tf
            LEFT JOIN api_predictions ap ON tf.fixture_id = ap.fixture_id
            WHERE tf.season    = :season
              AND tf.league_id = :league
              AND DATE(tf.match_date) >= :today
              AND tf.status NOT IN ('FT', 'AET', 'PEN')
              AND (
                  ap.fixture_id IS NULL
                  OR ap.home_odds IS NULL
                  OR ap.updated_at < NOW() - INTERVAL 6 HOUR
              )
            ORDER BY tf.match_date
        """), {
            "season": SEASON,
            "league": LEAGUE_ID,
            "today":  today.isoformat(),
        }).fetchall()

    if not results:
        print("  Alle Odds aktuell")
        return

    print(f"  {len(results)} Spiele brauchen Odds")
    saved = 0

    for fixture_id, home_team, away_team in results:
        # Kein bookmaker-Parameter → alle Bookmaker in einem Call
        data = api_get_func("odds", {"fixture": fixture_id})
        if not data:
            continue

        response = data.get("response", [])
        if not response:
            print(f"  {home_team} vs {away_team}: keine Odds verfügbar")
            continue

        odds = extract_odds(response[0].get("bookmakers", []))
        if odds is None:
            print(f"  {home_team} vs {away_team}: keine Whitelist-BM Daten")
            continue

        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO api_predictions (
                    fixture_id,
                    home_odds, draw_odds, away_odds,
                    home_win_implied, draw_implied, away_win_implied,
                    home_odds_pinnacle, draw_odds_pinnacle, away_odds_pinnacle,
                    home_odds_betfair,  draw_odds_betfair,  away_odds_betfair,
                    margin_avg, margin_min, margin_max,
                    odds_bookmaker_count, market_confidence
                ) VALUES (
                    :fixture_id,
                    :home_odds, :draw_odds, :away_odds,
                    :home_win_implied, :draw_implied, :away_win_implied,
                    :home_odds_pinnacle, :draw_odds_pinnacle, :away_odds_pinnacle,
                    :home_odds_betfair,  :draw_odds_betfair,  :away_odds_betfair,
                    :margin_avg, :margin_min, :margin_max,
                    :odds_bookmaker_count, :market_confidence
                )
                ON DUPLICATE KEY UPDATE
                    home_odds             = :home_odds,
                    draw_odds             = :draw_odds,
                    away_odds             = :away_odds,
                    home_win_implied      = :home_win_implied,
                    draw_implied          = :draw_implied,
                    away_win_implied      = :away_win_implied,
                    home_odds_pinnacle    = :home_odds_pinnacle,
                    draw_odds_pinnacle    = :draw_odds_pinnacle,
                    away_odds_pinnacle    = :away_odds_pinnacle,
                    home_odds_betfair     = :home_odds_betfair,
                    draw_odds_betfair     = :draw_odds_betfair,
                    away_odds_betfair     = :away_odds_betfair,
                    margin_avg            = :margin_avg,
                    margin_min            = :margin_min,
                    margin_max            = :margin_max,
                    odds_bookmaker_count  = :odds_bookmaker_count,
                    market_confidence     = :market_confidence,
                    updated_at            = CURRENT_TIMESTAMP
            """), {"fixture_id": fixture_id, **odds})
            conn.commit()

        saved += 1
        print(
            f"  {home_team} vs {away_team}: "
            f"{odds['home_odds']} / {odds['draw_odds']} / {odds['away_odds']}  "
            f"| impl. {odds['home_win_implied']*100:.1f}% / "
            f"{odds['draw_implied']*100:.1f}% / "
            f"{odds['away_win_implied']*100:.1f}%  "
            f"| margin {odds['margin_avg']*100:.1f}%  "
            f"| {odds['market_confidence']} "
            f"({odds['odds_bookmaker_count']} BMs)"
        )

    print(f"  {saved} Odds gespeichert")