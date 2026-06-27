# FootballOracle — WM 2026 Analyse & Prognose

Ein KI-gestütztes Analyse-System für die FIFA Weltmeisterschaft 2026. Kombiniert Buchmacher-Quoten, ELO-Ratings, historische Daten und Live-Statistiken zu fundierten Spielprognosen.

## Was es kann

- **Dashboard** — Interaktives Streamlit-Dashboard mit Live-Spielkarten, Gruppenübersicht, Quoten-Bewegungen und Turnierstatistiken pro Team
- **Agent** — KI-Chatbot (Gemini/Claude/Ollama) beantwortet Fragen zu Spielen, Mannschaften und liefert begründete Prognosen
- **Telegram-Bot** — Derselbe Agent als Telegram-Bot, inkl. automatischer Benachrichtigungen vor Spielbeginn und bei starken Quoten-Bewegungen
- **Live-Tracking** — Minutengenaue Spielstatistiken (Schüsse, Ballbesitz, Pässe, etc.) werden alle 60 Sekunden aktualisiert
- **ELO-System** — Eigenberechnetes ELO-Rating aus 15.000+ historischen Spielen

---

## Architektur

```
┌─────────────────────────────────────────────────────┐
│  Pipeline (täglich + live)                          │
│                                                     │
│  run_daily.py      → Standings, Fixtures, Odds      │
│  fetch_live.py     → Live-Stats während Spielen     │
│  compute_kpis.py   → Team-Statistiken + ELO         │
│  odds_extractor.py → Buchmacher-Quoten (Pinnacle,   │
│                       Betfair, Konsens)             │
└──────────────────────┬──────────────────────────────┘
                       │
                  MySQL Datenbank
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼──────────┐
│    Dashboard   │          │       Agent        │
│  dashboard.py  │          │     agent.py       │
│  (Streamlit)   │          │  (Gemini / Claude) │
└────────────────┘          └────────────────────┘
```

### Datenquellen
| Quelle | Inhalt |
|---|---|
| API-Football (api-sports.io) | Live-Fixtures, Statistiken, Standings, Quoten von Pinnacle, Betfair + Konsens (8 Bookmaker) |
| Kaggle-Datensatz | 15.000+ historische Länderspiele (Basis für ELO + KPIs) |
| FIFA-Ranking CSV | Aktuelle FIFA-Weltrangliste |

---

## Voraussetzungen

- Python 3.13+
- MySQL 8.0 (lokal oder remote)
- API-Keys:
  - [api-sports.io](https://api-sports.io) — WM-Daten & Statistiken
  - [Google AI Studio](https://aistudio.google.com) — Gemini API Key (oder Anthropic)

---

## Lokales Setup

### 1. Repository klonen & Abhängigkeiten installieren

```bash
git clone <repo-url>
cd footballAI
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren

`.env.example` kopieren und mit eigenen Werten füllen:

```bash
cp .env.example .env
```

### 3. Datenbank befüllen

Zwei Möglichkeiten, je nachdem ob ein eigener API-Football-Key vorhanden ist:

**Variante A — mit bereitgestelltem DB-Export:**

```bash
mysql -u <user> -p <db_name> < data.sql
```

Damit ist die Datenbank direkt mit dem finalen Datenstand (historische Daten, WM-2026-Fixtures, Odds, ELO/KPIs, Predictions) befüllt — weiter mit Schritt 5.

**Variante B — eigenständig über die API aufbauen (benötigt `API_FOOTBALL_KEY` in `.env`):**

```bash
# Tabellen erstellen (Frisch-Setup)
python db/schema.py

# Historische Daten laden (Kaggle CSV → DB)
python pipeline/load_historical.py

# ELO-Ratings + Team-KPIs berechnen
python pipeline/compute_kpis.py

# Alle Fixtures der WM 2026 laden
python pipeline/load_tournament_data.py

# Tägliche Pipeline (Standings, Odds, Predictions)
python pipeline/run_daily.py
```

### 5. Dashboard starten

```bash
streamlit run agent/dashboard/dashboard.py
```

→ Öffnet sich auf [http://localhost:8501](http://localhost:8501)

### 6. Agent (Terminal) starten

```bash
python main.py
```

### 7. Telegram-Bot starten (optional)

```bash
python telegram_bot.py
```

Befehle im Bot: `/heute` (heutige Spiele), `/neu` (neue Sitzung starten). Der Bot meldet sich zusätzlich automatisch 30 Minuten vor Spielbeginn und bei starken Quoten-Bewegungen (> 0.25). Ohne `ALLOWED_CHAT_IDS` hat nur die in `TELEGRAM_CHAT_ID` hinterlegte Person Zugriff.

---

## Täglicher Betrieb

| Script | Wann | Was |
|---|---|---|
| `pipeline/run_daily.py` | 1× täglich (morgens) | Standings, Fixtures, Odds, Predictions, KPIs |
| `pipeline/fetch_live.py` | Während Spielen | Live-Stats alle 60s, Snapshots alle 15min |
| `pipeline/compute_kpis.py` | Nach Spieltag | ELO + Team-Statistiken neu berechnen |

---

## Bestehende DB migrieren

Nach Updates die neue Spalten hinzufügen:

```bash
python pipeline/migrate_db.py
```

Das Script ist idempotent — kann mehrfach ausgeführt werden ohne Fehler.

---

## LLM wechseln

In `main.py` (Terminal-Agent) oder via Umgebungsvariable `LLM_PROVIDER`:

```python
# Gemini (Standard)
agent = FootballAIAgent(llm=GeminiLLM())

# Claude
agent = FootballAIAgent(llm=AnthropicLLM())
```
