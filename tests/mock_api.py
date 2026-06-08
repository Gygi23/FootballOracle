"""
tests/mock_api.py – Simulierte API-Responses für Tests

Simuliert realistische Live-Spieldaten für die ersten 3 WM 2026 Spiele:
- 1489369: Mexico vs South Africa
- 1538999: South Korea vs Czech Republic  
- 1539000: Canada vs Bosnia & Herzegovina

Verwendung in fetch_live.py:
    # data = api_get("fixtures", {"ids": ids_str})  ← auskommentieren
    from tests.mock_api import mock_live_response
    data = mock_live_response(fixture_ids)
"""

MOCK_FIXTURES = {
    1489369: {
        "fixture": {
            "id": 1489369,
            "status": {"short": "1H", "elapsed": 35}
        },
        "goals": {"home": 1, "away": 0},
        "teams": {
            "home": {"name": "Mexico"},
            "away": {"name": "South Africa"}
        },
        "statistics": [
            {"type": "Ball Possession",  "value": "58%"},
            {"type": "Shots on Goal",    "value": 4},
            {"type": "Shots off Goal",   "value": 3},
            {"type": "Total Shots",      "value": 7},
            {"type": "Blocked Shots",    "value": 1},
            {"type": "Shots insidebox",  "value": 5},
            {"type": "Corner Kicks",     "value": 4},
            {"type": "Fouls",            "value": 8},
            {"type": "Offsides",         "value": 2},
            {"type": "Yellow Cards",     "value": 1},
            {"type": "Red Cards",        "value": None},
            {"type": "Goalkeeper Saves", "value": 2},
            {"type": "Total passes",     "value": 312},
            {"type": "Passes accurate",  "value": 271},
            {"type": "Passes %",         "value": "87%"},
        ]
    },
    1538999: {
        "fixture": {
            "id": 1538999,
            "status": {"short": "1H", "elapsed": 22}
        },
        "goals": {"home": 0, "away": 0},
        "teams": {
            "home": {"name": "South Korea"},
            "away": {"name": "Czech Republic"}
        },
        "statistics": [
            {"type": "Ball Possession",  "value": "44%"},
            {"type": "Shots on Goal",    "value": 1},
            {"type": "Shots off Goal",   "value": 2},
            {"type": "Total Shots",      "value": 3},
            {"type": "Blocked Shots",    "value": 0},
            {"type": "Shots insidebox",  "value": 2},
            {"type": "Corner Kicks",     "value": 1},
            {"type": "Fouls",            "value": 6},
            {"type": "Offsides",         "value": 1},
            {"type": "Yellow Cards",     "value": 0},
            {"type": "Red Cards",        "value": None},
            {"type": "Goalkeeper Saves", "value": 1},
            {"type": "Total passes",     "value": 198},
            {"type": "Passes accurate",  "value": 164},
            {"type": "Passes %",         "value": "83%"},
        ]
    },
    1539000: {
        "fixture": {
            "id": 1539000,
            "status": {"short": "HT", "elapsed": 45}
        },
        "goals": {"home": 0, "away": 1},
        "teams": {
            "home": {"name": "Canada"},
            "away": {"name": "Bosnia & Herzegovina"}
        },
        "statistics": [
            {"type": "Ball Possession",  "value": "52%"},
            {"type": "Shots on Goal",    "value": 2},
            {"type": "Shots off Goal",   "value": 4},
            {"type": "Total Shots",      "value": 6},
            {"type": "Blocked Shots",    "value": 2},
            {"type": "Shots insidebox",  "value": 3},
            {"type": "Corner Kicks",     "value": 3},
            {"type": "Fouls",            "value": 10},
            {"type": "Offsides",         "value": 3},
            {"type": "Yellow Cards",     "value": 2},
            {"type": "Red Cards",        "value": None},
            {"type": "Goalkeeper Saves", "value": 1},
            {"type": "Total passes",     "value": 267},
            {"type": "Passes accurate",  "value": 228},
            {"type": "Passes %",         "value": "85%"},
        ]
    }
}

# Away-Team Statistiken (gespiegelt)
MOCK_FIXTURES_AWAY = {
    1489369: [
        {"type": "Ball Possession",  "value": "42%"},
        {"type": "Shots on Goal",    "value": 2},
        {"type": "Shots off Goal",   "value": 2},
        {"type": "Total Shots",      "value": 4},
        {"type": "Blocked Shots",    "value": 0},
        {"type": "Shots insidebox",  "value": 2},
        {"type": "Corner Kicks",     "value": 2},
        {"type": "Fouls",            "value": 11},
        {"type": "Offsides",         "value": 1},
        {"type": "Yellow Cards",     "value": 0},
        {"type": "Red Cards",        "value": None},
        {"type": "Goalkeeper Saves", "value": 3},
        {"type": "Total passes",     "value": 224},
        {"type": "Passes accurate",  "value": 185},
        {"type": "Passes %",         "value": "83%"},
    ],
    1538999: [
        {"type": "Ball Possession",  "value": "56%"},
        {"type": "Shots on Goal",    "value": 3},
        {"type": "Shots off Goal",   "value": 1},
        {"type": "Total Shots",      "value": 4},
        {"type": "Blocked Shots",    "value": 1},
        {"type": "Shots insidebox",  "value": 3},
        {"type": "Corner Kicks",     "value": 3},
        {"type": "Fouls",            "value": 5},
        {"type": "Offsides",         "value": 0},
        {"type": "Yellow Cards",     "value": 1},
        {"type": "Red Cards",        "value": None},
        {"type": "Goalkeeper Saves", "value": 1},
        {"type": "Total passes",     "value": 251},
        {"type": "Passes accurate",  "value": 219},
        {"type": "Passes %",         "value": "87%"},
    ],
    1539000: [
        {"type": "Ball Possession",  "value": "48%"},
        {"type": "Shots on Goal",    "value": 3},
        {"type": "Shots off Goal",   "value": 2},
        {"type": "Total Shots",      "value": 5},
        {"type": "Blocked Shots",    "value": 1},
        {"type": "Shots insidebox",  "value": 4},
        {"type": "Corner Kicks",     "value": 2},
        {"type": "Fouls",            "value": 7},
        {"type": "Offsides",         "value": 1},
        {"type": "Yellow Cards",     "value": 0},
        {"type": "Red Cards",        "value": None},
        {"type": "Goalkeeper Saves", "value": 2},
        {"type": "Total passes",     "value": 245},
        {"type": "Passes accurate",  "value": 204},
        {"type": "Passes %",         "value": "83%"},
    ]
}


def mock_live_response(fixture_ids: list[int]) -> dict:
    """
    Simuliert eine Batch-API-Antwort für mehrere Fixtures.
    Format identisch mit /fixtures?ids=ID1-ID2-ID3
    """
    fixtures = []
    for fid in fixture_ids:
        if fid not in MOCK_FIXTURES:
            continue
        fx = MOCK_FIXTURES[fid].copy()
        fx["statistics"] = [
            {"team": fx["teams"]["home"], "statistics": fx["statistics"]},
            {"team": fx["teams"]["away"], "statistics": MOCK_FIXTURES_AWAY[fid]},
        ]
        fixtures.append(fx)

    return {"response": fixtures}


def mock_live_fixture_ids() -> list[int]:
    """Gibt die IDs der simulierten Live-Spiele zurück."""
    return list(MOCK_FIXTURES.keys())


def advance_minute(delta: int = 5):
    """Simuliert Spielfortschritt — erhöht elapsed um delta Minuten."""
    for fid, fx in MOCK_FIXTURES.items():
        current = fx["fixture"]["status"]["elapsed"]
        new_minute = current + delta

        if new_minute >= 90:
            fx["fixture"]["status"]["short"] = "FT"
            fx["fixture"]["status"]["elapsed"] = 90
        elif new_minute >= 45 and fx["fixture"]["status"]["short"] == "1H":
            fx["fixture"]["status"]["short"] = "HT"
            fx["fixture"]["status"]["elapsed"] = 45
        elif fx["fixture"]["status"]["short"] == "HT":
            fx["fixture"]["status"]["short"] = "2H"
            fx["fixture"]["status"]["elapsed"] = 46
        else:
            fx["fixture"]["status"]["elapsed"] = new_minute