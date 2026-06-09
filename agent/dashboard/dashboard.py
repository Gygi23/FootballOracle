import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import streamlit.components.v1 as components
from datetime import date

st.set_page_config(
    page_title="football Orakel – WM 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
}
.section-title {
    font-size: 0.8rem; font-weight: 600; color: #8a9ab5;
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.75rem;
}
.group-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.group-table th { color: #a0aec0; font-weight: 500; font-size: 0.72rem; text-align: center; padding: 4px 6px; border-bottom: 1px solid rgba(0,0,0,0.05); }
.group-table th:first-child { text-align: left; }
.group-table td { padding: 7px 6px; text-align: center; color: #16213e; border-bottom: 1px solid rgba(0,0,0,0.04); }
.group-table td:first-child { text-align: left; font-weight: 500; }
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
    import os
    from agent.agent import FootballAIAgent
    _llm_backend = os.getenv("LLM_BACKEND", "gemini").lower()
    if _llm_backend == "ollama":
        from agent.llm.ollama import OllamaLLM
        st.session_state.agent = FootballAIAgent(llm=OllamaLLM())
    else:
        from agent.llm.gemini import GeminiLLM
        st.session_state.agent = FootballAIAgent(llm=GeminiLLM())


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

@st.cache_data(ttl=300)
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
def load_agent_predictions():
    from agent.tools.mysql_tools import get_agent_predictions
    import json
    r = json.loads(get_agent_predictions(limit=100))
    return r.get("result", [])

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
        "HIGH":   ("Markt sicher",  "#d4edda", "#1a6b2e"),
        "MEDIUM": ("Markt neutral", "#fff3cd", "#856404"),
        "LOW":    ("Offenes Spiel", "#f8d7da", "#842029"),
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

    dt = str(match_date)[:16].replace("T", " ")
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

    status_color = {
        "NS": "#a0aec0", "1H": "#22c55e", "HT": "#f59e0b",
        "2H": "#22c55e", "FT": "#16213e", "AET": "#16213e", "PEN": "#16213e"
    }.get(status, "#a0aec0")
    status_label = {
        "NS": "Ausstehend", "1H": "🔴 1. HZ", "HT": "🟡 Pause",
        "2H": "🔴 2. HZ", "FT": "Abgeschlossen",
        "AET": "Abgeschlossen (VL)", "PEN": "Abgeschlossen (E)"
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

        # Status + Confidence Badge
        conf_badge = confidence_badge(api_p.get("market_confidence")) if api_p else ""
        st.markdown(
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px">'
            f'<span style="font-size:0.75rem;color:{status_color};font-weight:600">{status_label}</span>'
            f'{conf_badge}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Prognosen ────────────────────────────────────────────────────────
        pred_html = ""
        if api_p and api_p.get("home_win_pct"):
            pred_html += pred_row_html(
                "Football API",
                api_p.get("home_win_pct"),
                api_p.get("draw_pct"),
                api_p.get("away_win_pct")
            )
        if agent_p:
            pred_html += pred_row_html(
                "WM-Orakel",
                agent_p.get("home_win_prob"),
                agent_p.get("draw_prob"),
                agent_p.get("away_win_prob")
            )
        if pred_html:
            st.markdown(
                f'<div style="font-size:0.7rem;font-weight:600;color:#a0aec0;'
                f'text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px">'
                f'Prognosen</div>{pred_html}',
                unsafe_allow_html=True
            )

        # ── Wettmarkt ────────────────────────────────────────────────────────
        if api_p and api_p.get("home_odds"):
            st.markdown(
                '<div style="font-size:0.7rem;font-weight:600;color:#a0aec0;'
                'text-transform:uppercase;letter-spacing:0.6px;'
                'margin-top:12px;margin-bottom:6px">Wettmarkt</div>',
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

            # ── Konsens-Quoten (Kacheln) ──────────────────────────────────
            meta_parts = []
            if bm_cnt is not None:
                meta_parts.append(f"{bm_cnt} Bookmakers")
            if margin is not None:
                meta_parts.append(f"Margin {round(margin * 100, 1)}%")
            meta_str = f"Konsens · {' · '.join(meta_parts)}" if meta_parts else ""

            st.markdown(
                odds_tiles_html(
                    label="Konsens-Quoten",
                    home_team=home, away_team=away,
                    h_odd=h_odd, d_odd=d_odd, a_odd=a_odd,
                    meta=meta_str,
                ),
                unsafe_allow_html=True,
            )

            # ── Implizite Wahrscheinlichkeiten (margin-bereinigt) ─────────
            if any(x is not None for x in (h_impl, d_impl, a_impl)):
                st.markdown(
                    odds_tiles_html(
                        label="Implizite W'keiten",
                        home_team=home, away_team=away,
                        h_odd=0, d_odd=0, a_odd=0,
                        h_prob=h_impl, d_prob=d_impl, a_prob=a_impl,
                    ),
                    unsafe_allow_html=True,
                )

            # ── Pinnacle ──────────────────────────────────────────────────
            if h_pin:
                st.markdown(
                    odds_tiles_html(
                        label="Pinnacle",
                        home_team=home, away_team=away,
                        h_odd=h_pin,
                        d_odd=api_p.get("draw_odds_pinnacle") or 0,
                        a_odd=api_p.get("away_odds_pinnacle") or 0,
                    ),
                    unsafe_allow_html=True,
                )

            # ── Betfair ───────────────────────────────────────────────────
            if h_bf:
                st.markdown(
                    odds_tiles_html(
                        label="Betfair",
                        home_team=home, away_team=away,
                        h_odd=h_bf,
                        d_odd=api_p.get("draw_odds_betfair") or 0,
                        a_odd=api_p.get("away_odds_betfair") or 0,
                    ),
                    unsafe_allow_html=True,
                )

        elif not pred_html:
            st.markdown(
                '<p style="font-size:0.75rem;color:#c0cadb;margin:4px 0">Predictions folgen</p>',
                unsafe_allow_html=True
            )

        # ── Match-Statistiken ────────────────────────────────────────────────
        if status in ["1H", "HT", "2H", "FT", "AET", "PEN"]:

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
                    f'<span style="font-size:0.75rem;font-weight:600;color:#16213e">{h}</span>'
                    f'<div style="height:10px;width:{h_pct}%;background:#16213e;border-radius:3px;min-width:2px"></div>'
                    f'</div>'
                    f'<span style="font-size:0.68rem;color:#2d3a50;white-space:nowrap;text-align:center">{label}</span>'
                    f'<div style="display:flex;align-items:center;gap:6px">'
                    f'<div style="height:10px;width:{a_pct}%;background:#dc6f5c;border-radius:3px;min-width:2px"></div>'
                    f'<span style="font-size:0.75rem;font-weight:600;color:#16213e">{a}</span>'
                    f'</div></div>'
                )

            stats = [
                ("Schüsse aufs Tor", fx.get("home_shots_on_target"),  fx.get("away_shots_on_target")),
                ("Schüsse total",    fx.get("home_total_shots"),       fx.get("away_total_shots")),
                ("Ballbesitz %",     fx.get("home_possession"),        fx.get("away_possession")),
                ("Ecken",            fx.get("home_corners"),           fx.get("away_corners")),
                ("Fouls",            fx.get("home_fouls"),             fx.get("away_fouls")),
                ("Gelbe Karten",     fx.get("home_yellow_cards"),      fx.get("away_yellow_cards")),
                ("Rote Karten",      fx.get("home_red_cards"),         fx.get("away_red_cards")),
                ("Paraden",          fx.get("home_saves"),             fx.get("away_saves")),
                ("Pässe",            fx.get("home_total_passes"),      fx.get("away_total_passes")),
                ("Pässe %",          fx.get("home_passes_pct"),        fx.get("away_passes_pct")),
                ("Abseits",          fx.get("home_offsides"),          fx.get("away_offsides")),
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
    agent_preds = {(p["home_team"], p["away_team"]): p for p in load_agent_predictions()}

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
    agent_preds = {(p["home_team"], p["away_team"]): p for p in load_agent_predictions()}

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
                            form = form_badges(t.get("form", ""))
                            rows_html += f'<tr class="{qual_cls}"><td>{t.get("team_name","")}</td><td>{t.get("won","")}</td><td>{t.get("drawn","")}</td><td>{t.get("lost","")}</td><td class="pts">{t.get("points","")}</td><td style="text-align:right">{form}</td></tr>'
                        with gc:
                            st.markdown(f'<div class="glass-sm"><div class="section-title">{gname}</div><table class="group-table"><thead><tr><th style="text-align:left">Team</th><th>S</th><th>U</th><th>N</th><th>Pkt</th><th style="text-align:right">Form</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass"><p style="color:#a0aec0;font-size:0.85rem;text-align:center">Gruppentabellen verfügbar ab Turnierbeginn · 11. Juni 2026</p></div>', unsafe_allow_html=True)

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