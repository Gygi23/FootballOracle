import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine =create_engine(
  f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
 )

# load matches
df = pd.read_sql("SELECT * FROM matches", engine)
df["date"] = pd.to_datetime(df["date"])

# turn matches in long-format (every team once per game)
home = df[["date", "home_team", "away_team", "home_score", "away_score", "stage", "shootout_winner"]].copy()
home.columns = ["date", "team", "opponent", "goals_scored", "goals_conceded", "stage", "shootout_winner"]
home["is_home"] = True

away = df[["date", "away_team", "home_team", "away_score", "home_score", "stage", "shootout_winner"]].copy()
away.columns = ["date", "team", "opponent", "goals_scored", "goals_conceded", "stage", "shootout_winner"]
away["is_home"] = False

matches_long = pd.concat([home, away], ignore_index=True)
matches_long = matches_long.sort_values("date")

# calculate results
def get_result(row):
    if row["goals_scored"] > row["goals_conceded"]:
        return "W"
    elif row["goals_scored"] == row["goals_conceded"]:
        return "D"
    else:
        return "L"

matches_long["result"] = matches_long.apply(get_result, axis=1)

# calculate stats per team
stats = []

for team, group in matches_long.groupby("team"):
    total = len(group)
    wins = (group["result"] == "W").sum()
    clean_sheets = (group["goals_conceded"] == 0).sum()

    # last 5 games
    last5 = group.tail(5)["result"].tolist()
    form = "".join(last5)

    # shootout stats
    shootout_games = group[group["shootout_winner"].notna()]
    shootout_total = len(shootout_games)
    shootout_wins = (shootout_games["shootout_winner"] == team).sum()
    shootout_win_rate = (
        round(shootout_wins / shootout_total, 3)
        if shootout_total >= 3
        else None
    )

    avg_goals = round(group["goals_scored"].mean(),3)
    avg_conceded = round(group["goals_conceded"].mean(),3)

    stats.append({
        "team_name": team,
        "win_rate": round(wins / total, 3),
        "avg_goals": avg_goals,
        "avg_conceded": avg_conceded,
        "goal_difference": round(avg_goals - avg_conceded, 3),
        "form_last5": form,
        "clean_sheet_rate": round(clean_sheets / total, 3),
        "shootout_wins": int(shootout_wins),
        "shootout_total": int(shootout_total),
        "shootout_win_rate": shootout_win_rate,
    })
    
stats_df = pd.DataFrame(stats)

# load and join fifa ranking
latest_rank = pd.read_csv("data/raw/fifa_ranking.csv")
stats_df = stats_df.merge(latest_rank, on="team_name", how="left")

# write in team stats
with engine.connect() as conn:
    conn.execute(text("DELETE FROM team_stats"))
    conn.commit()

stats_df.to_sql("team_stats", con=engine, if_exists="append", index=False)

print(f"{len(stats_df)} Teams in team_stats geschrieben")
print(f"Davon mit Fifa Rank: {stats_df['fifa_rank'].notna().sum()}")
print(f"Davon mit Shootout-Daten: {(stats_df['shootout_total'] > 0).sum()}")

