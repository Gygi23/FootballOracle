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


# ── Task 3: build_match_card_label ────────────────────────────────────────────

def _import_build_match_card_label():
    from agent.dashboard.dashboard import build_match_card_label
    return build_match_card_label


def test_ns_match_shows_vs_not_score():
    """Status NS → kein Score, zeigt 'vs'."""
    fn = _import_build_match_card_label()
    label = fn(home="Mexico", away="South Africa",
                home_score=0, away_score=0,
                status="NS", stage="Group Stage - 1",
                match_date="2026-06-11 21:00", group="Group A")
    assert "vs" in label
    assert "0 : 0" not in label


def test_live_match_shows_score():
    """Status 1H → Score wird angezeigt."""
    fn = _import_build_match_card_label()
    label = fn(home="Brazil", away="Morocco",
                home_score=2, away_score=1,
                status="1H", stage="Group Stage - 1",
                match_date="2026-06-18 18:00", group="Group C")
    assert "2" in label and "1" in label


def test_ft_match_shows_score():
    """Status FT → Score wird angezeigt."""
    fn = _import_build_match_card_label()
    label = fn(home="Germany", away="Japan",
                home_score=3, away_score=1,
                status="FT", stage="Group Stage - 1",
                match_date="2026-06-20 15:00", group="Group E")
    assert "3" in label and "1" in label


# ── Task 4: Wettmarkt-Rendering (integration helpers) ───────────────────────

def test_odds_tiles_html_label_shown():
    """The label string is rendered in the output."""
    from agent.dashboard.dashboard import odds_tiles_html
    html = odds_tiles_html(
        label="Konsens-Quoten",
        home_team="Germany", away_team="Spain",
        h_odd=2.10, d_odd=3.40, a_odd=3.20,
    )
    assert "Konsens-Quoten" in html


def test_odds_tiles_html_meta_in_konsens_block():
    """Meta string (bookmakers + margin) appears in output when provided."""
    from agent.dashboard.dashboard import odds_tiles_html
    html = odds_tiles_html(
        label="Konsens-Quoten",
        home_team="Germany", away_team="Spain",
        h_odd=2.10, d_odd=3.40, a_odd=3.20,
        meta="Konsens · 8 Bookmakers · Margin 3.5%",
    )
    assert "8 Bookmakers" in html
    assert "3.5%" in html


def test_stat_bar_uses_navy_not_old_blue():
    """stat_bar home color uses #16213e (navy) not old #4a7fd4."""
    import inspect
    from agent.dashboard.dashboard import render_match_card
    src = inspect.getsource(render_match_card)
    assert "#16213e" in src
    assert "#4a7fd4" not in src
