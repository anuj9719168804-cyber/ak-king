"""Command aliases from TXT-EXTRACTOR and vikas-bot, routed to the existing Extractor handlers.

/extract -> Classplus batch extract (same as /cp, staff only), from TXT-EXTRACTOR.
/cw      -> CareerWill (private chat), from vikas-bot. Extractor's own CareerWill flow is /ugcw.
"""
from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from Extractor.core.sudo_store import is_sudo
from Extractor.modules.classplus import classplus_txt
from Extractor.modules.careerwill import career_will


@app.on_message(filters.command("extract"))
async def extract_alias(client, m: Message):
    if not is_sudo(m.from_user.id):
        await m.reply_text("🚫 Only the owner or sudo users can use /extract.")
        return
    await classplus_txt(client, m)


@app.on_message(filters.command("cw") & filters.private)
async def cw_alias(client, m: Message):
    await career_will(client, m)
