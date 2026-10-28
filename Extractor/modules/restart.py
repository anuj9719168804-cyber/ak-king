"""/restart: owner-only. Re-executes the bot process (same as the newbot / Saini restart)."""
import os
import sys

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from config import OWNER_ID


@app.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client, m: Message):
    await m.reply_text("🔄 Restarting…", quote=True)
    # The bot is started as `python -m Extractor`; re-run it the same way.
    os.execl(sys.executable, sys.executable, "-m", "Extractor")
