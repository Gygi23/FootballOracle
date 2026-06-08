import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

RELEVANT_TOURNAMENTS = [
    "FIFA World Cup",
    "FIFA World Cup qualification",
    "UEFA Euro",
    "UEFA Euro qualification",
    "Copa América",
    "African Cup of Nations",
    "African Cup of Nations qualification",
    "AFC Asian Cup",
    "AFC Asian Cup qualification",
    "Gold Cup",
    "UEFA Nations League",
    "CONCACAF Nations League",
    "Friendly"
]

# load csv
df = pd.read_csv("data/raw/results.csv")
shootouts = pd.read_csv("data/raw/shootouts.csv")

# date as datetime
df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
shootouts["date"] = pd.to_datetime(shootouts["date"]).dt.strftime("%Y-%m-%d")

# only from 2010
df = df[df["date"] >= "2010-01-01"] 

# only relevant columns
df = df[["date", "home_team", "away_team", "home_score", "away_score", "tournament"]]

# define tournament stage
def get_stage(tournamnet):
    t = tournamnet.lower()
    if "world cup" in t and "qualification" not in t:
        return "WC"
    elif "qualification" in t:
        return "QUAL"
    elif "friendly" in t:
        return "FRIENDLY"
    elif "uefa euro" in t or "nations league" in t:
        return "CONTINENTAL"
    elif "copa america" in t or "asia cup" in t or "africa cup" in t or "gold cup" in t:
        return "CONTINENTAL"
    else:
        return "OTHER"
    
df["stage"] = df["tournament"].apply(get_stage)

# merge shootout
df = df.merge(
    shootouts[["date", "home_team", "away_team", "winner"]],
    on=["date", "home_team", "away_team"],
    how="left"
)
df.rename(columns={"winner": "shootout_winner"}, inplace=True)

# check
print(f"Total Spiele: {len(df)}")
print(f"Davon mit Elfmeterschiessen: {df['shootout_winner'].notna().sum()}")

# delete existing data's to avoid duplicates
with engine.connect() as conn:
    conn.execute(text("DELETE FROM matches"))
    conn.commit()

# laod in DB
df.to_sql("matches", con=engine, if_exists="append", index=False)
print(f"{len(df)} Spiele geladen.")

