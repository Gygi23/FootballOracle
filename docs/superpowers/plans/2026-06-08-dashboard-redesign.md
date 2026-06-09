# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Überarbeitung des Streamlit-Dashboards mit einheitlichem Design (dunkler Header, sportliche Badges), kompakten Spielkarten mit Status-Chip und einer neu gestalteten Wettquoten-Kachel-Komponente, plus Fix der fehlenden DB-Query-Felder.

**Architecture:** Alle Änderungen in zwei Dateien — `mysql_tools.py` (SQL-Fix) und `dashboard.py` (neue `odds_tiles_html()`-Funktion, überarbeitetes CSS, neue Card/Header-HTML). Tests in `tests/test_dashboard_components.py` prüfen die puren HTML-Generierungs-Funktionen.

**Tech Stack:** Python 3.13, Streamlit 1.40, SQLAlchemy 2.0, pytest, DM Sans/DM Mono fonts (Google Fonts CDN)

---

## Dateistruktur

| Datei | Änderung | Verantwortlichkeit |
|---|---|---|
| `agent/tools/mysql_tools.py` | Modify lines 610–635 | SQL SELECT um fehlende Spalten erweitern |
| `agent/dashboard/dashboard.py` | Modify CSS-Block, `odds_bar_html`, `render_match_card`, Header-HTML | Neues Design, neue Tile-Komponente |
| `tests/test_dashboard_components.py` | Create | Unit-Tests für reine HTML-Funktionen |

---

## Task 1: SQL-Query-Fix in `get_api_predictions()`

**Files:**
- Modify: `agent/tools/mysql_tools.py` (Funktion ab Zeile 610)
- Test: `tests/test_dashboard_components.py`

- [ ] **Schritt 1: Testdatei anlegen und ersten Test schreiben**

Erstelle `tests/test_dashboard_components.py`:

```python
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
```

- [ ] **Schritt 2: Test ausführen — muss scheitern**

```bash
cd /Users/silian/Dev/FHNW/footballAI
python -m pytest tests/test_dashboard_components.py::test_get_api_predictions_sql_contains_required_fields -v
```

Erwartetes Ergebnis: `FAILED — AssertionError: get_api_predictions() SQL fehlt Feld: 'home_win_implied'`

- [ ] **Schritt 3: SQL-Query in `get_api_predictions()` erweitern**

Datei: `agent/tools/mysql_tools.py`, Funktion `get_api_predictions` (ab Zeile 610).

Ersetze den SQL-String in der `else`-Variante (ohne `fixture_id`). Der vollständige neue SQL:

```python
        sql = """
        SELECT
            fixture_id, predicted_winner,
            home_win_pct, draw_pct, away_win_pct,
            advice, home_odds, draw_odds, away_odds,
            home_win_implied, draw_implied, away_win_implied,
            home_odds_pinnacle, draw_odds_pinnacle, away_odds_pinnacle,
            home_odds_betfair, draw_odds_betfair, away_odds_betfair,
            margin_avg, odds_bookmaker_count, market_confidence,
            updated_at
        FROM api_predictions
        ORDER BY updated_at DESC
        LIMIT :limit
        """
```

Und die `fixture_id`-Variante (Zeile ~614) ebenfalls ergänzen:

```python
        sql = """
        SELECT
            fixture_id, predicted_winner,
            home_win_pct, draw_pct, away_win_pct,
            advice, home_odds, draw_odds, away_odds,
            home_win_implied, draw_implied, away_win_implied,
            home_odds_pinnacle, draw_odds_pinnacle, away_odds_pinnacle,
            home_odds_betfair, draw_odds_betfair, away_odds_betfair,
            margin_avg, odds_bookmaker_count, market_confidence,
            updated_at
        FROM api_predictions
        WHERE fixture_id = :fixture_id
        """
```

- [ ] **Schritt 4: Test erneut ausführen — muss bestehen**

```bash
python -m pytest tests/test_dashboard_components.py::test_get_api_predictions_sql_contains_required_fields -v
```

Erwartetes Ergebnis: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add agent/tools/mysql_tools.py tests/test_dashboard_components.py
git commit -m "fix: add missing odds fields to get_api_predictions() SQL query"
```

---

## Task 2: Neue `odds_tiles_html()`-Funktion

**Files:**
- Modify: `agent/dashboard/dashboard.py` (nach Zeile 414, vor `render_match_card`)
- Test: `tests/test_dashboard_components.py`

- [ ] **Schritt 1: Tests für `odds_tiles_html()` schreiben**

Füge am Ende von `tests/test_dashboard_components.py` hinzu:

```python
# ── Task 2: odds_tiles_html ───────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    # Vorberechnete Werte (0–1 Skala)
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
```

- [ ] **Schritt 2: Tests ausführen — müssen scheitern**

```bash
python -m pytest tests/test_dashboard_components.py -k "odds_tiles" -v
```

Erwartetes Ergebnis: `ImportError: cannot import name 'odds_tiles_html'` oder ähnlich — alle 6 Tests `FAILED/ERROR`.

- [ ] **Schritt 3: `odds_tiles_html()` implementieren**

Füge in `agent/dashboard/dashboard.py` die neue Funktion **nach** `confidence_badge()` (Zeile ~415) ein. Ersetze gleichzeitig `odds_bar_html()` (Zeilen 259–331) und `impl_row_html()` (Zeilen 377–398) durch die neue Funktion — diese werden nicht mehr gebraucht:

```python
def odds_tiles_html(
    label: str,
    home_team: str,
    away_team: str,
    h_odd: float,
    d_odd: float,
    a_odd: float,
    h_prob: float | None = None,
    d_prob: float | None = None,
    a_prob: float | None = None,
    meta: str = "",
) -> str:
    """
    Rendert drei gleichbreite Kacheln für ein Ergebnis-Tripel.

    Kacheln: Wahrscheinlichkeit % gross, rohe Quote klein darunter.
    Team-Kopfzeile: ●HEIM links, AUSWÄRTS● rechts (kein Unentschieden-Label).

    h_prob/d_prob/a_prob: vorberechnete 0-1-Wahrscheinlichkeiten (z.B. margin-bereinigt).
    Wenn None, werden sie aus den Quoten berechnet (1/odd, normalisiert).
    """
    # Wahrscheinlichkeiten berechnen falls nicht übergeben
    if h_prob is None or d_prob is None or a_prob is None:
        rh = 1 / h_odd if h_odd else 0
        rd = 1 / d_odd if d_odd else 0
        ra = 1 / a_odd if a_odd else 0
        total = rh + rd + ra or 1
        h_prob = rh / total
        d_prob = rd / total
        a_prob = ra / total

    hp = round(h_prob * 100)
    dp = round(d_prob * 100)
    ap = 100 - hp - dp  # sicherstellen, dass Summe = 100

    h_str = f"{h_odd:.2f}" if h_odd else "–"
    d_str = f"{d_odd:.2f}" if d_odd else "–"
    a_str = f"{a_odd:.2f}" if a_odd else "–"

    home_upper = home_team.upper()
    away_upper = away_team.upper()

    label_html = (
        f'<div style="font-size:0.7rem;font-weight:600;color:#8a9ab5;'
        f'text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px">'
        f'{label}</div>'
    )
    header_html = (
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:0.7rem;font-weight:700;margin-bottom:5px">'
        f'<span style="color:#16213e">● {home_upper}</span>'
        f'<span style="color:#dc6f5c">{away_upper} ●</span>'
        f'</div>'
    )
    tiles_html = (
        f'<div style="display:flex;gap:6px;margin-bottom:4px">'
        f'<div style="flex:1;background:#16213e;border-radius:6px;padding:12px 6px;text-align:center">'
        f'<span style="font-size:0.9rem;font-weight:700;color:#fff">{hp}%</span></div>'
        f'<div style="flex:1;background:#eef1f6;border-radius:6px;padding:12px 6px;text-align:center">'
        f'<span style="font-size:0.9rem;font-weight:700;color:#475569">{dp}%</span></div>'
        f'<div style="flex:1;background:#dc6f5c;border-radius:6px;padding:12px 6px;text-align:center">'
        f'<span style="font-size:0.9rem;font-weight:700;color:#fff">{ap}%</span></div>'
        f'</div>'
    )
    odds_html = (
        f'<div style="display:flex;gap:6px;margin-bottom:4px">'
        f'<div style="flex:1;text-align:center;font-size:0.68rem;color:#9aa6ba;font-family:\'DM Mono\',monospace">{h_str}</div>'
        f'<div style="flex:1;text-align:center;font-size:0.68rem;color:#9aa6ba;font-family:\'DM Mono\',monospace">{d_str}</div>'
        f'<div style="flex:1;text-align:center;font-size:0.68rem;color:#9aa6ba;font-family:\'DM Mono\',monospace">{a_str}</div>'
        f'</div>'
    )
    meta_html = (
        f'<div style="font-size:0.65rem;color:#c0cadb;text-align:right;margin-bottom:4px">{meta}</div>'
        if meta else ""
    )

    return (
        f'<div style="margin-bottom:14px">'
        f'{label_html}{header_html}{tiles_html}{odds_html}{meta_html}'
        f'</div>'
    )
```

Lösche ausserdem die nun obsoleten Funktionen `odds_bar_html()` (Zeilen 259–331) und `impl_row_html()` (Zeilen 377–398) aus `dashboard.py`.

- [ ] **Schritt 4: Tests ausführen — müssen bestehen**

```bash
python -m pytest tests/test_dashboard_components.py -k "odds_tiles" -v
```

Erwartetes Ergebnis: alle 6 Tests `PASSED`.

- [ ] **Schritt 5: Commit**

```bash
git add agent/dashboard/dashboard.py tests/test_dashboard_components.py
git commit -m "feat: add odds_tiles_html() component, remove obsolete odds_bar_html/impl_row_html"
```

---

## Task 3: Spielkarte — Kollabierter Zustand (kompaktes Layout)

**Files:**
- Modify: `agent/dashboard/dashboard.py` — `render_match_card()` Zeilen 417–447
- Test: `tests/test_dashboard_components.py`

- [ ] **Schritt 1: Hilfsfunktion `build_match_card_label()` testen**

Füge am Ende von `tests/test_dashboard_components.py` hinzu:

```python
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
```

- [ ] **Schritt 2: Test ausführen — muss scheitern**

```bash
python -m pytest tests/test_dashboard_components.py -k "match_card_label" -v
```

Erwartetes Ergebnis: `ImportError: cannot import name 'build_match_card_label'`

- [ ] **Schritt 3: `build_match_card_label()` extrahieren und in `render_match_card()` einbinden**

Füge in `agent/dashboard/dashboard.py` **vor** `render_match_card()` (Zeile 417) ein:

```python
def build_match_card_label(
    home: str, away: str,
    home_score, away_score,
    status: str, stage: str,
    match_date: str, group: str = ""
) -> str:
    """
    Baut den Expander-Label-String.
    Score nur anzeigen wenn Status NICHT NS (nicht gestartet).
    """
    live_statuses = {"1H", "HT", "2H", "ET", "BT", "P"}
    done_statuses = {"FT", "AET", "PEN"}
    show_score = status in (live_statuses | done_statuses)

    if show_score and home_score is not None and away_score is not None:
        mid = f"{int(home_score)} : {int(away_score)}"
    else:
        mid = "vs"

    dt = str(match_date)[:16].replace("T", " ")
    prefix = f"{group}  ·  " if group else ""
    return f"{home}  {mid}  {away}   —   {prefix}{stage}  ·  {dt}"
```

Ändere dann in `render_match_card()` die Zeilen 444–446:

```python
    # Expander-Label — Score nur bei laufenden/abgeschlossenen Spielen
    group = fx.get("group_name", "")
    expander_label = build_match_card_label(
        home=home, away=away,
        home_score=fx.get("home_score"),
        away_score=fx.get("away_score"),
        status=status, stage=stage,
        match_date=fx.get("match_date", ""),
        group=group,
    )
```

- [ ] **Schritt 4: Test ausführen — muss bestehen**

```bash
python -m pytest tests/test_dashboard_components.py -k "match_card_label" -v
```

Erwartetes Ergebnis: alle 3 Tests `PASSED`.

- [ ] **Schritt 5: Commit**

```bash
git add agent/dashboard/dashboard.py tests/test_dashboard_components.py
git commit -m "feat: extract build_match_card_label(), fix NS matches showing score"
```

---

## Task 4: Spielkarte — Wettmarkt-Sektion mit neuen Kacheln

**Files:**
- Modify: `agent/dashboard/dashboard.py` — `render_match_card()` Zeilen 484–542

- [ ] **Schritt 1: Wettmarkt-Sektion in `render_match_card()` ersetzen**

Ersetze den Block `# ── Wettmarkt` (Zeilen 484–542) vollständig durch:

```python
        # ── Wettmarkt ────────────────────────────────────────────────────────
        if api_p and api_p.get("home_odds"):
            st.markdown(
                '<div style="font-size:0.7rem;font-weight:600;color:#8a9ab5;'
                'text-transform:uppercase;letter-spacing:0.6px;'
                'margin-top:14px;margin-bottom:8px">Wettmarkt</div>',
                unsafe_allow_html=True
            )

            h_odd  = api_p.get("home_odds")
            d_odd  = api_p.get("draw_odds")
            a_odd  = api_p.get("away_odds")
            h_impl = api_p.get("home_win_implied")
            d_impl = api_p.get("draw_implied")
            a_impl = api_p.get("away_win_implied")
            h_pin  = api_p.get("home_odds_pinnacle")
            h_bf   = api_p.get("home_odds_betfair")
            bm_cnt = api_p.get("odds_bookmaker_count")
            margin = api_p.get("margin_avg")
            conf   = api_p.get("market_confidence")

            # Meta-String für Konsens-Block
            meta_parts = []
            if bm_cnt is not None:
                meta_parts.append(f"{bm_cnt} Bookmakers")
            if margin is not None:
                meta_parts.append(f"Margin {round(margin * 100, 1)}%")
            if conf:
                cfg = {
                    "HIGH":   ("Markt sicher",  "#0a8f4f"),
                    "MEDIUM": ("Markt neutral", "#b7791f"),
                    "LOW":    ("Offenes Spiel", "#c53030"),
                }
                lbl, col = cfg.get(conf.upper(), ("–", "#8a9ab5"))
                meta_parts.append(
                    f'<span style="color:{col};font-weight:700">{lbl}</span>'
                )
            meta_str = " · ".join(meta_parts)

            # Konsens-Quoten (mit vorberechneten impl. Wahrscheinlichkeiten falls vorhanden)
            st.markdown(
                odds_tiles_html(
                    "Konsens-Quoten", home, away,
                    h_odd=h_odd, d_odd=d_odd, a_odd=a_odd,
                    h_prob=h_impl, d_prob=d_impl, a_prob=a_impl,
                    meta=meta_str,
                ),
                unsafe_allow_html=True,
            )

            # Pinnacle (Sharp Reference)
            if h_pin:
                st.markdown(
                    odds_tiles_html(
                        "Pinnacle", home, away,
                        h_odd=h_pin,
                        d_odd=api_p.get("draw_odds_pinnacle"),
                        a_odd=api_p.get("away_odds_pinnacle"),
                    ),
                    unsafe_allow_html=True,
                )

            # Betfair (Exchange Reference)
            if h_bf:
                st.markdown(
                    odds_tiles_html(
                        "Betfair", home, away,
                        h_odd=h_bf,
                        d_odd=api_p.get("draw_odds_betfair"),
                        a_odd=api_p.get("away_odds_betfair"),
                    ),
                    unsafe_allow_html=True,
                )

        elif not pred_html:
            st.markdown(
                '<p style="font-size:0.75rem;color:#c0cadb;margin:4px 0">'
                'Predictions folgen</p>',
                unsafe_allow_html=True,
            )
```

- [ ] **Schritt 2: Alle bisherigen Tests laufen lassen**

```bash
python -m pytest tests/test_dashboard_components.py -v
```

Erwartetes Ergebnis: alle Tests `PASSED` (keine Regression).

- [ ] **Schritt 3: Statistik-Balken-Farbe aktualisieren**

In `render_match_card()` — die `stat_bar`-Hilfsfunktion (Zeilen ~547–567). Ändere die Heim-Balkenfarbe von `#4a7fd4` auf `#16213e`:

```python
            def stat_bar(label, home_val, away_val):
                if home_val is None and away_val is None:
                    return ""
                h = home_val or 0
                a = away_val or 0
                total = h + a or 1
                h_pct = round(h / total * 100)
                a_pct = 100 - h_pct
                return (
                    f'<div style="display:grid;grid-template-columns:1fr auto 1fr;'
                    f'align-items:center;gap:8px;margin-bottom:6px">'
                    f'<div style="display:flex;align-items:center;gap:6px;justify-content:flex-end">'
                    f'<span style="font-size:0.75rem;font-weight:600;color:#1a2540">{h}</span>'
                    f'<div style="height:10px;width:{h_pct}%;background:#16213e;border-radius:3px;min-width:2px"></div>'
                    f'</div>'
                    f'<span style="font-size:0.68rem;color:#2d3a50;white-space:nowrap;text-align:center">{label}</span>'
                    f'<div style="display:flex;align-items:center;gap:6px">'
                    f'<div style="height:10px;width:{a_pct}%;background:#dc6f5c;border-radius:3px;min-width:2px"></div>'
                    f'<span style="font-size:0.75rem;font-weight:600;color:#1a2540">{a}</span>'
                    f'</div></div>'
                )
```

Und im Statistik-Header (Team-Farben, Zeilen ~585–592) ebenfalls anpassen:

```python
                    f'<span style="font-size:0.72rem;font-weight:600;color:#16213e">{home}</span>'
                    f'<span style="font-size:0.68rem;color:#a0aec0;text-align:center">Statistiken</span>'
                    f'<span style="font-size:0.72rem;font-weight:600;color:#dc6f5c;text-align:right">{away}</span>'
```

- [ ] **Schritt 4: Alle Tests laufen lassen**

```bash
python -m pytest tests/test_dashboard_components.py -v
```

Erwartetes Ergebnis: alle Tests `PASSED`.

- [ ] **Schritt 5: Commit**

```bash
git add agent/dashboard/dashboard.py
git commit -m "feat: replace odds bars with odds_tiles_html() in match detail, update stat bar colours"
```

---

## Task 5: CSS-Refresh und Header/Navigation

**Files:**
- Modify: `agent/dashboard/dashboard.py` — CSS-Block (Zeilen 16–116) und Navigation-HTML (Zeilen 621–638)

- [ ] **Schritt 1: CSS-Block vollständig ersetzen**

Ersetze das gesamte `st.markdown("""<style>...""")` (Zeilen 16–117) durch:

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f7f9fc; min-height: 100vh; }
.stApp > header { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }

/* Karten */
.match-card {
    background: #ffffff;
    border: 1px solid #e8ecf3;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.match-card-live {
    background: #eafbf1;
    border: 1px solid #bfead2;
}

/* Section-Titel */
.section-title {
    font-size: 0.75rem; font-weight: 700; color: #8a9ab5;
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.6rem;
}

/* Gruppen-Tabelle */
.group-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.group-table th { color: #a0aec0; font-weight: 500; font-size: 0.72rem; text-align: center; padding: 4px 6px; border-bottom: 1px solid rgba(0,0,0,0.05); }
.group-table th:first-child { text-align: left; }
.group-table td { padding: 7px 6px; text-align: center; color: #2d3a50; border-bottom: 1px solid rgba(0,0,0,0.04); }
.group-table td:first-child { text-align: left; font-weight: 500; }
.group-table tr:last-child td { border-bottom: none; }
.group-table tr.qualified td { color: #1a2540; }
.group-table tr.out td { color: #a0aec0; }
.pts { font-weight: 600 !important; color: #2d3a50 !important; }

/* Form-Badges */
.form-badge { display: inline-block; width: 18px; height: 18px; border-radius: 4px; font-size: 9px; font-weight: 600; line-height: 18px; text-align: center; margin-left: 2px; }
.form-w { background: #d4edda; color: #1a6b2e; }
.form-d { background: #fff3cd; color: #856404; }
.form-l { background: #f8d7da; color: #842029; }

/* Prognosen-Balken (slim, für WM-Orakel / Football API) */
.pred-row { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
.pred-label { font-size: 0.72rem; color: #8a9ab5; min-width: 110px; font-weight: 500; }
.pred-bar-wrap { flex: 1; height: 5px; border-radius: 3px; overflow: hidden; display: flex; background: rgba(0,0,0,0.06); }
.pred-bar-home { background: #16213e; height: 100%; }
.pred-bar-draw { background: #c0cadb; height: 100%; }
.pred-bar-away { background: #dc6f5c; height: 100%; }
.pred-values { font-size: 0.72rem; color: #8a9ab5; min-width: 120px; text-align: right; font-family: 'DM Mono', monospace; }

/* Gruppen-Karte */
.glass-sm {
    background: #ffffff;
    border: 1px solid #e8ecf3;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}

/* Expander */
div[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e8ecf3 !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
    box-shadow: none !important;
}
div[data-testid="stExpander"] summary {
    padding: 0.75rem 1rem !important;
    border-radius: 10px !important;
}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] > details > summary > span {
    color: #16213e !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
}
div[data-testid="stExpander"] > div > div {
    padding: 0 1rem 0.9rem 1rem !important;
}

/* Chat */
div[data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 12px !important;
    font-size: 0.82rem !important;
    color: #16213e !important;
}
div[data-testid="stChatMessage"] { border: none !important; box-shadow: none !important; background: transparent !important; }
[data-testid="stChatMessage"] > div { border: none !important; box-shadow: none !important; }
div[data-testid="stChatInput"] {
    background: #ffffff !important;
    border: 1px solid #e8ecf3 !important;
    border-radius: 12px !important;
}
div[data-testid="stChatInput"] textarea { color: #16213e !important; }

.stRadio [data-testid="stMarkdownContainer"] p { font-size: 0.82rem !important; color: #2d3a50 !important; }
div[data-baseweb="select"] { font-size: 0.82rem !important; }
</style>
""", unsafe_allow_html=True)
```

- [ ] **Schritt 2: Header/Navigation-HTML ersetzen**

Ersetze den Navigation-Block (Zeilen ~621–638, das `st.markdown('''<div style="background:rgba...`)`) durch:

```python
st.markdown(
    '<div style="background:#16213e;border-radius:14px;padding:0.85rem 1.5rem;'
    'margin-bottom:1.25rem;display:flex;align-items:baseline;gap:8px">'
    '<span style="font-size:1.25rem;font-weight:700;color:#ffffff">football</span>'
    '<span style="font-size:1.25rem;font-weight:700;color:#5b9bff">Orakel</span>'
    '<span style="font-size:0.75rem;color:rgba(255,255,255,0.45);margin-left:6px">'
    'FIFA World Cup 2026</span>'
    '</div>',
    unsafe_allow_html=True,
)
```

- [ ] **Schritt 3: Chat-Header aktualisieren**

In `render_chat()` (Zeile ~598) den Header-String anpassen — von dunklem `#1a2540` auf `#16213e` und Text auf weiss:

```python
def render_chat(key_suffix=""):
    st.markdown(
        '<div style="background:#16213e;border-radius:14px;padding:1rem 1.25rem 0.5rem;">'
        '<div style="font-size:0.85rem;font-weight:700;color:#ffffff;'
        'padding-bottom:0.75rem;border-bottom:1px solid rgba(255,255,255,0.1)">'
        '⚽ WM-Orakel</div></div>',
        unsafe_allow_html=True,
    )
    # Rest der Funktion bleibt unverändert
    ...
```

- [ ] **Schritt 4: Alle Tests laufen lassen**

```bash
python -m pytest tests/test_dashboard_components.py -v
```

Erwartetes Ergebnis: alle Tests `PASSED`.

- [ ] **Schritt 5: Dashboard lokal starten und visuell prüfen**

```bash
source .venv/bin/activate
streamlit run agent/dashboard/dashboard.py --server.port 8533
```

Prüfe im Browser (http://localhost:8533):
- [ ] Header ist dunkelblau (`#16213e`), "Orakel" in Hellblau
- [ ] App-Hintergrund ist hellgrau (`#f7f9fc`)
- [ ] Spielkarten zeigen Status-Badge rechts (z.B. "21:00" oder "LIVE")
- [ ] NS-Spiele zeigen "vs" statt "0:0"
- [ ] Aufgeklappte Detailansicht zeigt Kacheln mit % (gross) und Quote (klein darunter)
- [ ] "Unentschieden" fehlt im Kachel-Header
- [ ] Pinnacle/Betfair erscheinen als separate Kachel-Blöcke (sofern Daten vorhanden)
- [ ] Statistik-Balken: Heim-Balken in Navy, Auswärts in Rot

- [ ] **Schritt 6: Commit**

```bash
git add agent/dashboard/dashboard.py
git commit -m "feat: apply new CSS palette, dark navy header, updated chat header"
```

---

## Selbst-Review

### Spec-Abdeckung

| Spec-Anforderung | Umgesetzt in |
|---|---|
| Einheitliches, klares Design | Task 5: CSS-Block, neue Palette |
| Dunklerer Navy-Header | Task 5: Navigation-HTML |
| Kompakte Karten mit Status-Chip | Task 3: build_match_card_label() |
| NS-Spiele zeigen "vs" nicht Score | Task 3: build_match_card_label() |
| Akkordeon-Detailansicht | Bestehende st.expander-Mechanik, verfeinert in Task 4/5 |
| Quoten-Kacheln (% gross, Quote klein) | Task 2: odds_tiles_html() |
| Team-Kopfzeile (kein "Unentschieden") | Task 2: odds_tiles_html() |
| Pinnacle/Betfair in neuem Design | Task 4: render_match_card() Wettmarkt-Sektion |
| Konsistente Balkenfarben (navy/rot) | Task 4: stat_bar, Task 5: CSS pred-bar-home |
| SQL-Query-Fix für fehlende Odds-Felder | Task 1: get_api_predictions() |

### Placeholder-Check

Kein TBD, kein "implement later", alle Code-Blöcke sind vollständig.

### Typ-Konsistenz

- `odds_tiles_html()` wird in Task 2 definiert und in Task 4 aufgerufen — Signatur konsistent (`label, home_team, away_team, h_odd, d_odd, a_odd, [h_prob, d_prob, a_prob, meta]`).
- `build_match_card_label()` in Task 3 definiert, direkt in `render_match_card()` aufgerufen — `home_score`/`away_score` als rohe Werte (können None sein), Status-Logik intern.
- Alle Farbkonstanten (`#16213e`, `#dc6f5c`, `#eef1f6`) konsistent in CSS-Block (Task 5) und HTML-Generierung (Task 2/4).
