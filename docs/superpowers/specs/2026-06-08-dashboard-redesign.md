# Dashboard Redesign — football Orakel WM 2026

*Spec-Datum: 2026-06-08*

---

## Ziel

Das bestehende Streamlit-Dashboard soll einheitlich gestaltet und die Spielübersicht klarer strukturiert werden. Spiele werden kompakt angezeigt; per Akkordeon-Erweiterung erscheinen detaillierte Statistiken, Prognosen und Wettquoten. Die Quoten-Darstellung wird grundlegend überarbeitet: klare Team-Zuordnung, Wahrscheinlichkeiten als Primärgrösse, Quoten als Sekundärinfo.

---

## 1. Visuelle Richtung

**Palette:**

| Token | Wert | Verwendung |
|---|---|---|
| `navy` | `#16213e` | Heim-Team, Header-Hintergrund, Haupttext |
| `live-green` | `#0a8f4f` | Live-Status, Erfolgsindikatoren |
| `away-red` | `#dc6f5c` | Auswärts-Team |
| `draw-gray` | `#cbd5e1` / `#475569` | Unentschieden-Box |
| `surface` | `#eef1f6` | Hintergrund-Kacheln, neutrale Flächen |
| `text-muted` | `#8a9ab5` / `#9aa6ba` | Labels, Metainfo |
| `border` | `#e8ecf3` | Kanten, Trennlinien |

**Typografie:** DM Sans (bestehend) + DM Mono für Zahlen (bestehend) — unverändert beibehalten.

**Header:** Dunkelblauer Navigationsstreifen (`background: #16213e`) mit weissem Text und blauem Akzent (`#5b9bff`) für "Orakel".

**Status-Badges:** Pill-Form, font-weight 700, uppercase:
- Live: `background: #0a8f4f, color: #fff` — `● LIVE 67'`
- Ausstehend: `background: #eef1f6, color: #8a9ab5` — `21:00`
- Abgeschlossen: `background: #eef1f6, color: #8a9ab5` — `FT`

---

## 2. Komponente: Spielkarte (kollabiert)

Ersetzt die aktuelle breite Expander-Zeile. Kompakte Darstellung mit klarer Team-Zuordnung und Status-Akzent.

**Layout (einzeilig):**
```
[ Gruppe links ] [ Team Heim  Score/vs  Team Auswärts ] [ Status-Badge rechts ]
```

**Details:**
- Gruppe (`Group A`, `Group C` etc.) als kleines Label links (`font-size: 11px, color: #8a9ab5, min-width: 62px`)
- Teamnamen fett, Score blau (`#4a7fd4`) bei laufenden/abgeschlossenen Spielen, `vs` in Grau bei ausstehenden
- Status-Badge rechtsbündig als Pill
- Hintergrundfarbe der gesamten Karte:
  - Live: dezentes Grün `#eafbf1`, Rahmen `#bfead2`
  - Ausstehend/Abgeschlossen: weiss, Rahmen `#e8ecf3`
- Padding: `12px 16px`, Border-Radius: `8px`

**Score-Anzeige-Logik:** Score (`2 : 1`) nur anzeigen wenn `status` NICHT `NS` ist — `vs` anzeigen wenn `status == NS`, unabhängig von DB-Werten.

---

## 3. Komponente: Spielkarte (aufgeklappt — Akkordeon)

Beim Klick auf eine Karte öffnet sich der Detailbereich inline (bestehende `st.expander`-Mechanik, visuell neu gestylt). Drei Abschnitte, von oben nach unten:

### 3.1 Prognosen

Schlanke Balkenzeilen (bestehende Logik beibehalten) für:
- `WM-Orakel` (agent_predictions: home_win_prob / draw_prob / away_win_prob)
- `Football API` (api_predictions: home_win_pct / draw_pct / away_win_pct)

Format: Label links, schmaler Dreifarbbalken (navy/grau/rot), Prozentwerte rechts.

### 3.2 Wettmarkt

**Neues Kachel-Design** (ersetzt alle bestehenden `odds_bar_html`/`pred_row_html` Aufrufe für Quoten):

Für jede Quellen-Zeile (Konsens, Pinnacle, Betfair):

1. **Team-Kopfzeile** (`font-size: 9px, font-weight: 700`):
   - Links: `● TEAMNAME_HEIM` in `#16213e`
   - Rechts: `TEAMNAME_AUSWÄRTS ●` in `#dc6f5c`
   - Kein Label für Unentschieden in der Mitte

2. **Drei gleichbreite Kacheln** (`flex: 1`, `gap: 6px`, `border-radius: 6px`, `padding: 12px 6px`):
   - Heim-Kachel: `background: #16213e`, Zahl `color: #fff`
   - Remis-Kachel: `background: #eef1f6`, Zahl `color: #475569`
   - Auswärts-Kachel: `background: #dc6f5c`, Zahl `color: #fff`
   - Inhalt: Implizite Wahrscheinlichkeit `%` (margin-bereinigt aus DB), `font-size: 15px, font-weight: 700`

3. **Quoten-Zeile** direkt unter den Kacheln (`display: flex, gap: 6px`):
   - Drei `flex:1` Divs, zentriert, `font-size: 10px, color: #9aa6ba, font-family: DM Mono`
   - Inhalt: rohe Quote auf 2 Dezimalstellen (`1.65`, `3.80`, `5.20`)

4. **Meta-Zeile** (Konsens-Block only): `font-size: 10px, color: #c0cadb, text-align: right`
   - `Konsens · {bm_cnt} Bookmakers · Margin {margin}%`
   - Optional: Konfidenz-Badge (`Markt sicher` / `Markt neutral` / `Offenes Spiel`)

Reihenfolge der Quellen-Blöcke: Konsens-Quoten → Pinnacle → Betfair → Implizite Wahrscheinlichkeiten (letztere als separater Block ohne Quoten-Zeile darunter, da bereits `%`-Werte).

### 3.3 Live-Statistiken

Nur sichtbar wenn `status in ["1H", "HT", "2H", "FT", "AET", "PEN"]`.

Grid-Layout (bestehende `stat_bar`-Logik beibehalten): Heim-Wert | Label | Auswärts-Wert, mit proportionalen Balken (navy links, rot rechts). Keine Änderung an der Logik, nur Farben an neue Palette anpassen (`#16213e` statt `#4a7fd4`).

---

## 4. Seiten — Strukturell unverändert

Alle drei Seiten (Übersicht / Gruppenphase / KO-Phase) und die Chat-Sidebar bleiben erhalten. Nur CSS und Komponenten-Rendering werden erneuert.

### Übersicht
Sektionen beibehalten: 🔴 Live → Heute → Morgen → Letzte Resultate. Jede Sektion zeigt kompakte Karten (Typ 2), Klick öffnet Akkordeon (Typ 3).

### Gruppenphase
Gruppenтабellen-Layout bleibt (2-Spalten-Grid), Styling an neue Palette anpassen. Spiele-Sektion darunter zeigt Karten mit Akkordeon.

### KO-Phase
Bracket-Darstellung bleibt (5 Spalten für Sechzehntelfinale → Finale). Karten-Styling an neue Palette anpassen.

---

## 5. Datenlayer-Fix

**`get_api_predictions()` in `agent/tools/mysql_tools.py`:**

Die SQL-Query erweitern um alle bisher fehlenden Spalten, die das Dashboard bereits liest:

```sql
-- Ergänzen:
home_win_implied, draw_implied, away_win_implied,
home_odds_pinnacle, draw_odds_pinnacle, away_odds_pinnacle,
home_odds_betfair, draw_odds_betfair, away_odds_betfair,
margin_avg, odds_bookmaker_count, market_confidence
```

Ohne diesen Fix bleiben Pinnacle, Betfair, Margin, Konfidenz-Badge und implizite Wahrscheinlichkeiten immer leer, obwohl die Daten in der DB vorhanden sind.

---

## 6. Nicht im Scope

- Neue Seiten oder Navigation
- Mobile-Optimierung / Responsive Layout
- Pipeline-Änderungen / neue DB-Tabellen
- KO-Bracket Logik (Stage-Mapping bleibt wie heute)
- Chat-Sidebar Funktionalität

---

## Entscheidungsprotokoll (Brainstorming)

| Thema | Entscheidung |
|---|---|
| Kartendichte | Mittel — Karte mit Status-Akzent |
| Karten-Stil | B: Chip rechts + Hintergrundtönung, Gruppe links |
| Detailansicht | Akkordeon (poliertes st.expander) |
| Visuelle Palette | B: Auffrischen — dunkleres Navy, kräftiges Grün |
| Quoten-Darstellung | Drei gleich breite Kacheln (%, Quoten darunter) |
| Balken vs. Kacheln | Kacheln ohne proportionale Breite — Wahrscheinlichkeit als Primärzahl |
| "Unentschieden"-Label | Weglassen — Kontext ist durch Position klar |
| SQL-Query-Fix | Ja — fehlende Spalten ergänzen |
| Seitenstruktur | Unverändert beibehalten |
