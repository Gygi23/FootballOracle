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
    """Starke Quoten-Bewegungen melden (> 10 Rappen seit Marktöffnung)."""
    if not OWNER_CHAT_ID:
        return

    from agent.tools.mysql_tools import get_engine
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT tf.home_team, tf.away_team,
                   ap.home_odds,      ap.home_odds_open,
                   ap.away_odds,      ap.away_odds_open
            FROM api_predictions ap
            JOIN tournament_fixtures tf ON ap.fixture_id = tf.fixture_id
            WHERE tf.season = 2026 AND tf.status = 'NS'
              AND ap.home_odds_open IS NOT NULL
              AND (
                ABS(ap.home_odds  - ap.home_odds_open)  > 0.10
                OR ABS(ap.away_odds - ap.away_odds_open) > 0.10
              )
        """)).fetchall()

    for r in rows:
        lines = [f"📊 *Quotenbewegung: {r.home_team} vs {r.away_team}*\n"]
        h_delta = (r.home_odds or 0) - (r.home_odds_open or 0)
        a_delta = (r.away_odds or 0) - (r.away_odds_open or 0)

        if abs(h_delta) > 0.10:
            arrow = "▼" if h_delta < 0 else "▲"
            lines.append(
                f"• {r.home_team}: {r.home_odds_open:.2f} → {r.home_odds:.2f} "
                f"{arrow}{abs(h_delta):.2f}"
            )
        if abs(a_delta) > 0.10:
            arrow = "▼" if a_delta < 0 else "▲"
            lines.append(
                f"• {r.away_team}: {r.away_odds_open:.2f} → {r.away_odds:.2f} "
                f"{arrow}{abs(a_delta):.2f}"
            )

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
