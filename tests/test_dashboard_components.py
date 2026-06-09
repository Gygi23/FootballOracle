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
        count = source.count(field)
        assert count >= 2, (
            f"'{field}' muss in beiden SQL-Branches vorkommen, gefunden: {count} Mal. "
            f"Bitte beide SELECT-Statements in mysql_tools.py ergänzen."
        )


# ── Task 2: odds_tiles_html ───────────────────────────────────────────────────

def _import_odds_tiles_html():
    """Lazy import — Funktion existiert erst nach Task 2."""
    from agent.dashboard.dashboard import odds_tiles_html
    return odds_tiles_html


def test_odds_tiles_html_contains_team_names():
    """Team-Namen müssen in der Kopfzeile erscheinen."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20)
    assert "BRAZIL" in html.upper()
    assert "MOROCCO" in html.upper()


def test_odds_tiles_html_shows_probabilities_not_only_odds():
    """Die Kacheln zeigen Prozentwerte (%), nicht nur rohe Quoten."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20)
    assert "%" in html


def test_odds_tiles_html_shows_raw_odds():
    """Rohe Quoten erscheinen als Sekundärinfo unter den Kacheln."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20)
    assert "1.65" in html
    assert "3.80" in html
    assert "5.20" in html


def test_odds_tiles_html_no_unentschieden_label():
    """'Unentschieden' darf NICHT im Header erscheinen (nur Teamnamen)."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20)
    assert "Unentschieden" not in html
    assert "UNENTSCHIEDEN" not in html


def test_odds_tiles_html_accepts_precomputed_probs():
    """Wenn h_prob/d_prob/a_prob übergeben: diese Werte erscheinen in den Kacheln."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20,
               h_prob=0.61, d_prob=0.26, a_prob=0.13)
    assert "61%" in html
    assert "26%" in html
    assert "13%" in html


def test_odds_tiles_html_meta_string_rendered():
    """Meta-String (Bookmakers, Margin) wird am Ende gerendert."""
    fn = _import_odds_tiles_html()
    html = fn("Konsens-Quoten", "Brazil", "Morocco",
               h_odd=1.65, d_odd=3.80, a_odd=5.20,
               meta="Konsens · 6 Bookmakers · Margin 4.2%")
    assert "6 Bookmakers" in html
    assert "4.2%" in html
