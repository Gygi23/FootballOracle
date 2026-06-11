from __future__ import annotations

import json
import math
import os
from typing import Any, Callable

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


# -----------------------------------------------------------------------------
# Datenbankverbindung und gemeinsame Helper
# -----------------------------------------------------------------------------


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            host     = os.getenv("DB_HOST", "localhost")
            port     = os.getenv("DB_PORT", "3306")
            user     = os.getenv("DB_USER", "root")
            password = os.getenv("DB_PASSWORD", "")
            name     = os.getenv("DB_NAME", "footballAI")
            db_url   = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        _engine = create_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _engine


DEFAULT_ERROR_RESULT = {"result": [], "count": 0}

# Namens-Normalisierung: API-Football → historische Daten (matches / team_stats)
_TEAM_NAME_MAP: dict[str, str] = {
    "Bosnia & Herzegovina":  "Bosnia and Herzegovina",
    "Cape Verde Islands":    "Cape Verde",
    "Congo DR":              "DR Congo",
    "Türkiye":               "Turkey",
    "USA":                   "United States",
}


def normalize_team_name(name: str) -> str:
    """Mappt API-Football-Teamnamen auf die Schreibweise in den historischen Daten."""
    return _TEAM_NAME_MAP.get(name, name)


def json_response(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def safe_limit(limit: int | str | None, default: int = 10, maximum: int = 50) -> int:
    try:
        value = int(limit) if limit is not None else default
    except (TypeError, ValueError):
        value = default
    if value < 1:
        return default
    return min(value, maximum)


def query_to_json(sql: str, params: dict = None) -> str:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)

        if df.empty:
            return json.dumps({"result": [], "count": 0, "message": "Keine Daten gefunden."})

        df = df.where(pd.notna(df), None)
        records = df.to_dict(orient="records")

        clean = [
            {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
            for row in records
        ]

        return json.dumps({"result": clean, "count": len(clean)}, default=str)

    except Exception as e:
        return json.dumps({"error": str(e), "result": []})


# -----------------------------------------------------------------------------
# Tool 1: get_team_matches
# -----------------------------------------------------------------------------


def get_team_matches(team_name: str, limit: int = 10) -> str:
    team_name = normalize_team_name(team_name)
    limit = min(int(limit), 50)

    sql = """
    SELECT
    date,
    home_team,
    away_team,
    home_score,
    away_score,
    tournament,
    stage,
    shootout_winner
    FROM matches
    WHERE (home_team = :team OR away_team = :team)
    AND date <= CURDATE()
    ORDER BY date DESC
    LIMIT :limit
    """

    return query_to_json(sql, {"team": team_name, "limit": limit})


TOOL_GET_TEAM_MATCHES = {
    "name": "get_team_matches",
    "description": (
        "Holt historische Spiele einer Nationalmannschaft aus der matches-Tabelle. "
        "Diese Daten stammen aus einem Kaggle-/manuellen historischen Datensatz und dienen "
        "als Kontext fuer Formanalyse, Ergebnis-Trends, Head-to-Head und langfristige Teamhistorie. "
        "Nicht als primaere Quelle fuer aktuelle WM-2026-Fixtures oder Live-Resultate verwenden."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team_name": {
                "type": "string",
                "description": "Name der Nationalmannschaft auf Englisch, z.B. Germany, Brazil, Switzerland.",
            },
            "limit": {
                "type": "integer",
                "description": "Anzahl der letzten Spiele. Standard 10, Maximum 50.",
                "default": 10,
            },
        },
        "required": ["team_name"],
    },
}


# -----------------------------------------------------------------------------
# Tool 2: get_team_stats
# -----------------------------------------------------------------------------


def get_team_stats(team_name: str) -> str:
    team_name = normalize_team_name(team_name)
    sql = """
    SELECT
        team_name,
        fifa_rank,
        elo_rating,
        elo_rating_pre_wm,
        win_rate,
        avg_goals,
        avg_conceded,
        goal_difference,
        form_last5,
        clean_sheet_rate,
        shootout_wins,
        shootout_total,
        shootout_win_rate,
        updated_at
    FROM team_stats
    WHERE team_name = :team
    """

    return query_to_json(sql, {"team": team_name})


TOOL_GET_TEAM_STATS = {
    "name": "get_team_stats",
    "description": (
        "Holt manuell berechnete historische Team-Statistiken aus team_stats. "
        "Enthaelt u.a. ELO-Rating (berechnet aus 15.000+ Spielen, hoeher = staerker), "
        "FIFA-Rang, Siegesrate, durchschnittliche Tore, Gegentore, "
        "Tordifferenz, letzte Form, Clean-Sheet-Rate und Penalty-Statistik."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team_name": {
                "type": "string",
                "description": "Name der Nationalmannschaft auf Englisch.",
            }
        },
        "required": ["team_name"],
    },
}


# -----------------------------------------------------------------------------
# Tool 3: calculate_team_record
# -----------------------------------------------------------------------------


def calculate_team_record(team_name: str, stage: str | None = None) -> str:
    team_name = normalize_team_name(team_name)
    params: dict[str, Any] = {"team": team_name}
    stage_filter = ""

    if stage:
        stage_filter = "AND stage = :stage"
        params["stage"] = stage

    sql = f"""
    SELECT
        :team AS team,
        COUNT(*) AS total_matches,
        SUM(CASE
            WHEN home_team = :team AND home_score > away_score THEN 1
            WHEN away_team = :team AND away_score > home_score THEN 1
            ELSE 0
        END) AS wins,
        SUM(CASE
            WHEN home_score = away_score THEN 1
            ELSE 0
        END) AS draws,
        SUM(CASE
            WHEN home_team = :team AND home_score < away_score THEN 1
            WHEN away_team = :team AND away_score < home_score THEN 1
            ELSE 0
        END) AS losses,
        SUM(CASE
            WHEN home_team = :team THEN home_score
            ELSE away_score
        END) AS goals_scored,
        SUM(CASE
            WHEN home_team = :team THEN away_score
            ELSE home_score
        END) AS goals_conceded,
        SUM(CASE
            WHEN home_team = :team THEN home_score - away_score
            ELSE away_score - home_score
        END) AS goal_difference
    FROM matches
    WHERE (home_team = :team OR away_team = :team)
      {stage_filter}
    """

    return query_to_json(sql, params)


TOOL_CALCULATE_TEAM_RECORD = {
    "name": "calculate_team_record",
    "description": (
        "Berechnet eine historische Bilanz einer Nationalmannschaft direkt aus der matches-Tabelle. "
        "Liefert Spiele, Siege, Unentschieden, Niederlagen, Tore, Gegentore und Tordifferenz. "
        "Optional nach stage filterbar, z.B. WC, QUAL, FRIENDLY, CONTINENTAL oder OTHER."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team_name": {
                "type": "string",
                "description": "Name der Nationalmannschaft auf Englisch.",
            },
            "stage": {
                "type": "string",
                "description": "Optionaler Stage-Filter, z.B. WC, QUAL, FRIENDLY, CONTINENTAL, OTHER.",
            },
        },
        "required": ["team_name"],
    },
}


# -----------------------------------------------------------------------------
# Tool 4: get_head_to_head
# -----------------------------------------------------------------------------


def get_head_to_head(team1: str, team2: str, limit: int = 10) -> str:
    team1 = normalize_team_name(team1)
    team2 = normalize_team_name(team2)
    limit = min(int(limit), 50)

    sql = """
    SELECT
        date,
        home_team,
        away_team,
        home_score,
        away_score,
        tournament,
        stage,
        shootout_winner
    FROM matches
    WHERE (home_team = :team1 AND away_team = :team2)
       OR (home_team = :team2 AND away_team = :team1)
    ORDER BY date DESC
    LIMIT :limit
    """

    return query_to_json(sql, {"team1": team1, "team2": team2, "limit": limit})


TOOL_GET_HEAD_TO_HEAD = {
    "name": "get_head_to_head",
    "description": (
        "Holt historische Direktvergleiche zweier Nationalmannschaften aus matches. "
        "Nuetzlich fuer Kontext bei Prognosen, aber nicht als aktuelle Turnierquelle verwenden."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team1": {
                "type": "string",
                "description": "Name der ersten Nationalmannschaft auf Englisch.",
            },
            "team2": {
                "type": "string",
                "description": "Name der zweiten Nationalmannschaft auf Englisch.",
            },
            "limit": {
                "type": "integer",
                "description": "Anzahl Begegnungen. Standard 10, Maximum 50.",
                "default": 10,
            },
        },
        "required": ["team1", "team2"],
    },
}


# -----------------------------------------------------------------------------
# Tool 5: get_historical_group_record
# -----------------------------------------------------------------------------


def get_historical_group_record(teams: list[str], stage: str = "WC") -> str:
    if not teams:
        return json_response({**DEFAULT_ERROR_RESULT, "error": "Keine Mannschaften angegeben."})

    params: dict[str, Any] = {"stage": stage}
    placeholders = []
    for index, team in enumerate(teams):
        key = f"team{index}"
        placeholders.append(f":{key}")
        params[key] = team

    in_clause = ", ".join(placeholders)

    sql = f"""
    SELECT
        team,
        COUNT(*) AS matches,
        SUM(wins) AS wins,
        SUM(draws) AS draws,
        SUM(losses) AS losses,
        SUM(goals_scored) AS goals_scored,
        SUM(goals_conceded) AS goals_conceded,
        SUM(goals_scored) - SUM(goals_conceded) AS goal_difference,
        SUM(wins) * 3 + SUM(draws) AS points
    FROM (
        SELECT
            home_team AS team,
            CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS wins,
            CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draws,
            CASE WHEN home_score < away_score THEN 1 ELSE 0 END AS losses,
            home_score AS goals_scored,
            away_score AS goals_conceded
        FROM matches
        WHERE stage = :stage AND home_team IN ({in_clause})

        UNION ALL

        SELECT
            away_team AS team,
            CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS wins,
            CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draws,
            CASE WHEN away_score < home_score THEN 1 ELSE 0 END AS losses,
            away_score AS goals_scored,
            home_score AS goals_conceded
        FROM matches
        WHERE stage = :stage AND away_team IN ({in_clause})
    ) AS combined
    GROUP BY team
    ORDER BY points DESC, goal_difference DESC, goals_scored DESC
    """

    return query_to_json(sql, params)


TOOL_GET_HISTORICAL_GROUP_RECORD = {
    "name": "get_historical_group_record",
    "description": (
        "Berechnet eine historische Vergleichstabelle fuer eine Liste von Teams aus matches. "
        "Standardmaessig fuer stage = WC. Dies ist KEINE aktuelle Gruppenrangliste, sondern historischer Kontext."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "teams": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Liste von Nationalmannschaften auf Englisch.",
            },
            "stage": {
                "type": "string",
                "description": "Historischer Stage-Filter. Standard: WC.",
                "default": "WC",
            },
        },
        "required": ["teams"],
    },
}


# -----------------------------------------------------------------------------
# Tool 6: get_tournament_fixtures
# -----------------------------------------------------------------------------


def get_tournament_fixtures(
    league_id: int | None = None,
    season: int | None = None,
    team_name: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> str:
    limit = min(int(limit), 100)

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit}

    if league_id is not None:
        conditions.append("league_id = :league_id")
        params["league_id"] = league_id
    if season is not None:
        conditions.append("season = :season")
        params["season"] = season
    if team_name:
        conditions.append("(home_team = :team OR away_team = :team)")
        params["team"] = team_name
    if stage:
        conditions.append("stage = :stage")
        params["stage"] = stage
    if status:
        if "-" in status:
            # Mehrere Status: "1H-HT-2H" → IN ('1H', 'HT', '2H')
            status_list = status.split("-")
            placeholders = ", ".join([f":status{i}" for i in range(len(status_list))])
            conditions.append(f"status IN ({placeholders})")
            for i, s in enumerate(status_list):
                params[f"status{i}"] = s
        else:
            # Einzelner Status
            conditions.append("status = :status")
            params["status"] = status

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
    SELECT
        fixture_id, league_id, season, home_team, away_team, match_date,
        stage, status, home_score, away_score,
        home_possession, away_possession,
        home_shots_on_target, away_shots_on_target,
        home_shots_off_target, away_shots_off_target,
        home_total_shots, away_total_shots,
        home_blocked_shots, away_blocked_shots,
        home_shots_insidebox, away_shots_insidebox,
        home_saves, away_saves,
        home_total_passes, away_total_passes,
        home_passes_accurate, away_passes_accurate,
        home_passes_pct, away_passes_pct,
        home_fouls, away_fouls,
        home_yellow_cards, away_yellow_cards,
        home_red_cards, away_red_cards,
        home_corners, away_corners,
        home_offsides, away_offsides,
        updated_at
    FROM tournament_fixtures
    {where_clause}
    ORDER BY match_date ASC
    LIMIT :limit
    """

    return query_to_json(sql, params)


TOOL_GET_TOURNAMENT_FIXTURES = {
    "name": "get_tournament_fixtures",
    "description": (
        "Holt Turnier-Fixtures, Resultate, Spielstatus und Match-Statistiken aus tournament_fixtures. "
        "Bevorzugte Quelle fuer konkrete WM-2026-Spiele, Resultate und Matchmetriken."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "league_id": {"type": "integer", "description": "League-ID des Turniers."},
            "season": {"type": "integer", "description": "Saison/Jahr, z.B. 2026."},
            "team_name": {"type": "string", "description": "Teamname auf Englisch."},
            "stage": {"type": "string", "description": "Optionaler Stage-Filter."},
            "status": {"type": "string", "description": "Fixture-Status, z.B. NS, FT, AET, PEN."},
            "limit": {"type": "integer", "description": "Anzahl Fixtures. Standard 20, Maximum 100.", "default": 20},
        },
        "required": [],
    },
}


# -----------------------------------------------------------------------------
# Tool 7: get_tournament_standings
# -----------------------------------------------------------------------------


def get_tournament_standings(
    league_id: int | None = None,
    season: int | None = None,
    group_name: str | None = None,
    team_name: str | None = None,
    limit: int = 100,
) -> str:
    limit = min(int(limit), 500)

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit}

    if league_id is not None:
        conditions.append("league_id = :league_id")
        params["league_id"] = league_id
    if season is not None:
        conditions.append("season = :season")
        params["season"] = season
    if group_name:
        conditions.append("group_name = :group_name")
        params["group_name"] = group_name
    if team_name:
        conditions.append("team_name = :team_name")
        params["team_name"] = team_name

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
    SELECT
        league_id, season, group_name, standing_rank, team_name, team_id,
        points, played, won, drawn, lost,
        goals_for, goals_against, goal_diff, form, updated_at
    FROM tournament_standings
    {where_clause}
    ORDER BY season DESC, league_id ASC, group_name ASC, standing_rank ASC
    LIMIT :limit
    """

    return query_to_json(sql, params)


TOOL_GET_TOURNAMENT_STANDINGS = {
    "name": "get_tournament_standings",
    "description": (
        "Holt Turnierstaende aus tournament_standings. "
        "Massgebend fuer Tabellen, Punkte, Gruppenranglisten und Qualifikationslage."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "league_id": {"type": "integer", "description": "League-ID des Turniers."},
            "season": {"type": "integer", "description": "Saison/Jahr, z.B. 2026."},
            "group_name": {"type": "string", "description": "Optionaler Gruppenname."},
            "team_name": {"type": "string", "description": "Optionaler Teamname auf Englisch."},
            "limit": {"type": "integer", "description": "Maximale Anzahl Zeilen. Standard 100, Maximum 500.", "default": 100},
        },
        "required": [],
    },
}


# -----------------------------------------------------------------------------
# Tool 8: get_agent_predictions
# -----------------------------------------------------------------------------


def get_agent_predictions(
    team1: str | None = None,
    team2: str | None = None,
    limit: int = 5,
) -> str:
    limit = min(int(limit), 50)

    params: dict[str, Any] = {"limit": limit}
    conditions: list[str] = []

    if team1 and team2:
        conditions.append(
            "((home_team = :team1 AND away_team = :team2) OR (home_team = :team2 AND away_team = :team1))"
        )
        params["team1"] = team1
        params["team2"] = team2
    elif team1:
        conditions.append("(home_team = :team OR away_team = :team)")
        params["team"] = team1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
    SELECT
        home_team, away_team,
        home_win_prob, draw_prob, away_win_prob,
        predicted_winner, confidence, created_at
    FROM agent_predictions
    {where_clause}
    ORDER BY created_at DESC
    LIMIT :limit
    """

    return query_to_json(sql, params)


TOOL_GET_AGENT_PREDICTIONS = {
    "name": "get_agent_predictions",
    "description": (
        "Holt gespeicherte Vorhersagen des eigenen Agenten aus agent_predictions. "
        "Enthaelt Home-/Draw-/Away-Wahrscheinlichkeiten, vorhergesagten Sieger und Confidence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team1": {"type": "string", "description": "Optionales erstes Team."},
            "team2": {"type": "string", "description": "Optionales zweites Team fuer ein spezifisches Duell."},
            "limit": {"type": "integer", "description": "Anzahl Vorhersagen. Standard 5, Maximum 50.", "default": 5},
        },
        "required": [],
    },
}


# -----------------------------------------------------------------------------
# Tool 9: get_api_predictions
# -----------------------------------------------------------------------------


def get_api_predictions(fixture_id: int | None = None, limit: int = 10) -> str:
    limit = min(int(limit), 200)  # WM 2026 hat max. 104 Spiele

    cols = """
            fixture_id, predicted_winner,
            home_win_pct, draw_pct, away_win_pct,
            advice, home_odds, draw_odds, away_odds,
            home_odds_open, draw_odds_open, away_odds_open,
            home_win_implied, draw_implied, away_win_implied,
            home_odds_pinnacle, draw_odds_pinnacle, away_odds_pinnacle,
            home_odds_betfair, draw_odds_betfair, away_odds_betfair,
            margin_avg, margin_min, margin_max,
            odds_bookmaker_count, market_confidence,
            updated_at"""
    if fixture_id is not None:
        sql = f"SELECT {cols} FROM api_predictions WHERE fixture_id = :fixture_id"
        params = {"fixture_id": fixture_id}
    else:
        sql = f"SELECT {cols} FROM api_predictions ORDER BY updated_at DESC LIMIT :limit"
        params = {"limit": limit}

    return query_to_json(sql, params)


TOOL_GET_API_PREDICTIONS = {
    "name": "get_api_predictions",
    "description": (
        "Holt API-basierte Prognosen und Buchmacher-Odds aus api_predictions. "
        "Optional nach fixture_id filterbar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fixture_id": {"type": "integer", "description": "Fixture-ID."},
            "limit": {"type": "integer", "description": "Anzahl Eintraege. Standard 10, Maximum 50.", "default": 10},
        },
        "required": [],
    },
}


# -----------------------------------------------------------------------------
# Tool 10: get_fixture_with_prediction
# -----------------------------------------------------------------------------


def get_fixture_with_prediction(fixture_id: int) -> str:
    sql = """
    SELECT
        f.fixture_id, f.league_id, f.season,
        f.home_team, f.away_team, f.match_date, f.stage, f.status,
        f.home_score, f.away_score,
        f.home_possession, f.away_possession,
        f.home_total_shots, f.away_total_shots,
        f.home_shots_on_target, f.away_shots_on_target,
        f.home_corners, f.away_corners,
        f.home_yellow_cards, f.away_yellow_cards,
        f.home_red_cards, f.away_red_cards,
        -- Poisson-Prognose
        p.predicted_winner,
        p.home_win_pct, p.draw_pct, p.away_win_pct,
        p.advice,
        -- Buchmacher-Konsens (rohe Quoten)
        p.home_odds, p.draw_odds, p.away_odds,
        -- Implizite Wahrscheinlichkeiten (margin-bereinigt — primäres Signal)
        p.home_win_implied, p.draw_implied, p.away_win_implied,
        -- Sharp References
        p.home_odds_pinnacle, p.draw_odds_pinnacle, p.away_odds_pinnacle,
        p.home_odds_betfair,  p.draw_odds_betfair,  p.away_odds_betfair,
        -- Eröffnungsquoten (Vergleich → Bewegung erkennbar)
        p.home_odds_open, p.draw_odds_open, p.away_odds_open,
        -- Markt-Qualität
        p.margin_avg, p.margin_min, p.margin_max,
        p.odds_bookmaker_count, p.market_confidence,
        GREATEST(f.updated_at, COALESCE(p.updated_at, f.updated_at)) AS updated_at
    FROM tournament_fixtures f
    LEFT JOIN api_predictions p ON p.fixture_id = f.fixture_id
    WHERE f.fixture_id = :fixture_id
    """

    return query_to_json(sql, {"fixture_id": fixture_id})


TOOL_GET_FIXTURE_WITH_PREDICTION = {
    "name": "get_fixture_with_prediction",
    "description": (
        "Holt ein konkretes Fixture zusammen mit vollstaendiger Odds-Analyse und API-Prognose. "
        "Liefert: Fixture-Status, Poisson-Prognose, Konsens-Odds, implizite Wahrscheinlichkeiten, "
        "Pinnacle- und Betfair-Quoten, Margin, Bookmaker-Anzahl und market_confidence. "
        "Beste Wahl fuer Prognose-Fragen zu einem konkreten Spiel mit bekannter fixture_id."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fixture_id": {"type": "integer", "description": "Fixture-ID des Spiels."}
        },
        "required": ["fixture_id"],
    },
}


# -----------------------------------------------------------------------------
# Tool 11: get_tournament_team_summary
# -----------------------------------------------------------------------------


def get_tournament_team_summary(team_name: str, season: int = 2026) -> str:
    """Aggregierte Turnierstatistik eines Teams über alle abgeschlossenen Spiele."""
    sql = """
    SELECT
        :team                                                        AS team_name,
        COUNT(*)                                                     AS games_played,
        SUM(CASE
            WHEN home_team = :team AND home_score > away_score THEN 1
            WHEN away_team = :team AND away_score > home_score THEN 1
            ELSE 0 END)                                              AS wins,
        SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END)    AS draws,
        SUM(CASE
            WHEN home_team = :team AND home_score < away_score THEN 1
            WHEN away_team = :team AND away_score < home_score THEN 1
            ELSE 0 END)                                              AS losses,
        SUM(CASE WHEN home_team = :team THEN home_score
                 ELSE away_score END)                                AS goals_scored,
        SUM(CASE WHEN home_team = :team THEN away_score
                 ELSE home_score END)                                AS goals_conceded,
        -- Angriff
        SUM(CASE WHEN home_team = :team THEN home_shots_on_target
                 ELSE away_shots_on_target END)                     AS shots_on_target,
        SUM(CASE WHEN home_team = :team THEN home_total_shots
                 ELSE away_total_shots END)                         AS total_shots,
        SUM(CASE WHEN home_team = :team THEN home_shots_insidebox
                 ELSE away_shots_insidebox END)                     AS shots_insidebox,
        -- Ballbesitz
        ROUND(AVG(CASE WHEN home_team = :team THEN home_possession
                       ELSE away_possession END), 1)                AS avg_possession,
        -- Pässe
        SUM(CASE WHEN home_team = :team THEN home_total_passes
                 ELSE away_total_passes END)                        AS total_passes,
        ROUND(AVG(CASE WHEN home_team = :team THEN home_passes_pct
                       ELSE away_passes_pct END), 1)                AS avg_pass_accuracy,
        -- Defensiv
        SUM(CASE WHEN home_team = :team THEN home_saves
                 ELSE away_saves END)                               AS goalkeeper_saves,
        SUM(CASE WHEN home_team = :team THEN home_fouls
                 ELSE away_fouls END)                               AS fouls,
        SUM(CASE WHEN home_team = :team THEN home_yellow_cards
                 ELSE away_yellow_cards END)                        AS yellow_cards,
        SUM(CASE WHEN home_team = :team THEN home_red_cards
                 ELSE away_red_cards END)                           AS red_cards,
        SUM(CASE WHEN home_team = :team THEN home_corners
                 ELSE away_corners END)                             AS corners,
        SUM(CASE WHEN home_team = :team THEN home_offsides
                 ELSE away_offsides END)                            AS offsides
    FROM tournament_fixtures
    WHERE season = :season
      AND league_id = 1
      AND status IN ('FT', 'AET', 'PEN')
      AND (home_team = :team OR away_team = :team)
    """
    return query_to_json(sql, {"team": team_name, "season": season})


TOOL_GET_TOURNAMENT_TEAM_SUMMARY = {
    "name": "get_tournament_team_summary",
    "description": (
        "Aggregierte WM-Turnierstatistik eines Teams: Spiele, Tore, Schüsse, "
        "Ballbesitz, Pässe, Paraden, Karten über alle abgeschlossenen Turnierspiele. "
        "Verwenden wenn nach Turnierform oder Spielstärke im aktuellen Turnier gefragt wird."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "team_name": {"type": "string", "description": "Teamname auf Englisch."},
            "season": {"type": "integer", "description": "Saison/Jahr. Standard 2026.", "default": 2026},
        },
        "required": ["team_name"],
    },
}


# -----------------------------------------------------------------------------
# Tool 12: get_odds_history
# -----------------------------------------------------------------------------


def get_odds_history(fixture_id: int, limit: int = 20) -> str:
    """Quoten-Verlaufshistorie für ein Fixture aus odds_history."""
    limit = min(int(limit), 100)
    sql = """
    SELECT
        oh.recorded_at,
        oh.home_odds,
        oh.draw_odds,
        oh.away_odds,
        tf.home_team,
        tf.away_team
    FROM odds_history oh
    JOIN tournament_fixtures tf ON tf.fixture_id = oh.fixture_id
    WHERE oh.fixture_id = :fixture_id
    ORDER BY oh.recorded_at ASC
    LIMIT :limit
    """
    return query_to_json(sql, {"fixture_id": fixture_id, "limit": limit})


TOOL_GET_ODDS_HISTORY = {
    "name": "get_odds_history",
    "description": (
        "Holt den zeitlichen Quoten-Verlauf (Snapshots) für ein konkretes Fixture aus odds_history. "
        "Zeigt wie sich home_odds, draw_odds und away_odds über die Zeit entwickelt haben. "
        "Verwenden wenn nach Quotenbewegungen, Markttrend oder Sharp-Money-Signalen gefragt wird. "
        "Sinkende Quote = Geld fliesst rein (Favorit wird stärker). "
        "Steigende Quote = Markt verliert Vertrauen. "
        "Benötigt fixture_id — zuerst get_tournament_fixtures aufrufen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fixture_id": {
                "type": "integer",
                "description": "Fixture-ID des Spiels.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximale Anzahl Snapshots. Standard 20, Maximum 100.",
                "default": 20,
            },
        },
        "required": ["fixture_id"],
    },
}


# -----------------------------------------------------------------------------
# Tool 13: get_current_time
# -----------------------------------------------------------------------------


def get_current_time() -> str:
    """Gibt aktuelle UTC-Zeit und lokale Zeit (konfigurierte Zeitzone) zurück."""
    import os
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    now_utc = datetime.now(timezone.utc)
    tz_name = os.getenv("TIMEZONE", "Europe/Zurich")

    try:
        local_tz = ZoneInfo(tz_name)
        now_local = now_utc.astimezone(local_tz)
        offset_h = int(now_local.utcoffset().total_seconds() // 3600)
        offset_str = f"UTC+{offset_h}" if offset_h >= 0 else f"UTC{offset_h}"
        return json_response({
            "utc_now":   now_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "local_now": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone":  tz_name,
            "utc_offset": offset_str,
            "note": (
                "match_date-Werte in der DB sind UTC. "
                "Zeiten in Antworten immer als lokale Zeit (local_now) angeben, "
                "z.B. '23:00 Uhr' statt '21:00 UTC'."
            ),
        })
    except ZoneInfoNotFoundError:
        return json_response({
            "utc_now":  now_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "UTC",
            "note": f"Zeitzone '{tz_name}' nicht gefunden, UTC wird verwendet.",
        })


TOOL_GET_CURRENT_TIME = {
    "name": "get_current_time",
    "description": (
        "Gibt die aktuelle Uhrzeit in UTC zurück. "
        "Verwenden wenn gefragt wird wie viele Minuten/Stunden bis zum nächsten Spiel, "
        "ob ein Spiel gerade läuft, oder wann heute noch Spiele stattfinden."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


ALL_TOOLS = [
    TOOL_GET_TEAM_MATCHES,
    TOOL_GET_TEAM_STATS,
    TOOL_CALCULATE_TEAM_RECORD,
    TOOL_GET_HEAD_TO_HEAD,
    TOOL_GET_HISTORICAL_GROUP_RECORD,
    TOOL_GET_TOURNAMENT_FIXTURES,
    TOOL_GET_TOURNAMENT_STANDINGS,
    TOOL_GET_AGENT_PREDICTIONS,
    TOOL_GET_API_PREDICTIONS,
    TOOL_GET_FIXTURE_WITH_PREDICTION,
    TOOL_GET_TOURNAMENT_TEAM_SUMMARY,
    TOOL_GET_ODDS_HISTORY,
    TOOL_GET_CURRENT_TIME,
]

TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
    "get_team_matches": get_team_matches,
    "get_team_stats": get_team_stats,
    "calculate_team_record": calculate_team_record,
    "get_head_to_head": get_head_to_head,
    "get_historical_group_record": get_historical_group_record,
    "get_tournament_fixtures": get_tournament_fixtures,
    "get_tournament_standings": get_tournament_standings,
    "get_agent_predictions": get_agent_predictions,
    "get_api_predictions": get_api_predictions,
    "get_fixture_with_prediction": get_fixture_with_prediction,
    "get_tournament_team_summary": get_tournament_team_summary,
    "get_odds_history": get_odds_history,
    "get_current_time": get_current_time,
}


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return json_response({
            **DEFAULT_ERROR_RESULT,
            "error": f"Unbekanntes Tool: {tool_name}",
            "available_tools": sorted(TOOL_FUNCTIONS.keys()),
        })
    try:
        return func(**tool_input)
    except TypeError as exc:
        return json_response({
            **DEFAULT_ERROR_RESULT,
            "error": f"Ungueltige Tool-Parameter fuer {tool_name}: {exc}",
        })