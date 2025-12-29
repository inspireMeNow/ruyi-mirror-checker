import logging
import httpx
import asyncio
from typing import Dict, Any
from os import environ
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ruyi Mirror Checker")

RESULTS_URL = environ.get(
    "RESULTS_URL",
    "https://raw.githubusercontent.com/inspireMeNow/ruyi-mirror-checker/refs/heads/hidden/status.json",
)
TELEGRAM_MSG_LIMIT = 4000
TOKEN = environ.get("TELEGRAM_BOT_TOKEN")
REFRESH_INTERVAL = 3 * 60 * 60  # 3 hours

status_data: Dict[str, Any] = {}
telegram_app = None


async def fetch_status_json():
    """Fetch the pre-generated JSON from GitHub."""
    global status_data
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(RESULTS_URL)
        resp.raise_for_status()
        status_data = resp.json()
        logger.info("Loaded %d boards from status.json", len(status_data.get("boards", {})))


async def refresh_status_periodically():
    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        try:
            await fetch_status_json()
        except Exception as e:
            logger.error("Failed to refresh status.json: %s", e)


@app.on_event("startup")
async def startup_event():
    """Fetch JSON once at startup"""
    await fetch_status_json()
    asyncio.create_task(refresh_status_periodically())


# Telegram Bot

def get_telegram_app():
    global telegram_app
    if telegram_app is None:
        if not TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN not set, Telegram bot disabled")
            return None
        telegram_app = Application.builder().token(TOKEN).build()
        telegram_app.add_handler(CommandHandler("boards", boards_command))
        telegram_app.add_handler(CommandHandler("board", board_command))
        telegram_app.add_handler(CommandHandler(["start", "help"], start_command))
    return telegram_app


async def send_long_message(update: Update, text: str):
    """Split long messages to avoid Telegram length limit."""
    if len(text) <= TELEGRAM_MSG_LIMIT:
        await update.message.reply_text(text)
        return

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > TELEGRAM_MSG_LIMIT:
            if current:
                parts.append(current)
            current = line
        else:
            current += "\n" + line if current else line
    if current:
        parts.append(current)

    for part in parts:
        await update.message.reply_text(part)


def format_status(available: bool | None, status_code: int | None) -> str:
    """Format availability status."""
    if status_code == 404:
        return "Not found (404)"
    if available:
        return f"Available ({status_code})"
    return f"Unavailable ({status_code})"


def format_distfiles(data: dict) -> str:
    """Format distfiles for display."""
    lines = []
    distfiles = data.get("distfiles", [])

    if not distfiles:
        return "No distfiles."

    for df in distfiles:
        dist_name = df.get("name", "unknown")
        urls = df.get("urls", [])

        if not urls:
            lines.append(
                f'name: "{dist_name}"\n'
                f'url: "-"\n'
                f'status: "No URLs"\n'
                + "-" * 30
            )
            continue

        for u in urls:
            url = u.get("url") or "-"
            status_code = u.get("status_code")
            is_available = u.get("available")
            status_text = format_status(is_available, status_code)

            lines.append(
                f'name: "{dist_name}"\n'
                f'url: "{url}"\n'
                f'status: "{status_text}"\n'
                + "-" * 30
            )

    return "\n".join(lines).rstrip("- ")



async def boards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all boards."""
    try:
        boards = status_data.get("boards", {})
        if not boards:
            await update.message.reply_text("No boards available.")
            return

        board_list = "\n".join(f"- {b}" for b in sorted(boards.keys()))
        msg = f"Available Boards:\n\n{board_list}"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Failed to fetch boards: {e}")
        await update.message.reply_text("Error fetching boards.")


async def board_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get URLs for a specific board with availability info."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /board <board_name>\n\n"
            "Example: /board lpi4a\n\n"
            "Use /boards to see all available boards"
        )
        return

    board_name = context.args[0]
    try:
        boards = status_data.get("boards", {})

        if board_name not in boards:
            await update.message.reply_text(f"Board '{board_name}' not found.")
            return

        board_data = {
            "distfiles": boards[board_name].get("distfiles", [])
        }
        message = format_distfiles(board_data)
        await send_long_message(update, message)
    except Exception as e:
        logger.error(f"Failed to fetch board '{board_name}': {e}")
        await update.message.reply_text(f"Error fetching board '{board_name}'.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Ruyi Mirror Checker\n\n"
        "Commands:\n"
        "/boards - List all boards\n"
        "/board <name> - Check board availability\n"
        "/help - Show this message\n\n"
        "Status:\n"
        "Available (200) — File is accessible\n"
        "Not found (404) — File does not exist\n"
        "Unavailable – Server is experiencing issues"
    )
    await update.message.reply_text(text)


# FastAPI

@app.get("/")
def root():
    """Service information."""
    return {
        "service": "ruyi-mirror-checker",
        "results_url": RESULTS_URL,
        "endpoints": {
            "boards": "/board-images",
            "board_detail": "/board-images/{board_name}",
            "telegram_webhook": "/api/webhook",
        },
    }


@app.get("/board-images")
def list_board_images():
    """List all available boards."""
    boards = status_data.get("boards", {})
    return {
        "generated_at": status_data.get("generated_at"),
        "boards": sorted(boards.keys()),
    }


@app.get("/board-images/{board_name}")
def get_board_image(board_name: str):
    """Get detailed information for a specific board."""
    boards = status_data.get("boards", {})

    if board_name not in boards:
        raise HTTPException(status_code=404, detail=f"Board '{board_name}' not found")

    return {
        "generated_at": status_data.get("generated_at"),
        "board": board_name,
        "distfiles": boards[board_name].get("distfiles", []),
    }


@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook requests."""
    if not TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not set")

    try:
        body = await request.json()
        tg_app = get_telegram_app()

        if not tg_app:
            raise HTTPException(status_code=500, detail="Telegram bot not initialized")

        update = Update.de_json(body, tg_app.bot)
        await tg_app.initialize()
        await tg_app.process_update(update)

        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "boards_loaded": len(status_data.get("boards", {})),
        "telegram_enabled": TOKEN is not None,
    }
