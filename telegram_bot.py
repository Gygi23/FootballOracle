"""
telegram_bot.py — FootballAI Telegram Bot

Features:
  - Fragen an den FootballAI-Agenten stellen
  - /heute  → heutige Spiele anzeigen
  - /neu    → neue Sitzung starten

Automatische Benachrichtigungen:
  - 30 Minuten vor Spielstart
  - Starke Quoten-Bewegungen (> 10 Rappen)

Setup:
  TELEGRAM_BOT_TOKEN  → Token von @BotFather
  TELEGRAM_CHAT_ID    → Deine persönliche Chat-ID (nach /start im Bot sichtbar)
"""

import logging
import os

from dotenv import load_dotenv
from sqlalchemy import text
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID  = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# ─── Agent initialisieren ─────────────────────────────────────────────────────

_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
if _provider == "claude":
    from agent.llm.anthropic import AnthropicLLM
    _llm = AnthropicLLM()
elif _provider == "ollama":
    from agent.llm.ollama import OllamaLLM
    _llm = OllamaLLM()
else:
    from agent.llm.gemini import GeminiLLM
    _llm = GeminiLLM()

from agent.agent import FootballAIAgent
agent = FootballAIAgent(llm=_llm)


# ─── Commands ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"⚽ *footballAI — WM 2026*\n\n"
        f"Stelle mir eine Frage zu einem Spiel, einer Mannschaft oder einer Prognose.\n\n"
        f"*Befehle:*\n"
        f"/heute — Heutige Spiele\n"
        f"/neu — Neue Sitzung starten\n\n"
        f"Deine Chat-ID: {chat_id}\n"
        f"Diese ID als TELEGRAM_CHAT_ID in Railway setzen.",
        parse_mode="Markdown"
    )


async def cmd_neu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    agent.new_session()
    await update.message.reply_text("✅ Neue Sitzung gestartet.")


async def cmd_heute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from agent.tools.mysql_tools import get_engine
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT home_team, away_team, match_date, status,
                   home_score, away_score, stage
            FROM tournament_fixtures
            WHERE season = 2026 AND league_id = 1
              AND DATE(match_date) = CURDATE()
            ORDER BY match_date
        """)).fetchall()

    if not rows:
        await update.message.reply_text("Heute finden keine WM-Spiele statt.")
        return

    lines = ["⚽ *Heutige Spiele:*\n"]
    for r in rows:
        time_str = r.match_date.strftime("%H:%M") if r.match_date else "?"
        if r.status in ("FT", "AET", "PEN"):
            score = f"{r.home_score}:{r.away_score} ✅"
        elif r.status in ("1H", "2H", "HT", "ET", "LIVE"):
            score = f"{r.home_score}:{r.away_score} 🔴 LIVE"
        else:
            score = f"{time_str} Uhr"
        lines.append(f"• {r.home_team} vs {r.away_team} — {score}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── Nachrichten → Agent ──────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Analysiere…")
    response = agent.chat(update.message.text)

    # Telegram-Limit: 4096 Zeichen pro Nachricht
    for i in range(0, len(response), 4000):
        await update.message.reply_text(response[i:i + 4000])


# ─── Automatische Benachrichtigungen ──────────────────────────────────────────

async def notify_pregame(ctx: ContextTypes.DEFAULT_TYPE):
    """30 Minuten vor Spielstart eine Nachricht senden."""
    if not OWNER_CHAT_ID:
        return

    from agent.tools.mysql_tools import get_engine
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT home_team, away_team, match_date, stage
            FROM tournament_fixtures
            WHERE season = 2026 AND league_id = 1
              AND status = 'NS'
              AND match_date BETWEEN NOW() + INTERVAL 28 MINUTE
                                 AND NOW() + INTERVAL 32 MINUTE
        """)).fetchall()

    for r in rows:
        await ctx.bot.send_message(
            OWNER_CHAT_ID,
            f"🔔 *Spielstart in 30 Minuten!*\n\n"
            f"⚽ {r.home_team} vs {r.away_team}\n"
            f"🕐 {r.match_date.strftime('%H:%M')} Uhr · {r.stage}",
            parse_mode="Markdown"
        )


async def notify_odds_movement(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Starke Quoten-Bewegungen melden — vergleicht die letzten ZWEI Snapshots.

    Schwellen (abgestuft nach Zeitnähe zum Anpfiff):
      < 24h vor Anpfiff  → Bewegung > 0.10  (empfindlich — Aufstellung/Verletzung)
      24h–48h vorher     → Bewegung > 0.20  (nur klare Signale)
      > 48h vorher       → keine Benachrichtigung (Markt-Rauschen)
    """
    if not OWNER_CHAT_ID:
        return

    from agent.tools.mysql_tools import get_engine
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            WITH ranked AS (
                SELECT
                    fixture_id,
                    home_odds, draw_odds, away_odds,
                    recorded_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY fixture_id ORDER BY recorded_at DESC
                    ) AS rn
                FROM odds_history
            )
            SELECT
                tf.home_team, tf.away_team, tf.match_date, tf.stage,
                r1.home_odds  AS h_now,  r1.draw_odds  AS d_now,  r1.away_odds  AS a_now,
                r2.home_odds  AS h_prev, r2.draw_odds  AS d_prev, r2.away_odds  AS a_prev,
                r1.recorded_at AS snapshot_at,
                TIMESTAMPDIFF(HOUR, NOW(), tf.match_date) AS hours_to_kickoff
            FROM tournament_fixtures tf
            JOIN ranked r1 ON r1.fixture_id = tf.fixture_id AND r1.rn = 1
            JOIN ranked r2 ON r2.fixture_id = tf.fixture_id AND r2.rn = 2
            WHERE tf.season = 2026
              AND tf.status = 'NS'
              AND tf.match_date BETWEEN NOW() AND NOW() + INTERVAL 48 HOUR
              AND (
                  -- < 24h: Schwelle 0.10
                  (TIMESTAMPDIFF(HOUR, NOW(), tf.match_date) < 24
                   AND (ABS(r1.home_odds - r2.home_odds) > 0.10
                        OR ABS(r1.away_odds - r2.away_odds) > 0.10))
                  OR
                  -- 24–48h: Schwelle 0.20 (nur starke Signale)
                  (TIMESTAMPDIFF(HOUR, NOW(), tf.match_date) BETWEEN 24 AND 48
                   AND (ABS(r1.home_odds - r2.home_odds) > 0.20
                        OR ABS(r1.away_odds - r2.away_odds) > 0.20))
              )
            ORDER BY tf.match_date
        """)).fetchall()

    for r in rows:
        h_delta = float(r.h_now  or 0) - float(r.h_prev or 0)
        d_delta = float(r.d_now  or 0) - float(r.d_prev or 0)
        a_delta = float(r.a_now  or 0) - float(r.a_prev or 0)
        hours   = int(r.hours_to_kickoff or 0)

        time_str  = r.match_date.strftime("%d.%m. %H:%M") if r.match_date else "?"
        timing    = f"in {hours}h" if hours < 24 else f"in {hours//24}d {hours%24}h"

        lines = [f"📊 *Quotenbewegung* — {r.home_team} vs {r.away_team}",
                 f"{time_str} Uhr · {r.stage} · Anpfiff {timing}\n"]

        for team, now, prev, delta in [
            (r.home_team,     r.h_now, r.h_prev, h_delta),
            ("Unentschieden", r.d_now, r.d_prev, d_delta),
            (r.away_team,     r.a_now, r.a_prev, a_delta),
        ]:
            if abs(delta) > 0.08:
                arrow = "▼" if delta < 0 else "▲"
                note  = " ← Geld fliesst rein" if delta < 0 else " ← driftet weg"
                lines.append(
                    f"• {team}: {float(prev):.2f} → {float(now):.2f}  "
                    f"{arrow}{abs(delta):.2f}{note}"
                )

        lines.append("\nMögliche Ursache: Verletzung, Aufstellung oder Sharp-Money.")

        await ctx.bot.send_message(
            OWNER_CHAT_ID, "\n".join(lines), parse_mode="Markdown"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN nicht gesetzt.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("neu",   cmd_neu))
    app.add_handler(CommandHandler("heute", cmd_heute))

    # Nachrichten
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Scheduled Jobs
    jq = app.job_queue
    jq.run_repeating(notify_pregame,       interval=60,  first=10)   # jede Minute
    jq.run_repeating(notify_odds_movement, interval=900, first=30)   # alle 15 Min

    logger.info("Bot läuft...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
