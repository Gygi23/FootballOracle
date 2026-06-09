"""
Unit-Tests für Dashboard-Komponenten (pure Funktionen ohne DB/Streamlit).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ── Task 1: SQL-Felder in get_api_predictions ────────────────────────────────

import inspect
from agent.tools.mysql_tools import get_api_predictions

REQUIRED_FIELDS = [
    "home_win_implied", "draw_implied", "away_win_implied",
    "home_odds_pinnacle", "draw_odds_pinnacle", "away_odds_pinnacle",
    "home_odds_betfair", "draw_odds_betfair", "away_odds_betfair",
    "margin_avg", "odds_bookmaker_count", "market_confidence",
]

def test_get_api_predictions_sql_contains_required_fields():
    """
    get_api_predictions() muss alle erweiterten Odds-Felder im SQL-String enthalten.
    Wir prüfen den Quellcode der Funktion (keine DB-Verbindung nötig).
    """
    source = inspect.getsource(get_api_predictions)
    for field in REQUIRED_FIELDS:
        assert field in source, (
            f"get_api_predictions() SQL fehlt Feld: '{field}'. "
            f"Bitte SELECT in mysql_tools.py:~614 ergänzen."
        )
