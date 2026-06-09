"""
migrate_db.py — Alle Schema-Migrationen in chronologischer Reihenfolge.

Jede Migration ist idempotent (läuft mehrfach ohne Fehler).
Beim Hosting auf neuem Server: einmalig ausführen.

Ausführen:
    python pipeline/migrate_db.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)


def add_column_if_missing(conn, table: str, column: str, definition: str):
    exists = conn.execute(text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name   = :t
          AND column_name  = :c
    """), {"t": table, "c": column}).scalar()
    if exists:
        print(f"  skip  {table}.{column}")
    else:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        conn.commit()
        print(f"  added {table}.{column}")


MIGRATIONS = [
    # ── 2026-06-09: Quotenbewegung ───────────────────────────────────────────
    ("api_predictions",     "home_odds_open",         "DECIMAL(6,3) DEFAULT NULL AFTER away_odds"),
    ("api_predictions",     "draw_odds_open",         "DECIMAL(6,3) DEFAULT NULL AFTER home_odds_open"),
    ("api_predictions",     "away_odds_open",         "DECIMAL(6,3) DEFAULT NULL AFTER draw_odds_open"),

    # ── 2026-06-09: Shots outsidebox ─────────────────────────────────────────
    ("tournament_fixtures", "home_shots_outsidebox",  "INT DEFAULT NULL AFTER home_shots_insidebox"),
    ("tournament_fixtures", "away_shots_outsidebox",  "INT DEFAULT NULL AFTER away_shots_insidebox"),

    # ── 2026-06-09: ELO-Rating ───────────────────────────────────────────────
    ("team_stats",          "elo_rating",             "DECIMAL(8,2) DEFAULT 1500.0"),
    ("team_stats",          "elo_rating_pre_wm",      "DECIMAL(8,2) DEFAULT NULL"),
]


def run():
    print(f"footballAI – migrate_db.py ({len(MIGRATIONS)} Migrationen)\n")
    with engine.connect() as conn:
        for table, column, definition in MIGRATIONS:
            add_column_if_missing(conn, table, column, definition)
    print("\nFertig.")


if __name__ == "__main__":
    run()
