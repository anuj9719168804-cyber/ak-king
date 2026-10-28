"""/id and /info: show a chat id or your own Telegram details.

Ported from the newbot /id and /info commands.
"""
from pyrogram import filters
from pyrogram.types import Message

from Extractor import app


@app.on_message(filters.command("id"))
async def chat_id(client, m: Message):
    await m.reply_text(f"🆔 <b>Chat ID:</b> <code>{m.chat.id}</code>", quote=True)


@app.on_message(filters.private & filters.command("info"))
async def user_info(client, m: Message):
    u = m.from_user
    text = (
        "✨ <b>Information</b> ✨\n\n"
        f"👤 <b>First name:</b> {u.first_name}\n"
        f"👤 <b>Last name:</b> {u.last_name or 'None'}\n"
        f"🔗 <b>Username:</b> @{u.username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{u.id}</code>\n"
        f"🔗 <b>Profile:</b> {u.mention}"
    )
    await m.reply_text(text, disable_web_page_preview=True, quote=True)
