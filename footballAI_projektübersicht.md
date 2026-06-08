# footballAI — Projektübersicht
*Stand: Mai 2026*

---

## 1. Projektziel

Ein KI-Agent der während der WM 2026 Spielausgänge vorhersagt und sich dynamisch an den Turnierverlauf anpasst. Der Agent interpretiert Daten aus einem Streamlit-Dashboard und gibt strukturierte Vorhersagen mit Begründungen.

---

## 2. Architektur: 5-Layer BI Framework

| Layer | Technologie | Beschreibung |
|---|---|---|
| Data Sources | API-Football + Kaggle CSV | Historische & Live-Daten |
| Data Platform | MySQL 8.0 | Speicherung & Transformation |
| Semantic Layer | Konsistente KPIs | Goals, Shots on Target, Form, Standings |
| AI Analytics | Gemini/Claude Agent | Interpretiert Daten, gibt Predictions |
| Decision Layer | Streamlit Dashboard | Visualisierung & User-Interaktion |

---

## 3. Tech Stack

```
Python 3.13
MySQL 8.0
SQLAlchemy 2.0.36
Streamlit
Anthropic API / Gemini API (Free Tier zum Testen)
API-Football (Pro Plan, 7500 Calls/Tag, $19/Monat)
```

---

## 4. Architektur-Entscheidungen

### Kein eigenes ML-Modell
- Der LLM-Agent (Gemini/Claude) übernimmt die Prediction-Logik
- Kein scikit-learn, kein Poisson-Training nötig
- Agent wird mit strukturierten DB-Daten als Kontext gefüttert

### LLM-agnostisch
- Per `.env` Variable zwischen Gemini und Claude wechselbar
- Gemini Free Tier zum Entwickeln & Testen
- Claude API für Produktion (ca. $5-10 für gesamte WM)

### Agent liest nur aus DB
- API-Football wird nur vom Pipeline-Script aufgerufen (nicht vom Agent)
- DB ist der lokale Cache → keine verschwendeten API-Calls
- Ausnahme: Live-Updates während laufender Spiele

### Feature-Strategie
- Historische Daten (Kaggle): H2H, Form, engineerte Features
- API-Football: reichhaltige Match-Statistiken für WM-Spiele
- Kein xG (nicht im Free Tier verfügbar → Semantic Layer Konsistenz)

---

## 5. Datenbankschema

### Bestehende Tabellen (unverändert)

```sql
matches        -- Alle Länderspiele 2010-2025 (Kaggle)
               -- Felder: date, home_team, away_team, 
               --         home_score, away_score, tournament, stage

team_stats     -- Aggregierte Teamstatistiken
               -- Felder: team_name, fifa_rank, win_rate,
               --         avg_goals, avg_conceded, form_last5, etc.

predictions    -- Agent-Outputs
api_log        -- API Call Tracking
```

### Neue Tabellen

```sql
wm_fixtures    -- WM + Turnier Spieldaten mit allen Statistiken
               -- Felder: fixture_id, league_id, season,
               --         home_team, away_team, match_date, stage, status,
               --         home_score, away_score,
               --         home_possession, away_possession,
               --         home_shots_on_target, away_shots_on_target,
               --         home_shots_off_target, away_shots_off_target,
               --         home_total_shots, away_total_shots,
               --         home_blocked_shots, away_blocked_shots,
               --         home_shots_insidebox, away_shots_insidebox,
               --         home_fouls, away_fouls,
               --         home_corners, away_corners,
               --         home_offsides, away_offsides,
               --         home_yellow_cards, away_yellow_cards,
               --         home_red_cards, away_red_cards,
               --         home_saves, away_saves,
               --         home_total_passes, away_total_passes,
               --         home_passes_accurate, away_passes_accurate,
               --         home_passes_pct, away_passes_pct

wm_standings   -- Gruppenstandings pro Turnier & Saison
               -- Felder: season, league_id, team_name, team_id,
               --         group_name, rank, points,
               --         played, won, drawn, lost,
               --         goals_for, goals_against, goal_diff, form

wm_predictions -- API-Football Vorhersagen + Buchmacher-Quoten
               -- Felder: fixture_id, predicted_winner,
               --         home_win_pct, draw_pct, away_win_pct, advice
               --         home_odds, draw_odds, away_odds  ← Buchmacher
               -- Hinweis: Odds nur für WM 2026 live verfügbar
               --          (7 Tage History, coverage abhängig von Plan)
```

---

## 6. API-Football

### Konfiguration
```
Base URL:   https://v3.football.api-sports.io
Plan:       Pro ($19/Monat)
Calls/Tag:  7500
Reset:      täglich 00:00 UTC
league_id WM: 1
```

### Genutzte Endpoints

| Endpoint | Zweck | Calls |
|---|---|---|
| `/fixtures` | Alle Spiele eines Turniers | 1x pro Turnier |
| `/fixtures/statistics` | Possession, Shots etc. | 1x pro Spiel |
| `/standings` | Gruppenstandings | 1x täglich |
| `/predictions` | API-eigene Vorhersagen | 1x pro Spiel |
| `/odds` | Buchmacher-Quoten vor Spiel | 1x pro Spiel (nur WM 2026 live) |

### Nicht genutzte Endpoints
- `/fixtures/headtohead` → haben wir in `matches`
- `/teams/statistics` → aus `wm_fixtures` berechenbar
- `/injuries` → lückenhafte WM-Coverage
- `/fixtures/events` → zu granular
- `/players` → zu viele Calls

---

## 7. Historische Daten (einmaliger Load)

| Turnier | League ID | Seasons | Spiele ca. | Stats |
|---|---|---|---|---|
| World Cup | 1 | 2018, 2022 | 128 | ✅ |
| UEFA Euro | 4 | 2020, 2024 | 102 | ✅ ab 2016 |
| Copa América | 9 | 2021, 2024 | 60 | ✅ ab 2015 |
| Africa Cup | 6 | 2021, 2023 | 104 | ✅ ab 2019 |
| AFC Asian Cup | 7 | 2019, 2023 | ~64 | ✅ ab 2019 |
| **Total** | | **10 Seasons** | **~458** | |

### Load-Strategie (Pro Plan: 7500 Calls/Tag)
```
Alles an 1 Tag ladbar (~470 Calls total)

WM 2018 + 2022              (~130 Calls)
EURO 2020 + 2024            (~103 Calls)
Copa 2021 + 2024            (~62 Calls)
Africa Cup 2021 + 2023      (~106 Calls)
AFC Asian Cup 2019 + 2023   (~66 Calls)
─────────────────────────────────────────
Total                        (~467 Calls)
```

---

## 8. Live-Betrieb während WM 2026

```
Täglich (Pipeline):
→ /fixtures: neue Spiele & Ergebnisse → wm_fixtures
→ /standings: aktuelle Tabellen → wm_standings
→ /fixtures/statistics: Stats gespielte Spiele → wm_fixtures
→ /predictions: Vorhersagen nächste Spiele → wm_predictions
→ /odds: Buchmacher-Quoten nächste Spiele → wm_predictions

Geschätzte Calls/Tag WM: 6-10 (weit unter 7500 Limit)
Pro Plan deckt historischen Load + WM 2026 Season ab
```

---

## 9. Agent-Architektur

### Tools (DB-Queries)
```python
get_upcoming_fixtures()    -- nächste WM-Spiele
get_team_form()            -- aktuelle Form eines Teams
get_h2h()                  -- Head-to-Head aus matches-Tabelle
get_standings()            -- aktuelle Gruppenstandings
get_fixture_stats()        -- Statistiken gespielte Spiele
get_api_prediction()       -- API-Football Vorhersage + Odds als Kontext
```

### LLM Wechsel via .env
```bash
LLM_PROVIDER=gemini        # zum Testen (kostenlos)
LLM_PROVIDER=claude        # für Produktion
```

---

## 10. Nächste Schritte

- [ ] API-Football Pro Plan abonnieren ($19/Monat)
- [ ] Schema updaten (wm_fixtures + wm_standings + wm_predictions)
- [ ] `pipeline/load_historical_wm.py` schreiben
- [ ] Historische Daten laden (alles an 1 Tag)
- [ ] Agent mit Tools aufbauen
- [ ] Streamlit Dashboard bauen
