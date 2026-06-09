from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INT,
    away_score INT,
    tournament VARCHAR(100),
    stage VARCHAR(50),
    shootout_winner VARCHAR(100) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS team_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(100) UNIQUE,
    fifa_rank INT,
    win_rate FLOAT,
    avg_goals FLOAT,
    avg_conceded FLOAT,
    goal_difference FLOAT,
    form_last5 VARCHAR(10),
    clean_sheet_rate FLOAT,
    shootout_wins INT DEFAULT 0,
    shootout_total INT DEFAULT 0,
    shootout_win_rate FLOAT DEFAULT NULL,
    elo_rating DECIMAL(8,2) DEFAULT 1500.0,
    elo_rating_pre_wm DECIMAL(8,2) DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_win_prob FLOAT,
    draw_prob FLOAT,
    away_win_prob FLOAT,
    predicted_winner VARCHAR(100),
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    endpoint VARCHAR(200) UNIQUE,
    calls_today INT DEFAULT 0,
    last_called TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tournament_fixtures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fixture_id INT UNIQUE,
    league_id INT,
    season INT,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    match_date DATETIME,
    stage VARCHAR(100),
    status VARCHAR(20),
    home_score INT DEFAULT NULL,
    away_score INT DEFAULT NULL,
    -- Ballbesitz
    home_possession FLOAT DEFAULT NULL,
    away_possession FLOAT DEFAULT NULL,
    -- Schüsse
    home_shots_on_target INT DEFAULT NULL,
    away_shots_on_target INT DEFAULT NULL,
    home_shots_off_target INT DEFAULT NULL,
    away_shots_off_target INT DEFAULT NULL,
    home_total_shots INT DEFAULT NULL,
    away_total_shots INT DEFAULT NULL,
    home_blocked_shots INT DEFAULT NULL,
    away_blocked_shots INT DEFAULT NULL,
    home_shots_insidebox INT DEFAULT NULL,
    away_shots_insidebox INT DEFAULT NULL,
    home_shots_outsidebox INT DEFAULT NULL,
    away_shots_outsidebox INT DEFAULT NULL,
    -- Defensiv
    home_saves INT DEFAULT NULL,
    away_saves INT DEFAULT NULL,
    -- Pässe
    home_total_passes INT DEFAULT NULL,
    away_total_passes INT DEFAULT NULL,
    home_passes_accurate INT DEFAULT NULL,
    away_passes_accurate INT DEFAULT NULL,
    home_passes_pct FLOAT DEFAULT NULL,
    away_passes_pct FLOAT DEFAULT NULL,
    -- Disziplin
    home_fouls INT DEFAULT NULL,
    away_fouls INT DEFAULT NULL,
    home_yellow_cards INT DEFAULT NULL,
    away_yellow_cards INT DEFAULT NULL,
    home_red_cards INT DEFAULT NULL,
    away_red_cards INT DEFAULT NULL,
    -- Weitere
    home_corners INT DEFAULT NULL,
    away_corners INT DEFAULT NULL,
    home_offsides INT DEFAULT NULL,
    away_offsides INT DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tournament_standings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    league_id INT,
    season INT,
    team_name VARCHAR(100),
    team_id INT,
    group_name VARCHAR(100),
    standing_rank INT,
    points INT,
    played INT,
    won INT,
    drawn INT,
    lost INT,
    goals_for INT,
    goals_against INT,
    goal_diff INT,
    form VARCHAR(10),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_team_season (league_id, season, team_id)
);

CREATE TABLE IF NOT EXISTS api_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fixture_id INT UNIQUE,

    -- API-Football Prediction (Poisson)
    predicted_winner VARCHAR(100),
    home_win_pct FLOAT DEFAULT NULL,
    draw_pct FLOAT DEFAULT NULL,
    away_win_pct FLOAT DEFAULT NULL,
    advice TEXT DEFAULT NULL,

    -- Buchmacher Konsens-Quoten (Durchschnitt Whitelist-BMs, für Anzeige)
    home_odds FLOAT DEFAULT NULL,
    draw_odds FLOAT DEFAULT NULL,
    away_odds FLOAT DEFAULT NULL,

    -- Eröffnungsquoten (werden nie überschrieben → Quotenbewegung)
    home_odds_open DECIMAL(6,3) DEFAULT NULL,
    draw_odds_open DECIMAL(6,3) DEFAULT NULL,
    away_odds_open DECIMAL(6,3) DEFAULT NULL,

    -- Implizite Wahrscheinlichkeiten (margin-bereinigt, für Agent)
    home_win_implied FLOAT DEFAULT NULL,
    draw_implied FLOAT DEFAULT NULL,
    away_win_implied FLOAT DEFAULT NULL,

    -- Pinnacle als Sharp Reference (~2% Margin, fairste klassische Quote)
    home_odds_pinnacle FLOAT DEFAULT NULL,
    draw_odds_pinnacle FLOAT DEFAULT NULL,
    away_odds_pinnacle FLOAT DEFAULT NULL,

    -- Betfair als Exchange Reference (kein Margin, fairste Quote überhaupt)
    home_odds_betfair FLOAT DEFAULT NULL,
    draw_odds_betfair FLOAT DEFAULT NULL,
    away_odds_betfair FLOAT DEFAULT NULL,

    -- Margin-Statistiken (Unsicherheitsindikator des Marktes)
    margin_avg FLOAT DEFAULT NULL,
    margin_min FLOAT DEFAULT NULL,
    margin_max FLOAT DEFAULT NULL,

    -- Qualitätsmasse
    odds_bookmaker_count INT DEFAULT NULL,
    market_confidence VARCHAR(10) DEFAULT NULL,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fixture_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fixture_id INT,
    minute INT,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INT DEFAULT NULL,
    away_score INT DEFAULT NULL,
    home_possession FLOAT DEFAULT NULL,
    away_possession FLOAT DEFAULT NULL,
    home_shots_on_target INT DEFAULT NULL,
    away_shots_on_target INT DEFAULT NULL,
    home_shots_off_target INT DEFAULT NULL,
    away_shots_off_target INT DEFAULT NULL,
    home_shots_total INT DEFAULT NULL,
    away_shots_total INT DEFAULT NULL,
    home_shots_insidebox INT DEFAULT NULL,
    away_shots_insidebox INT DEFAULT NULL,
    home_shots_outsidebox INT DEFAULT NULL,
    away_shots_outsidebox INT DEFAULT NULL,
    home_blocked_shots INT DEFAULT NULL,
    away_blocked_shots INT DEFAULT NULL,
    home_corners INT DEFAULT NULL,
    away_corners INT DEFAULT NULL,
    home_fouls INT DEFAULT NULL,
    away_fouls INT DEFAULT NULL,
    home_offsides INT DEFAULT NULL,
    away_offsides INT DEFAULT NULL,
    home_yellow_cards INT DEFAULT NULL,
    away_yellow_cards INT DEFAULT NULL,
    home_red_cards INT DEFAULT NULL,
    away_red_cards INT DEFAULT NULL,
    home_saves INT DEFAULT NULL,
    away_saves INT DEFAULT NULL,
    home_total_passes INT DEFAULT NULL,
    away_total_passes INT DEFAULT NULL,
    home_passes_accurate INT DEFAULT NULL,
    away_passes_accurate INT DEFAULT NULL,
    home_passes_pct FLOAT DEFAULT NULL,
    away_passes_pct FLOAT DEFAULT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fixture_id (fixture_id),
    INDEX idx_recorded_at (recorded_at)
);

"""

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

with engine.connect() as conn:
    for statement in SQL.strip().split(";"):
        if statement.strip():
            conn.execute(text(statement))
    conn.commit()
    print("Tabellen erstellt.")