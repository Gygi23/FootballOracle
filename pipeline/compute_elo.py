"""
compute_elo.py — ELO-Rating aus historischen Matches berechnen

Formel:
    E_A = 1 / (1 + 10^((ELO_B - ELO_A) / 400))     # Erwartete Siegchance
    ELO_A += K × (Ergebnis - E_A)                    # Update nach Spiel

K-Faktoren nach Spielwichtigkeit:
    60  FIFA World Cup / WM
    50  FIFA Confederations Cup / Olympic
    40  Continental (UEFA Euro, Copa America, AFCON, ...)
    25  FIFA Qualifier / Nations League
    10  Friendly

Start-ELO: 1500 für alle Teams
Quelle: historische matches-Tabelle + WM-2026-Fixtures
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

BASE_ELO   = 1500.0
ELO_SCALE  = 400.0  # Skalierungsfaktor in der Erwartungsformel


# ─── K-Faktor Tabelle ─────────────────────────────────────────────────────────

def _k_factor(tournament: str) -> int:
    t = (tournament or "").lower()
    if "fifa world cup" in t or "world cup" in t or t == "wc":
        return 60
    if "confederation" in t or "olympic" in t:
        return 50
    if any(x in t for x in ["euro", "copa america", "africa cup", "afcon", "asian cup",
                              "gold cup", "nations cup", "continental"]):
        return 40
    if any(x in t for x in ["qualifier", "qualifying", "nations league", "wc qualification"]):
        return 25
    return 10  # Friendly / Sonstige


# ─── ELO Berechnung ───────────────────────────────────────────────────────────

def _expected(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / ELO_SCALE))


def _update(elo_a: float, elo_b: float, result_a: float, k: int) -> tuple[float, float]:
    """
    result_a: 1.0 = A gewinnt, 0.5 = Unentschieden, 0.0 = B gewinnt
    Gibt (neues_elo_a, neues_elo_b) zurück.
    """
    e_a = _expected(elo_a, elo_b)
    e_b = 1.0 - e_a
    new_a = elo_a + k * (result_a       - e_a)
    new_b = elo_b + k * ((1 - result_a) - e_b)
    return new_a, new_b


# ─── Hauptfunktion ────────────────────────────────────────────────────────────

def run():
    print("ELO-Rating berechnen...")

    # ── Historische Matches laden ─────────────────────────────────────────────
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT date, home_team, away_team, home_score, away_score, tournament
            FROM matches
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            ORDER BY date ASC
        """)).fetchall()

    # ── WM-2026-Fixtures laden ────────────────────────────────────────────────
    with engine.connect() as conn:
        wm_rows = conn.execute(text("""
            SELECT match_date, home_team, away_team, home_score, away_score
            FROM tournament_fixtures
            WHERE season = 2026 AND league_id = 1
              AND status IN ('FT', 'AET', 'PEN')
              AND home_score IS NOT NULL
            ORDER BY match_date ASC
        """)).fetchall()

    total_matches = len(rows) + len(wm_rows)
    print(f"  {len(rows)} historische Spiele + {len(wm_rows)} WM-2026-Spiele")

    # ── ELO berechnen ────────────────────────────────────────────────────────
    elo: dict[str, float] = {}

    def get_elo(team: str) -> float:
        return elo.get(team, BASE_ELO)

    processed = 0
    for row in rows:
        home, away = row.home_team, row.away_team
        hs, aws    = row.home_score, row.away_score
        tournament  = row.tournament or ""
        k = _k_factor(tournament)

        if hs > aws:
            result = 1.0
        elif hs == aws:
            result = 0.5
        else:
            result = 0.0

        e_home, e_away = get_elo(home), get_elo(away)
        elo[home], elo[away] = _update(e_home, e_away, result, k)
        processed += 1

    # ── Snapshot vor WM-Spielen (pre-WM ELO) ─────────────────────────────────
    elo_pre_wm = dict(elo)  # Kopie nach historischen Matches, vor WM 2026

    # WM 2026 mit höchstem K-Faktor
    for row in wm_rows:
        home, away = row.home_team, row.away_team
        hs, aws    = int(row.home_score), int(row.away_score)
        k = 60  # WM-Faktor

        result = 1.0 if hs > aws else (0.5 if hs == aws else 0.0)
        e_home, e_away = get_elo(home), get_elo(away)
        elo[home], elo[away] = _update(e_home, e_away, result, k)
        processed += 1

    print(f"  {processed} Spiele verarbeitet")

    # ── Top-10 zur Kontrolle ──────────────────────────────────────────────────
    top = sorted(elo.items(), key=lambda x: -x[1])[:10]
    print("  Top-10 ELO:")
    for i, (team, rating) in enumerate(top, 1):
        pre = elo_pre_wm.get(team, BASE_ELO)
        delta = rating - pre
        sign  = "▲" if delta >= 0 else "▼"
        print(f"    {i:2}. {team:<30} {rating:.0f}  ({sign}{abs(delta):.0f} WM)")

    # ── In team_stats speichern ───────────────────────────────────────────────
    updated = 0
    with engine.connect() as conn:
        for team, rating in elo.items():
            pre_wm = elo_pre_wm.get(team, BASE_ELO)
            result = conn.execute(text("""
                UPDATE team_stats
                SET elo_rating        = :elo,
                    elo_rating_pre_wm = :pre_wm
                WHERE team_name = :team
            """), {"elo": round(rating, 2), "pre_wm": round(pre_wm, 2), "team": team})
            updated += result.rowcount
        conn.commit()

    print(f"  {updated} team_stats-Einträge mit ELO aktualisiert")
    print(f"  ELO-Spanne: {min(elo.values()):.0f} – {max(elo.values()):.0f}")


if __name__ == "__main__":
    run()
