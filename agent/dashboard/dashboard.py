import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

_DISPLAY_TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Zurich"))


def _fmt_local(match_date) -> str:
    """UTC-Datetime aus DB → lokale Anzeigezeit (z.B. MESZ)."""
    if match_date is None:
        return "?"
    if isinstance(match_date, str):
        match_date = match_date[:16].replace("T", " ")
        try:
            match_date = datetime.fromisoformat(match_date)
        except ValueError:
            return match_date
    if match_date.tzinfo is None:
        match_date = match_date.replace(tzinfo=timezone.utc)
    return match_date.astimezone(_DISPLAY_TZ).strftime("%d.%m. %H:%M")

st.set_page_config(
    page_title="football Orakel – WM 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Passwortschutz ───────────────────────────────────────────────────────────

_DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

if _DASHBOARD_PASSWORD:
    if not st.session_state.get("authenticated"):
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp { background: #16213e !important; min-height: 100vh; }

        /* Alle Streamlit-Chrome-Elemente verstecken */
        header, footer, #MainMenu,
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stToolbar"],
        [data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"] {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
        }

        /* Block-Container zentrieren */
        .block-container {
            max-width: 420px !important;
            padding-top: 8rem !important;
            margin: 0 auto !important;
        }

        /* Titel */
        .login-title {
            font-size: 1.7rem; font-weight: 700; color: #ffffff;
            margin-bottom: 0.2rem;
        }
        .login-sub {
            font-size: 0.82rem; color: #6b82a8; margin-bottom: 1.75rem;
        }
        .login-divider {
            border: none; border-top: 1px solid rgba(255,255,255,0.08);
            margin: 1.5rem 0;
        }

        /* Input */
        .stTextInput > div > div > input {
            background: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 10px !important;
            color: #16213e !important;
            font-size: 0.95rem !important;
            padding: 0.65rem 0.9rem !important;
            caret-color: #16213e !important;
        }
        .stTextInput > div > div > input::placeholder { color: #94a3b8 !important; }
        .stTextInput > div > div > input:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 2px rgba(37,99,235,0.25) !important;
        }

        /* Button */
        .stButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.65rem !important;
            width: 100% !important;
            margin-top: 0.25rem;
            transition: background 0.15s;
        }
        .stButton > button:hover { background: #1d4ed8 !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-title">⚽ footballOrakel</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">FIFA World Cup 2026 · Analyse & Prognosen</div>', unsafe_allow_html=True)
        pw = st.text_input("pw", type="password", placeholder="Passwort eingeben…", label_visibility="collapsed")
        if st.button("Anmelden", use_container_width=True):
            if pw == _DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Falsches Passwort.")
        st.stop()

# ─── Styles ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f7f9fc; min-height: 100vh; }
.stApp > header { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }

.glass {
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(200,210,230,0.6);
    border-radius: 18px;
    box-shadow: 0 2px 24px rgba(60,80,120,0.07);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.glass-sm {
    background: rgba(255,255,255,0.55);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(200,210,230,0.5);
    border-radius: 14px;
    box-shadow: 0 2px 16px rgba(60,80,120,0.06);
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    overflow: hidden;
}
.section-title {
    font-size: 0.8rem; font-weight: 600; color: #8a9ab5;
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.75rem;
}
.group-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed; }
.group-table th { color: #a0aec0; font-weight: 500; font-size: 0.68rem; text-align: center; padding: 3px 3px; border-bottom: 1px solid rgba(0,0,0,0.05); width: 22px; }
.group-table th:first-child { text-align: left; width: auto; }
.group-table th:last-child { width: 76px; }
.group-table td { padding: 5px 3px; text-align: center; color: #16213e; border-bottom: 1px solid rgba(0,0,0,0.04); overflow: hidden; font-size: 0.78rem; }
.group-table td:first-child { text-align: left; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; max-width: 0; font-size: 0.8rem; }
.group-table td:last-child { white-space: nowrap; text-overflow: clip; }
.group-table tr:last-child td { border-bottom: none; }
.group-table tr.qualified td { color: #16213e; }
.group-table tr.out td { color: #a0aec0; }
.pts { font-weight: 600 !important; color: #2d3a50 !important; }

.form-badge { display: inline-block; width: 18px; height: 18px; border-radius: 4px; font-size: 9px; font-weight: 600; line-height: 18px; text-align: center; margin-left: 2px; }
.form-w { background: #d4edda; color: #1a6b2e; }
.form-d { background: #fff3cd; color: #856404; }
.form-l { background: #f8d7da; color: #842029; }

.pred-row { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
.pred-label { font-size: 0.72rem; color: #8a9ab5; min-width: 110px; font-weight: 500; }
.pred-bar-wrap { flex: 1; height: 5px; border-radius: 3px; overflow: hidden; display: flex; background: rgba(0,0,0,0.06); }
.pred-bar-wrap-lg { flex: 1; height: 28px; border-radius: 6px; overflow: hidden; display: flex; background: rgba(0,0,0,0.06); position: relative; }
.pred-bar-home { background: #16213e; height: 100%; }
.pred-bar-draw { background: #c0cadb; height: 100%; }
.pred-bar-away { background: #dc6f5c; height: 100%; }
.pred-values { font-size: 0.72rem; color: #8a9ab5; min-width: 120px; text-align: right; font-family: 'DM Mono', monospace; }

/* Expander: Label-Text sichtbar */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.7) !important;
    border: 1px solid rgba(200,210,230,0.6) !important;
    border-radius: 14px !important;
    margin-bottom: 0.75rem !important;
    box-shadow: none !important;
}
div[data-testid="stExpander"] summary {
    padding: 0.85rem 1.25rem !important;
    border-radius: 14px !important;
}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] > details > summary > span {
    color: #16213e !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
}
div[data-testid="stExpander"] > div > div {
    padding: 0 1.25rem 1rem 1.25rem !important;
}

.stRadio [data-testid="stMarkdownContainer"] p { font-size: 0.82rem !important; color: #2d3a50 !important; }
div[data-baseweb="select"] { font-size: 0.82rem !important; }

/* Chat */
div[data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 12px !important;
    font-size: 0.82rem !important;
    color: #16213e !important;
}
div[data-testid="stChatMessageContent"][data-role="user"] { background: transparent !important; }
div[data-testid="stChatMessage"] { border: none !important; box-shadow: none !important; background: transparent !important; }
[data-testid="stChatMessage"] > div { border: none !important; box-shadow: none !important; }
div[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.8) !important;
    border: 1px solid rgba(200,210,230,0.5) !important;
    border-radius: 14px !important;
}
div[data-testid="stChatInput"] textarea { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "uebersicht"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent" not in st.session_state:
    from agent.agent import FootballAIAgent
    st.session_state.agent = FootballAIAgent()


# ─── Data Loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_live_fixtures():
    from agent.tools.mysql_tools import get_tournament_fixtures
    import json
    r = json.loads(get_tournament_fixtures(
        season=2026, league_id=1,
        status="1H-HT-2H-ET-P-BT",
        limit=10
    ))
    return r.get("result", [])

@st.cache_data(ttl=60)
def load_today_upcoming():
    from agent.tools.mysql_tools import get_tournament_fixtures
    import json
    from datetime import date, timedelta
    today = date.today()
    wm_start = date(2026, 6, 11)
    display_date = max(today, wm_start)
    tomorrow = display_date + timedelta(days=1)
    r = json.loads(get_tournament_fixtures(season=2026, league_id=1, status="NS", limit=100))
    fixtures = r.get("result", [])
    today_games = sorted(
        [f for f in fixtures if str(f.get("match_date", ""))[:10] == display_date.isoformat()],
        key=lambda x: x.get("match_date", "")
    )
    tomorrow_games = sorted(
        [f for f in fixtures if str(f.get("match_date", ""))[:10] == tomorrow.isoformat()],
        key=lambda x: x.get("match_date", "")
    )
    return today_games, tomorrow_games

@st.cache_data(ttl=300)
def load_recent_results():
    from agent.tools.mysql_tools import get_tournament_fixtures
    import json
    all_results = []
    for status in ["FT", "AET", "PEN"]:
        r = json.loads(get_tournament_fixtures(season=2026, league_id=1, status=status, limit=20))
        all_results.extend(r.get("result", []))
    return sorted(all_results, key=lambda x: x.get("match_date", ""), reverse=True)[:10]

@st.cache_data(ttl=300)
def load_standings():
    from agent.tools.mysql_tools import get_tournament_standings
    import json
    r = json.loads(get_tournament_standings(season=2026))
    return r.get("result", [])

@st.cache_data(ttl=300)
def load_fixtures_by_group(group_name: str):
    from agent.tools.mysql_tools import get_tournament_fixtures, get_tournament_standings
    import json
    sr = json.loads(get_tournament_standings(season=2026, group_name=group_name))
    teams = [r["team_name"] for r in sr.get("result", [])]
    if not teams:
        return []
    all_fx, seen = [], set()
    for team in teams:
        r = json.loads(get_tournament_fixtures(season=2026, league_id=1, team_name=team, limit=10))
        for fx in r.get("result", []):
            fid = fx.get("fixture_id")
            if fid not in seen:
                seen.add(fid)
                all_fx.append(fx)
    return sorted(all_fx, key=lambda x: x.get("match_date", ""))

@st.cache_data(ttl=300)
def load_api_predictions():
    from agent.tools.mysql_tools import get_api_predictions
    import json
    r = json.loads(get_api_predictions(limit=100))
    return r.get("result", [])

@st.cache_data(ttl=300)
def load_exact_score_odds(fixture_id: int) -> list[dict]:
    """Top-5 Exact-Score-Ergebnisse aus odds_exact_score für ein Fixture."""
    from sqlalchemy import text
    from agent.tools.mysql_tools import get_engine
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(text("""
                SELECT scoreline, odds_avg, probability
                FROM odds_exact_score
                WHERE fixture_id = :fid
                ORDER BY probability DESC
                LIMIT 5
            """), {"fid": fixture_id}).fetchall()
        return [{"scoreline": r.scoreline, "odds_avg": float(r.odds_avg), "probability": float(r.probability)} for r in rows]
    except Exception:
        return []

@st.cache_data(ttl=300)
def load_ko_fixtures():
    from agent.tools.mysql_tools import get_tournament_fixtures
    import json
    r = json.loads(get_tournament_fixtures(season=2026, league_id=1, limit=100))
    fixtures = r.get("result", [])
    return [f for f in fixtures if f.get("stage") and "Group" not in f.get("stage", "")]

@st.cache_data(ttl=10)
def get_last_db_update() -> str:
    from sqlalchemy import text
    from agent.tools.mysql_tools import get_engine
    with get_engine().connect() as conn:
        result = conn.execute(text("""
            SELECT MAX(updated_at)
            FROM tournament_fixtures
            WHERE season = 2026 AND league_id = 1
        """)).fetchone()
    return str(result[0]) if result[0] else ""


# ─── Auto Refresh ─────────────────────────────────────────────────────────────

@st.fragment(run_every=10)
def auto_refresh():
    last_update = get_last_db_update()
    if last_update != st.session_state.get("last_db_update"):
        st.session_state.last_db_update = last_update
        st.cache_data.clear()
        st.rerun(scope="app")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def form_badges(form_str):
    if not form_str:
        return ""
    html = ""
    for c in str(form_str)[:5]:
        cls = {"W": "form-w", "L": "form-l", "D": "form-d"}.get(c.upper(), "form-d")
        html += f'<span class="form-badge {cls}">{c.upper()}</span>'
    return html


def pred_row_html(label, home, draw, away, is_odds=False):
    """
    Rendert eine Prognose-Zeile mit schmalem Balken.
    is_odds=True: home/draw/away sind Quoten (z.B. 2.10)
                  → Balkenbreite via margin-bereinigte implizite Wahrsch.
                  → Anzeige: rohe Quoten auf 2 Kommastellen
    is_odds=False: home/draw/away sind Prozentwerte (0-100)
                  → Balkenbreite direkt aus Prozentwerten
    """
    if is_odds:
        h_str = f"{home:.2f}" if home else "–"
        d_str = f"{draw:.2f}" if draw else "–"
        a_str = f"{away:.2f}" if away else "–"
        vs = f"{h_str} · {d_str} · {a_str}"
        if home and draw and away:
            rh = 1 / home
            rd = 1 / draw
            ra = 1 / away
            total = rh + rd + ra
            hw = round(rh / total * 100)
            dw = round(rd / total * 100)
            aw = 100 - hw - dw
        else:
            hw, dw, aw = 33, 33, 34
    else:
        hw = round(home or 33)
        dw = round(draw or 33)
        aw = 100 - hw - dw
        vs = f"{round(home or 0)}% · {round(draw or 0)}% · {round(away or 0)}%"

    return (
        f'<div class="pred-row">'
        f'<span class="pred-label">{label}</span>'
        f'<div class="pred-bar-wrap">'
        f'<div class="pred-bar-home" style="width:{hw}%"></div>'
        f'<div class="pred-bar-draw" style="width:{dw}%"></div>'
        f'<div class="pred-bar-away" style="width:{aw}%"></div>'
        f'</div>'
        f'<span class="pred-values">{vs}</span>'
        f'</div>'
    )


def confidence_badge(confidence: str | None) -> str:
    if not confidence:
        return ""
    cfg = {
        "HIGH":   ("Sicherer Markt",   "#d4edda", "#1a6b2e"),
        "MEDIUM": ("Normaler Markt",   "#fff3cd", "#856404"),
        "LOW":    ("Unsicherer Markt", "#f8d7da", "#842029"),
    }
    label, bg, color = cfg.get(confidence.upper(), ("–", "#f0f0f0", "#888"))
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;'
        f'background:{bg};color:{color};font-size:0.68rem;font-weight:600">'
        f'{label}</span>'
    )


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
    if h_prob is None and d_prob is None and a_prob is None:
        rh = 1 / h_odd if h_odd else 0
        rd = 1 / d_odd if d_odd else 0
        ra = 1 / a_odd if a_odd else 0
        if rh == 0 and rd == 0 and ra == 0:
            hp, dp, ap = 33, 33, 34
        else:
            total = rh + rd + ra
            h_prob = rh / total
            d_prob = rd / total
            a_prob = ra / total
            hp = round(h_prob * 100)
            dp = round(d_prob * 100)
            ap = max(0, 100 - hp - dp)
    else:
        # At least one prob is provided; use them as-is (already 0-1 normalized)
        hp = round((h_prob or 0) * 100)
        dp = round((d_prob or 0) * 100)
        ap = max(0, 100 - hp - dp)

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


def exact_score_section_html(scores: list[dict]) -> str:
    """
    Rendert die Top-N wahrscheinlichsten Ergebnisse als kompakte Kachelreihe.
    scores: [{"scoreline": "1:0", "odds_avg": 5.50, "probability": 0.182}, ...]
    """
    if not scores:
        return ""

    header = (
        '<div style="font-size:0.7rem;font-weight:600;color:#8a9ab5;'
        'text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px">'
        'Wahrscheinlichstes Ergebnis</div>'
    )

    tiles = ""
    for entry in scores[:5]:
        pct   = round(entry["probability"] * 100, 1)
        score = entry["scoreline"]
        odds  = entry["odds_avg"]
        # Top-Ergebnis bekommt dunkleren Hintergrund
        is_top = entry is scores[0]
        bg     = "#16213e" if is_top else "#f1f5f9"
        color  = "#ffffff" if is_top else "#374151"
        sub    = "#94b4d4" if is_top else "#94a3b8"
        tiles += (
            f'<div style="flex:1;min-width:52px;background:{bg};border-radius:8px;'
            f'padding:8px 4px;text-align:center">'
            f'<div style="font-size:0.85rem;font-weight:700;color:{color};'
            f'font-family:\'DM Mono\',monospace">{score}</div>'
            f'<div style="font-size:0.68rem;font-weight:600;color:{color};margin-top:2px">'
            f'{pct}%</div>'
            f'<div style="font-size:0.6rem;color:{sub};margin-top:1px">{odds:.2f}</div>'
            f'</div>'
        )

    return (
        f'<div style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.06)">'
        f'{header}'
        f'<div style="display:flex;gap:5px">{tiles}</div>'
        f'</div>'
    )


def wettmarkt_html(home: str, away: str, api_p: dict, is_finished: bool = False) -> str:
    """
    Wettmarkt-Block: Wahrscheinlichkeitsbalken + Quoten-Tabelle mit Legende.
    Immer sichtbar — passender Placeholder wenn keine Odds verfügbar.
    Confidence Badge gehört hierher (nicht zum Spielstatus).
    """
    h_impl = api_p.get("home_win_implied")
    d_impl = api_p.get("draw_implied")
    a_impl = api_p.get("away_win_implied")
    h_odd  = api_p.get("home_odds")
    d_odd  = api_p.get("draw_odds")
    a_odd  = api_p.get("away_odds")
    h_pin  = api_p.get("home_odds_pinnacle")
    d_pin  = api_p.get("draw_odds_pinnacle")
    a_pin  = api_p.get("away_odds_pinnacle")
    h_bf   = api_p.get("home_odds_betfair")
    d_bf   = api_p.get("draw_odds_betfair")
    a_bf   = api_p.get("away_odds_betfair")
    bm_cnt = api_p.get("odds_bookmaker_count")
    margin = api_p.get("margin_avg")
    conf   = api_p.get("market_confidence")

    has_odds = bool(h_odd or h_impl)

    # ── Section header ────────────────────────────────────────────────────────
    meta_parts = []
    if bm_cnt:
        meta_parts.append(f"{int(bm_cnt)} Buchmacher")
    if margin is not None:
        meta_parts.append(f"Margin {round(margin * 100, 1)}%")
    meta_str = " · ".join(meta_parts)

    section_header = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:10px">'
        f'<span style="font-size:0.7rem;font-weight:600;color:#8a9ab5;'
        f'text-transform:uppercase;letter-spacing:0.6px">Wettmarkt</span>'
        f'<span style="font-size:0.63rem;color:#a0aec0">{meta_str}</span>'
        f'</div>'
    )

    # ── No odds → Placeholder ─────────────────────────────────────────────────
    if not has_odds:
        msg = (
            "Keine Quoten für dieses Spiel gespeichert"
            if is_finished
            else "Quoten erscheinen kurz vor Spielbeginn (~24h vorher)"
        )
        return (
            f'<div style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.06)">'
            f'{section_header}'
            f'<p style="font-size:0.72rem;color:#b0bac8;margin:4px 0 0 0;font-style:italic">{msg}</p>'
            f'</div>'
        )

    # Opening Odds für Bewegungsanzeige
    h_open = api_p.get("home_odds_open")
    d_open = api_p.get("draw_odds_open")
    a_open = api_p.get("away_odds_open")

    # ── Probability bar ───────────────────────────────────────────────────────
    hp = round((h_impl or 0) * 100)
    dp = round((d_impl or 0) * 100)
    ap = max(0, 100 - hp - dp)

    h_short = (home[:15] + "…") if len(home) > 15 else home
    a_short = (away[:15] + "…") if len(away) > 15 else away

    # Mitte des grauen Segments (in % der Gesamtbreite)
    draw_center = hp + dp / 2

    prob_section = (
        # Team labels + "Unentschieden" zentriert über dem grauen Balken
        f'<div style="position:relative;height:1.3rem;margin-bottom:5px">'
        f'<span style="position:absolute;left:0;font-size:0.7rem;font-weight:600;color:#16213e;'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:38%">{h_short}</span>'
        f'<span style="position:absolute;left:{draw_center:.1f}%;transform:translateX(-50%);'
        f'font-size:0.65rem;font-weight:400;color:#94a3b8;white-space:nowrap">Unentschieden</span>'
        f'<span style="position:absolute;right:0;font-size:0.7rem;font-weight:600;color:#dc6f5c;'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:38%;text-align:right">{a_short}</span>'
        f'</div>'
        # Bar
        f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;margin-bottom:5px">'
        f'<div style="flex:{hp};background:#16213e"></div>'
        f'<div style="flex:{dp};background:#94a3b8;margin:0 1px"></div>'
        f'<div style="flex:{ap};background:#dc6f5c"></div>'
        f'</div>'
        # Prozentwerte ebenfalls zentriert über dem jeweiligen Segment
        f'<div style="position:relative;height:1.2rem;margin-bottom:12px">'
        f'<span style="position:absolute;left:0;font-size:0.72rem;font-weight:700;color:#16213e">{hp}%</span>'
        f'<span style="position:absolute;left:{draw_center:.1f}%;transform:translateX(-50%);'
        f'font-size:0.72rem;color:#94a3b8">{dp}%</span>'
        f'<span style="position:absolute;right:0;font-size:0.72rem;font-weight:700;color:#dc6f5c">{ap}%</span>'
        f'</div>'
    )

    # ── Odds table ────────────────────────────────────────────────────────────
    def _fmt(v): return f"{v:.2f}" if v else "–"

    def _movement(current, opening):
        """Pfeil + Delta wenn Quote sich >0.03 bewegt hat."""
        if not current or not opening or abs(current - opening) < 0.03:
            return ""
        delta = abs(current - opening)
        if current < opening:
            # Quote gesunken = Team mehr favorisiert
            return f'<span style="color:#15803d;font-size:0.6rem;margin-left:3px">▼{delta:.2f}</span>'
        else:
            # Quote gestiegen = Team weniger favorisiert
            return f'<span style="color:#dc2626;font-size:0.6rem;margin-left:3px">▲{delta:.2f}</span>'

    def _row(label, ho, do_, ao, ho_open=None, do_open=None, ao_open=None):
        return (
            f'<tr>'
            f'<td style="font-size:0.68rem;color:#6b7280;padding:5px 0;white-space:nowrap">{label}</td>'
            f'<td style="font-size:0.74rem;font-weight:700;color:#16213e;text-align:center;'
            f'padding:5px 6px;font-family:\'DM Mono\',monospace">'
            f'{_fmt(ho)}{_movement(ho, ho_open)}</td>'
            f'<td style="font-size:0.74rem;font-weight:500;color:#64748b;text-align:center;'
            f'padding:5px 6px;font-family:\'DM Mono\',monospace">'
            f'{_fmt(do_)}{_movement(do_, do_open)}</td>'
            f'<td style="font-size:0.74rem;font-weight:700;color:#dc6f5c;text-align:right;'
            f'padding:5px 6px;font-family:\'DM Mono\',monospace">'
            f'{_fmt(ao)}{_movement(ao, ao_open)}</td>'
            f'</tr>'
        )

    rows = ""
    if h_odd:
        rows += _row("Konsens", h_odd, d_odd, a_odd, h_open, d_open, a_open)
    if h_pin:
        rows += _row("Pinnacle", h_pin, d_pin, a_pin)
    if h_bf:
        rows += _row("Betfair", h_bf, d_bf, a_bf)

    odds_table = (
        f'<table style="width:100%;border-collapse:collapse;margin-bottom:8px">'
        f'<thead><tr style="border-bottom:1px solid rgba(0,0,0,0.07)">'
        f'<th style="font-size:0.62rem;color:#a0aec0;font-weight:400;text-align:left;'
        f'padding:0 0 5px 0"></th>'
        f'<th style="font-size:0.62rem;color:#16213e;font-weight:700;text-align:center;'
        f'padding:0 6px 5px">Heimsieg</th>'
        f'<th style="font-size:0.62rem;color:#64748b;font-weight:600;text-align:center;'
        f'padding:0 6px 5px">X</th>'
        f'<th style="font-size:0.62rem;color:#dc6f5c;font-weight:700;text-align:right;'
        f'padding:0 6px 5px">Auswärtssieg</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )

    # ── Legend + Confidence badge ─────────────────────────────────────────────
    conf_map = {
        "HIGH":   ("Sicherer Markt",   "#d4edda", "#1a6b2e"),
        "MEDIUM": ("Normaler Markt",   "#fff3cd", "#856404"),
        "LOW":    ("Unsicherer Markt", "#f8d7da", "#842029"),
    }
    conf_label, conf_bg, conf_color = conf_map.get(conf or "", ("", "#f0f0f0", "#888"))
    conf_badge_html = (
        f'<span style="padding:2px 8px;border-radius:4px;background:{conf_bg};'
        f'color:{conf_color};font-size:0.62rem;font-weight:600;white-space:nowrap">'
        f'{conf_label}</span>'
    ) if conf_label else ""

    footer = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
        f'<span style="font-size:0.6rem;color:#c0cadb;line-height:1.4">'
        f'Konsens&nbsp;=&nbsp;Ø&nbsp;Buchmacher'
        f'&nbsp;·&nbsp;Pinnacle&nbsp;=&nbsp;Schärfster&nbsp;Markt'
        f'&nbsp;·&nbsp;Betfair&nbsp;=&nbsp;Wettbörse'
        f'</span>'
        f'{conf_badge_html}'
        f'</div>'
    )

    return (
        f'<div style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.06)">'
        f'{section_header}{prob_section}{odds_table}{footer}'
        f'</div>'
    )


def build_match_card_label(
    home: str, away: str,
    home_score: int | float | None, away_score: int | float | None,
    status: str, stage: str,
    match_date: str, group: str = ""
) -> str:
    """
    Baut den Expander-Label-String für st.expander.
    Score wird angezeigt bei Live-Status (1H, HT, 2H, ET, BT, P) und
    Abgeschlossen-Status (FT, AET, PEN). Bei NS (nicht gestartet) oder
    unbekanntem Status erscheint 'vs'.
    """
    live_statuses = {"1H", "HT", "2H", "ET", "BT", "P"}
    done_statuses = {"FT", "AET", "PEN"}
    show_score = status in (live_statuses | done_statuses)

    if show_score and home_score is not None and away_score is not None:
        try:
            mid = f"{int(float(home_score))} : {int(float(away_score))}"
        except (TypeError, ValueError):
            mid = "vs"
    else:
        mid = "vs"

    dt = _fmt_local(match_date)
    prefix = f"{group}  ·  " if group else ""
    return f"{home}  {mid}  {away}   —   {prefix}{stage}  ·  {dt}"


def render_match_card(fx, api_preds, agent_preds):
    home = fx.get("home_team", "")
    away = fx.get("away_team", "")
    if not home or not away:
        return

    fid    = fx.get("fixture_id")
    stage  = fx.get("stage", "")
    status = fx.get("status", "NS")

    # Status: Hintergrundfarbe + Textfarbe als Pill
    status_style = {
        "NS":  ("#f1f5f9", "#64748b"),
        "1H":  ("#dcfce7", "#15803d"),
        "HT":  ("#fef9c3", "#a16207"),
        "2H":  ("#dcfce7", "#15803d"),
        "ET":  ("#fef9c3", "#a16207"),
        "BT":  ("#fef9c3", "#a16207"),
        "P":   ("#fee2e2", "#dc2626"),
        "INT": ("#fef9c3", "#a16207"),
        "FT":  ("#f1f5f9", "#374151"),
        "AET": ("#f1f5f9", "#374151"),
        "PEN": ("#f1f5f9", "#374151"),
    }
    s_bg, s_fg = status_style.get(status, ("#f1f5f9", "#64748b"))
    # Für Expander-Label noch die alte Farblogik brauchen wir nicht mehr
    status_color = s_fg  # kept for compat
    status_label = {
        "NS":  "Ausstehend",
        "1H":  "🔴 1. Halbzeit",
        "HT":  "🟡 Pause",
        "2H":  "🔴 2. Halbzeit",
        "ET":  "🟡 Verlängerung",
        "BT":  "🟡 Pause (VL)",
        "P":   "🔴 Elfmeter",
        "INT": "🟡 Unterbrochen",
        "FT":  "Abgeschlossen",
        "AET": "Abgeschlossen (VL)",
        "PEN": "Abgeschlossen (E)",
    }.get(status, status)

    api_p   = api_preds.get(fid, {})
    agent_p = agent_preds.get((home, away), {})

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

    with st.expander(expander_label, expanded=False):

        # Status-Pill — allein, kein Confidence Badge hier
        st.markdown(
            f'<div style="margin-bottom:12px">'
            f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;'
            f'background:{s_bg};color:{s_fg};font-size:0.72rem;font-weight:600">'
            f'{status_label}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Wettmarkt (Confidence Badge ist jetzt darin) ──────────────────────
        is_finished = status in {"FT", "AET", "PEN"}
        st.markdown(
            wettmarkt_html(home, away, api_p if api_p else {}, is_finished=is_finished),
            unsafe_allow_html=True,
        )

        # ── Wahrscheinlichstes Ergebnis (Exact Score) ─────────────────────────
        if fid and not is_finished:
            exact_scores = load_exact_score_odds(fid)
            if exact_scores:
                st.markdown(
                    exact_score_section_html(exact_scores),
                    unsafe_allow_html=True,
                )

        # ── Quotenverlauf ────────────────────────────────────────────────────
        if fid:
            history = load_odds_history(fid)
            if len(history) >= 2:
                import plotly.graph_objects as go
                import pandas as pd

                df = pd.DataFrame(history)
                fig = go.Figure()

                # Heimsieg — Blau
                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["home"],
                    name=f"🏠 {home}",
                    mode="lines+markers",
                    line=dict(color="#2563eb", width=2.5),
                    marker=dict(size=5, color="#2563eb", symbol="circle"),
                    hovertemplate="<b>%{y:.2f}</b><extra>" + home + "</extra>",
                ))
                # Unentschieden — Grau gestrichelt
                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["draw"],
                    name="⚖️ Unentschieden",
                    mode="lines+markers",
                    line=dict(color="#94a3b8", width=1.5, dash="dash"),
                    marker=dict(size=4, color="#94a3b8", symbol="circle"),
                    hovertemplate="<b>%{y:.2f}</b><extra>Unentschieden</extra>",
                ))
                # Auswärtssieg — Orange-Rot
                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["away"],
                    name=f"✈️ {away}",
                    mode="lines+markers",
                    line=dict(color="#dc6f5c", width=2.5),
                    marker=dict(size=5, color="#dc6f5c", symbol="circle"),
                    hovertemplate="<b>%{y:.2f}</b><extra>" + away + "</extra>",
                ))

                fig.update_layout(
                    margin=dict(l=0, r=48, t=36, b=32),
                    height=220,
                    plot_bgcolor="rgba(248,250,252,0.6)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="DM Sans", size=10, color="#64748b"),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", y=1.02,
                        xanchor="left", x=0,
                        font=dict(size=10, color="#475569"),
                        bgcolor="rgba(0,0,0,0)",
                        bordercolor="rgba(0,0,0,0)",
                        traceorder="normal",
                    ),
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(size=10, color="#64748b"),
                        tickformat="%d.%m.",
                        tickangle=0,
                        linecolor="rgba(203,213,225,0.6)",
                        linewidth=1,
                        showline=True,
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="rgba(203,213,225,0.4)",
                        zeroline=False,
                        tickfont=dict(size=10, color="#64748b"),
                        tickformat=".2f",
                        side="right",
                        title=dict(
                            text="Quote",
                            font=dict(size=10, color="#94a3b8"),
                        ),
                    ),
                    hovermode="x unified",
                    hoverlabel=dict(
                        bgcolor="white",
                        bordercolor="#e2e8f0",
                        font=dict(family="DM Sans", size=11, color="#16213e"),
                    ),
                )

                st.markdown(
                    '<div style="font-size:0.68rem;color:#8a9ab5;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:0.6px;'
                    'margin:8px 0 0 0;padding-top:10px;border-top:1px solid rgba(0,0,0,0.06)">'
                    'Quotenverlauf</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                st.markdown(
                    '<div style="font-size:0.7rem;color:#94a3b8;margin-top:-8px;margin-bottom:4px">'
                    '↓ Tiefere Quote = mehr Geld auf dieses Team = Favorit des Marktes'
                    '</div>',
                    unsafe_allow_html=True,
                )

        # ── Match-Statistiken ────────────────────────────────────────────────
        if status in ["1H", "HT", "2H", "FT", "AET", "PEN"]:

            def stat_bar(label, home_val, away_val):
                if home_val is None and away_val is None:
                    return ""
                h = home_val or 0
                a = away_val or 0
                # Beide 0 → nichts anzeigen (verhindert falsche 0%/100% Balken)
                if h == 0 and a == 0:
                    return ""
                total = h + a or 1
                h_pct = round(h / total * 100)
                a_pct = 100 - h_pct
                return (
                    f'<div style="display:grid;grid-template-columns:1fr auto 1fr;'
                    f'align-items:center;gap:8px;margin-bottom:6px">'
                    f'<div style="display:flex;align-items:center;gap:6px;justify-content:flex-end">'
                    f'<span style="font-size:0.75rem;font-weight:600;color:#16213e">{h}</span>'
                    f'<div style="height:10px;width:{h_pct}%;background:#16213e;border-radius:3px"></div>'
                    f'</div>'
                    f'<span style="font-size:0.68rem;color:#2d3a50;white-space:nowrap;text-align:center">{label}</span>'
                    f'<div style="display:flex;align-items:center;gap:6px">'
                    f'<div style="height:10px;width:{a_pct}%;background:#dc6f5c;border-radius:3px"></div>'
                    f'<span style="font-size:0.75rem;font-weight:600;color:#16213e">{a}</span>'
                    f'</div></div>'
                )

            stats = [
                # Schüsse
                ("Schüsse aufs Tor",       fx.get("home_shots_on_target"),    fx.get("away_shots_on_target")),
                ("Schüsse daneben",        fx.get("home_shots_off_target"),   fx.get("away_shots_off_target")),
                ("Schüsse geblockt",       fx.get("home_blocked_shots"),      fx.get("away_blocked_shots")),
                ("Schüsse im Strafraum",   fx.get("home_shots_insidebox"),    fx.get("away_shots_insidebox")),
                ("Schüsse ausserhalb",     fx.get("home_shots_outsidebox"),   fx.get("away_shots_outsidebox")),
                ("Schüsse total",          fx.get("home_total_shots"),        fx.get("away_total_shots")),
                # Spielkontrolle
                ("Ballbesitz %",           fx.get("home_possession"),         fx.get("away_possession")),
                ("Ecken",                  fx.get("home_corners"),            fx.get("away_corners")),
                ("Abseits",                fx.get("home_offsides"),           fx.get("away_offsides")),
                # Pässe
                ("Pässe gesamt",           fx.get("home_total_passes"),       fx.get("away_total_passes")),
                ("Pässe präzise",          fx.get("home_passes_accurate"),    fx.get("away_passes_accurate")),
                ("Pässe %",                fx.get("home_passes_pct"),         fx.get("away_passes_pct")),
                # Defensiv / Disziplin
                ("Paraden",                fx.get("home_saves"),              fx.get("away_saves")),
                ("Fouls",                  fx.get("home_fouls"),              fx.get("away_fouls")),
                ("Gelbe Karten",           fx.get("home_yellow_cards"),       fx.get("away_yellow_cards")),
                ("Rote Karten",            fx.get("home_red_cards"),          fx.get("away_red_cards")),
            ]

            bars = "".join(stat_bar(label, h, a) for label, h, a in stats)

            if bars:
                st.markdown(
                    f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(0,0,0,0.06)">'
                    f'<div style="display:grid;grid-template-columns:1fr auto 1fr;margin-bottom:10px">'
                    f'<span style="font-size:0.72rem;font-weight:600;color:#16213e">{home}</span>'
                    f'<span style="font-size:0.68rem;color:#a0aec0;text-align:center">Statistiken</span>'
                    f'<span style="font-size:0.72rem;font-weight:600;color:#dc6f5c;text-align:right">{away}</span>'
                    f'</div>{bars}</div>',
                    unsafe_allow_html=True
                )


@st.cache_data(ttl=120)
def load_odds_history(fixture_id: int) -> list:
    """Quoten-Verlaufshistorie für ein Spiel."""
    from agent.tools.mysql_tools import get_engine
    from sqlalchemy import text as sa_text
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(sa_text("""
                SELECT recorded_at, home_odds, draw_odds, away_odds
                FROM odds_history
                WHERE fixture_id = :fid
                ORDER BY recorded_at ASC
            """), {"fid": fixture_id}).fetchall()
        return [
            {"time": row[0], "home": float(row[1]), "draw": float(row[2]), "away": float(row[3])}
            for row in rows
        ]
    except Exception:
        return []


@st.cache_data(ttl=300)
def load_team_tournament_summary(team_name: str) -> dict:
    from agent.tools.mysql_tools import get_tournament_team_summary
    import json
    r = json.loads(get_tournament_team_summary(team_name, season=2026))
    rows = r.get("result", [])
    return rows[0] if rows else {}


@st.cache_data(ttl=300)
def load_team_elo(team_name: str) -> dict:
    """ELO-Rating + Pre-WM-ELO aus team_stats."""
    from agent.tools.mysql_tools import get_engine
    from sqlalchemy import text as sa_text
    with get_engine().connect() as conn:
        row = conn.execute(sa_text("""
            SELECT elo_rating, elo_rating_pre_wm
            FROM team_stats WHERE team_name = :t
        """), {"t": team_name}).fetchone()
    if row:
        return {"elo_rating": float(row[0]) if row[0] else None,
                "elo_rating_pre_wm": float(row[1]) if row[1] else None}
    return {}


def team_stat_tile(label: str, value, pct: bool = False) -> str:
    if value is None:
        return ""
    display = f"{value:.1f}%" if pct else str(int(value)) if isinstance(value, (int, float)) else str(value)
    return (
        f'<div style="background:rgba(0,0,0,0.03);border-radius:8px;padding:8px 10px;text-align:center">'
        f'<div style="font-size:1rem;font-weight:700;color:#16213e">{display}</div>'
        f'<div style="font-size:0.62rem;color:#94a3b8;margin-top:2px">{label}</div>'
        f'</div>'
    )


def elo_tile(elo: float | None, pre_wm: float | None) -> str:
    """ELO-Kachel mit WM-Veränderungspfeil."""
    if elo is None:
        return ""
    elo_int = int(round(elo))
    delta_html = ""
    if pre_wm is not None:
        delta = elo - pre_wm
        if abs(delta) >= 1:
            arrow  = "▲" if delta > 0 else "▼"
            color  = "#16a34a" if delta > 0 else "#dc2626"
            delta_html = (
                f'<div style="font-size:0.6rem;color:{color};font-weight:600;margin-top:1px">'
                f'{arrow}{abs(delta):.0f} WM</div>'
            )
    return (
        f'<div style="background:rgba(0,0,0,0.03);border-radius:8px;padding:8px 10px;text-align:center">'
        f'<div style="font-size:1rem;font-weight:700;color:#16213e">{elo_int}</div>'
        f'<div style="font-size:0.62rem;color:#94a3b8;margin-top:2px">ELO</div>'
        f'{delta_html}'
        f'</div>'
    )


def render_chat(key_suffix=""):
    st.markdown('''<div style="background:#16213e;border-radius:18px;padding:1.25rem 1.25rem 0.5rem 1.25rem;margin-bottom:0.5rem">
<div style="font-size:0.85rem;font-weight:600;color:#ffffff;padding-bottom:0.75rem;border-bottom:1px solid rgba(255,255,255,0.1)">⚽ WM-Orakel</div>
</div>''', unsafe_allow_html=True)
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    if prompt := st.chat_input("Frage stellen...", key=f"chat_{key_suffix}"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner(""):
                    response = st.session_state.agent.chat(prompt)
                st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()


# ─── Navigation ───────────────────────────────────────────────────────────────

st.markdown('''<div style="background:#16213e;border-radius:16px;padding:0.75rem 1.5rem;margin-bottom:1.5rem">
<div style="font-size:1.3rem;font-weight:600;color:#ffffff">football<span style="color:#5b9bff">Orakel</span></div>
<div style="font-size:0.75rem;color:#8a9ab5">FIFA World Cup 2026</div>
</div>''', unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns([1, 1, 1, 7])
with nav1:
    if st.button("Übersicht", use_container_width=True, type="primary" if st.session_state.page == "uebersicht" else "secondary"):
        st.session_state.page = "uebersicht"; st.rerun()
with nav2:
    if st.button("Gruppenphase", use_container_width=True, type="primary" if st.session_state.page == "gruppe" else "secondary"):
        st.session_state.page = "gruppe"; st.rerun()
with nav3:
    if st.button("KO-Phase", use_container_width=True, type="primary" if st.session_state.page == "ko" else "secondary"):
        st.session_state.page = "ko"; st.rerun()
with nav4:
    if st.button("🔄", use_container_width=False):
        st.cache_data.clear(); st.rerun()

auto_refresh()


# ─── Page: Übersicht ──────────────────────────────────────────────────────────

if st.session_state.page == "uebersicht":
    col_main, col_chat = st.columns([3, 1])
    api_preds   = {p["fixture_id"]: p for p in load_api_predictions() if p.get("fixture_id")}
    agent_preds = {}

    with col_main:
        live = load_live_fixtures()
        if live:
            st.markdown('<div class="section-title">🔴 Live</div>', unsafe_allow_html=True)
            for fx in live:
                render_match_card(fx, api_preds, agent_preds)

        today_games, tomorrow_games = load_today_upcoming()
        if today_games:
            st.markdown('<div class="section-title">Heute</div>', unsafe_allow_html=True)
            for fx in today_games:
                render_match_card(fx, api_preds, agent_preds)
        elif not live:
            st.markdown('<div class="glass"><p style="color:#a0aec0;font-size:0.85rem;text-align:center">Heute keine Spiele</p></div>', unsafe_allow_html=True)

        if tomorrow_games:
            st.markdown('<div class="section-title">Morgen</div>', unsafe_allow_html=True)
            for fx in tomorrow_games:
                render_match_card(fx, api_preds, agent_preds)

        results = load_recent_results()
        if results:
            st.markdown('<div class="section-title" style="margin-top:0.5rem">Letzte Resultate</div>', unsafe_allow_html=True)
            for fx in results:
                render_match_card(fx, api_preds, agent_preds)

    with col_chat:
        render_chat("uebersicht")


# ─── Page: Gruppenphase ───────────────────────────────────────────────────────

elif st.session_state.page == "gruppe":
    col_main, col_chat = st.columns([3, 1])
    api_preds   = {p["fixture_id"]: p for p in load_api_predictions() if p.get("fixture_id")}
    agent_preds = {}

    with col_main:
        standings = load_standings()
        groups = {}
        for row in standings:
            g = row.get("group_name", "?")
            groups.setdefault(g, []).append(row)

        if groups:
            st.markdown('<div class="section-title">Gruppentabellen</div>', unsafe_allow_html=True)
            group_names = sorted(groups.keys())
            for i in range(0, len(group_names), 2):
                gcols = st.columns(2)
                for j, gc in enumerate(gcols):
                    if i + j < len(group_names):
                        gname = group_names[i + j]
                        teams = sorted(groups[gname], key=lambda x: (-(x.get("points") or 0), -(x.get("goal_diff") or 0)))
                        rows_html = ""
                        for k, t in enumerate(teams):
                            qual_cls = "qualified" if k < 2 else "out"
                            gd = t.get("goal_diff", 0) or 0
                            gd_str = f"+{gd}" if gd > 0 else str(gd)
                            gd_color = "#15803d" if gd > 0 else ("#dc2626" if gd < 0 else "#64748b")
                            form = form_badges(str(t.get("form", "") or "")[:4])  # max 4 Spiele
                            rows_html += (
                                f'<tr class="{qual_cls}">'
                                f'<td>{t.get("team_name","")}</td>'
                                f'<td>{t.get("played","")}</td>'
                                f'<td>{t.get("won","")}</td>'
                                f'<td>{t.get("drawn","")}</td>'
                                f'<td>{t.get("lost","")}</td>'
                                f'<td style="color:{gd_color};font-weight:600">{gd_str}</td>'
                                f'<td class="pts">{t.get("points","")}</td>'
                                f'<td style="text-align:right">{form}</td>'
                                f'</tr>'
                            )
                        upd = str(teams[0].get("updated_at", "") or "")[:16] if teams else ""
                        upd_note = f'<div style="font-size:0.6rem;color:#c0cadb;margin-top:4px;text-align:right">Stand: {upd}</div>' if upd else ""
                        with gc:
                            st.markdown(
                                f'<div class="glass-sm">'
                                f'<div class="section-title">{gname}</div>'
                                f'<table class="group-table">'
                                f'<thead><tr>'
                                f'<th style="text-align:left">Team</th>'
                                f'<th title="Spiele">Sp</th>'
                                f'<th title="Siege">S</th>'
                                f'<th title="Unentschieden">U</th>'
                                f'<th title="Niederlagen">N</th>'
                                f'<th title="Tordifferenz">TD</th>'
                                f'<th title="Punkte">Pkt</th>'
                                f'<th style="text-align:right">Form</th>'
                                f'</tr></thead>'
                                f'<tbody>{rows_html}</tbody>'
                                f'</table>'
                                f'{upd_note}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
        else:
            st.markdown('<div class="glass"><p style="color:#a0aec0;font-size:0.85rem;text-align:center">Gruppentabellen verfügbar ab Turnierbeginn · 11. Juni 2026</p></div>', unsafe_allow_html=True)

        # ── Team-Turnierstatistik ─────────────────────────────────────────────
        st.markdown('<div class="section-title" style="margin-top:0.5rem">Team-Turnierstatistik</div>', unsafe_allow_html=True)
        all_team_names = sorted(set(
            r.get("team_name", "") for r in standings if r.get("team_name")
        ))
        if all_team_names:
            sel_team = st.selectbox("Team wählen", all_team_names, label_visibility="collapsed", key="team_stats_select")
            if sel_team:
                ts  = load_team_tournament_summary(sel_team)
                elo = load_team_elo(sel_team)
                if ts and ts.get("games_played", 0):
                    g = ts["games_played"]
                    gf, ga = ts.get("goals_scored") or 0, ts.get("goals_conceded") or 0
                    st.markdown(
                        f'<div class="glass-sm">'
                        # Kopfzeile
                        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px">'
                        f'<span style="font-size:0.85rem;font-weight:600;color:#16213e">{sel_team}</span>'
                        f'<span style="font-size:0.72rem;color:#8a9ab5">{g} Spiele · {ts.get("wins",0)}S {ts.get("draws",0)}U {ts.get("losses",0)}N · {gf}:{ga} Tore</span>'
                        f'</div>'
                        # Stat-Grid
                        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'
                        + elo_tile(elo.get("elo_rating"), elo.get("elo_rating_pre_wm"))
                        + team_stat_tile("Tore erzielt",       ts.get("goals_scored"))
                        + team_stat_tile("Tore erhalten",      ts.get("goals_conceded"))
                        + team_stat_tile("Schüsse aufs Tor",   ts.get("shots_on_target"))
                        + team_stat_tile("Schüsse gesamt",     ts.get("total_shots"))
                        + team_stat_tile("Im Strafraum",       ts.get("shots_insidebox"))
                        + team_stat_tile("Ballbesitz Ø",       ts.get("avg_possession"), pct=True)
                        + team_stat_tile("Pässe gesamt",       ts.get("total_passes"))
                        + team_stat_tile("Pass-Genauigkeit",   ts.get("avg_pass_accuracy"), pct=True)
                        + team_stat_tile("Paraden",            ts.get("goalkeeper_saves"))
                        + team_stat_tile("Fouls",              ts.get("fouls"))
                        + f'</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    # Kein WM-Spiel absolviert — nur ELO anzeigen
                    elo_html = elo_tile(elo.get("elo_rating"), elo.get("elo_rating_pre_wm"))
                    st.markdown(
                        f'<div class="glass-sm">'
                        f'<div style="display:flex;align-items:center;gap:12px">'
                        f'{elo_html}'
                        f'<p style="color:#a0aec0;font-size:0.82rem;margin:0">{sel_team} hat noch keine WM-Spiele absolviert.</p>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )

        # ── Spiele nach Gruppe ────────────────────────────────────────────────
        st.markdown('<div class="section-title" style="margin-top:0.5rem">Spiele</div>', unsafe_allow_html=True)
        real_groups = sorted(set(r.get("group_name", "") for r in standings if r.get("group_name")))
        group_options = real_groups if real_groups else ["Group A", "Group B", "Group C"]
        selected_group = st.selectbox("Gruppe wählen", group_options, label_visibility="collapsed")
        fixtures = load_fixtures_by_group(selected_group)
        if fixtures:
            for fx in fixtures:
                render_match_card(fx, api_preds, agent_preds)
        else:
            st.markdown('<div class="glass"><p style="color:#a0aec0;font-size:0.85rem;text-align:center">Keine Spiele gefunden</p></div>', unsafe_allow_html=True)

    with col_chat:
        render_chat("gruppe")


# ─── Page: KO-Phase ───────────────────────────────────────────────────────────

elif st.session_state.page == "ko":
    col_main, col_chat = st.columns([3, 1])

    with col_main:
        ko_fixtures = load_ko_fixtures()

        stage_map = {
            "round of 32": "Sechzehntelfinale", "sechzehntelfinale": "Sechzehntelfinale",
            "round of 16": "Achtelfinale", "achtelfinale": "Achtelfinale",
            "quarter-final": "Viertelfinal", "quarter-finals": "Viertelfinal",
            "semi-final": "Halbfinal", "semi-finals": "Halbfinal",
            "3rd place final": "Finale", "final": "Finale",
        }

        static_rounds = {
            "Sechzehntelfinale": [
                {"date": "28.06.", "label": "2A:2B"}, {"date": "29.06.", "label": "1C:2F"},
                {"date": "29.06.", "label": "1E:3."},  {"date": "30.06.", "label": "1F:2C"},
                {"date": "30.06.", "label": "2E:2I"},  {"date": "30.06.", "label": "1I:3."},
                {"date": "01.07.", "label": "1A:3."},  {"date": "01.07.", "label": "1L:3."},
                {"date": "01.07.", "label": "1G:3."},  {"date": "02.07.", "label": "1D:3."},
                {"date": "02.07.", "label": "1H:2J"},  {"date": "03.07.", "label": "2K:2L"},
                {"date": "03.07.", "label": "1B:3."},  {"date": "03.07.", "label": "2D:2G"},
                {"date": "04.07.", "label": "1J:2H"},  {"date": "04.07.", "label": "1K:3."},
            ],
            "Achtelfinale":  [{"date": "04.07."}, {"date": "04.07."}, {"date": "05.07."}, {"date": "06.07."}, {"date": "06.07."}, {"date": "07.07."}, {"date": "07.07."}, {"date": "07.07."}],
            "Viertelfinal":  [{"date": "09.07."}, {"date": "10.07."}, {"date": "11.07."}, {"date": "12.07."}],
            "Halbfinal":     [{"date": "14.07."}, {"date": "15.07."}],
            "Finale":        [{"date": "18.07. 🥉"}, {"date": "19.07. 🏆"}],
        }

        round_db = {k: [] for k in static_rounds}
        for fx in ko_fixtures:
            stage_raw = fx.get("stage", "").lower()
            for key, label in stage_map.items():
                if key in stage_raw:
                    round_db[label].append(fx)
                    break

        for round_name, db_fxs in round_db.items():
            for i, fx in enumerate(db_fxs):
                if i < len(static_rounds[round_name]):
                    static_rounds[round_name][i]["home"] = fx.get("home_team")
                    static_rounds[round_name][i]["away"] = fx.get("away_team")
                    hs = fx.get("home_score"); aws = fx.get("away_score")
                    if hs is not None and aws is not None:
                        static_rounds[round_name][i]["score"] = f"{int(hs)}:{int(aws)}"

        st.markdown('<div class="section-title">KO-Phase · 28. Juni – 19. Juli 2026</div>', unsafe_allow_html=True)
        cols = st.columns([2, 1.5, 1, 0.8, 0.8])

        for col, round_name in zip(cols, ["Sechzehntelfinale", "Achtelfinale", "Viertelfinal", "Halbfinal", "Finale"]):
            with col:
                st.markdown(f'<div class="section-title">{round_name}</div>', unsafe_allow_html=True)
                for fx in static_rounds[round_name]:
                    home  = fx.get("home") or "TBD"
                    away  = fx.get("away") or "TBD"
                    dt    = fx.get("date", "")
                    label = fx.get("label", "")
                    score = fx.get("score", "")
                    hc    = "#16213e" if home != "TBD" else "#c0cadb"
                    ac    = "#16213e" if away != "TBD" else "#c0cadb"
                    score_part = f'<div style="font-size:0.75rem;font-weight:600;color:#16213e;margin:1px 0">{score}</div>' if score else ""
                    label_part = f'<div style="font-size:0.6rem;color:#b0bccc;font-style:italic">{label}</div>' if home == "TBD" and label else ""
                    st.markdown(
                        f'<div style="background:rgba(255,255,255,0.7);border:1px solid rgba(200,210,230,0.5);border-radius:10px;padding:7px 10px;margin-bottom:6px">'
                        f'<div style="font-size:0.62rem;color:#a0aec0">{dt}</div>'
                        f'{label_part}'
                        f'<div style="font-size:0.75rem;color:{hc};font-weight:{"500" if home != "TBD" else "400"}">{home}</div>'
                        f'{score_part}'
                        f'<div style="font-size:0.75rem;color:{ac};font-weight:{"500" if away != "TBD" else "400"}">{away}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    with col_chat:
        render_chat("ko")