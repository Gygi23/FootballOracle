import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

# Pfad zur FIFA-Ranking CSV (relativ zum Projekt-Root)
_FIFA_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "fifa_ranking.csv")


def _get_result(row) -> str:
    if row["goals_scored"] > row["goals_conceded"]:
        return "W"
    elif row["goals_scored"] == row["goals_conceded"]:
        return "D"
    else:
        return "L"


def run():
    print("Team-KPIs berechnen...")

    # ── 1. Historische Daten (Kaggle matches) ────────────────────────────────
    df = pd.read_sql("SELECT * FROM matches", engine)
    df["date"] = pd.to_datetime(df["date"])

    hist_home = df[["date", "home_team", "away_team", "home_score", "away_score",
                    "stage", "shootout_winner"]].copy()
    hist_home.columns = ["date", "team", "opponent", "goals_scored", "goals_conceded",
                         "stage", "shootout_winner"]
    hist_home["is_home"] = True

    hist_away = df[["date", "away_team", "home_team", "away_score", "home_score",
                    "stage", "shootout_winner"]].copy()
    hist_away.columns = ["date", "team", "opponent", "goals_scored", "goals_conceded",
                         "stage", "shootout_winner"]
    hist_away["is_home"] = False

    matches_long = pd.concat([hist_home, hist_away], ignore_index=True)

    # ── 2. WM-2026-Spiele aus tournament_fixtures ────────────────────────────
    wm_df = pd.read_sql("""
        SELECT home_team, away_team, home_score, away_score, match_date, stage
        FROM tournament_fixtures
        WHERE season   = 2026
          AND league_id = 1
          AND status   IN ('FT', 'AET', 'PEN')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """, engine)

    if not wm_df.empty:
        wm_df["match_date"] = pd.to_datetime(wm_df["match_date"])

        wm_home = wm_df[["match_date", "home_team", "away_team",
                          "home_score", "away_score", "stage"]].copy()
        wm_home.columns = ["date", "team", "opponent",
                           "goals_scored", "goals_conceded", "stage"]
        wm_home["is_home"] = True
        wm_home["shootout_winner"] = None   # nicht in tournament_fixtures gespeichert

        wm_away = wm_df[["match_date", "away_team", "home_team",
                          "away_score", "home_score", "stage"]].copy()
        wm_away.columns = ["date", "team", "opponent",
                           "goals_scored", "goals_conceded", "stage"]
        wm_away["is_home"] = False
        wm_away["shootout_winner"] = None

        tournament_long = pd.concat([wm_home, wm_away], ignore_index=True)
        matches_long = pd.concat([matches_long, tournament_long], ignore_index=True)
        print(f"  {len(wm_df)} abgeschlossene WM-2026-Spiele einbezogen")
    else:
        print("  Noch keine abgeschlossenen WM-2026-Spiele — nur historische Daten")

    # ── 3. Sortieren + Ergebnis berechnen ────────────────────────────────────
    matches_long = matches_long.sort_values("date").reset_index(drop=True)
    matches_long["result"] = matches_long.apply(_get_result, axis=1)

    # ── 4. KPIs pro Team ─────────────────────────────────────────────────────
    stats = []

    for team, group in matches_long.groupby("team"):
        total       = len(group)
        wins        = (group["result"] == "W").sum()
        clean_sheets = (group["goals_conceded"] == 0).sum()

        # Letzte 5 Spiele (chronologisch — WM-Spiele erscheinen zuletzt)
        last5 = group.tail(5)["result"].tolist()
        form  = "".join(last5)

        # Shootout-Stats (nur aus historischen Daten — tournament_fixtures hat kein shootout_winner)
        shootout_games   = group[group["shootout_winner"].notna()]
        shootout_total   = len(shootout_games)
        shootout_wins    = (shootout_games["shootout_winner"] == team).sum()
        shootout_win_rate = (
            round(shootout_wins / shootout_total, 3)
            if shootout_total >= 3
            else None
        )

        avg_goals    = round(group["goals_scored"].mean(), 3)
        avg_conceded = round(group["goals_conceded"].mean(), 3)

        stats.append({
            "team_name":        team,
            "win_rate":         round(wins / total, 3),
            "avg_goals":        avg_goals,
            "avg_conceded":     avg_conceded,
            "goal_difference":  round(avg_goals - avg_conceded, 3),
            "form_last5":       form,
            "clean_sheet_rate": round(clean_sheets / total, 3),
            "shootout_wins":    int(shootout_wins),
            "shootout_total":   int(shootout_total),
            "shootout_win_rate": shootout_win_rate,
        })

    stats_df = pd.DataFrame(stats)

    # ── 5. FIFA-Ranking einjoinen ─────────────────────────────────────────────
    latest_rank = pd.read_csv(_FIFA_CSV)
    stats_df = stats_df.merge(latest_rank, on="team_name", how="left")

    # ── 6. In team_stats schreiben ────────────────────────────────────────────
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM team_stats"))
        conn.commit()

    stats_df.to_sql("team_stats", con=engine, if_exists="append", index=False)

    wm_count = len(wm_df) if not wm_df.empty else 0
    print(f"  {len(stats_df)} Teams in team_stats geschrieben")
    print(f"  Davon mit FIFA-Rang: {stats_df['fifa_rank'].notna().sum()}")
    print(f"  Davon mit Shootout-Daten: {(stats_df['shootout_total'] > 0).sum()}")
    print(f"  WM-2026-Spiele einbezogen: {wm_count}")


if __name__ == "__main__":
    run()
