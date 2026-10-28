"""/t2t: turn text the user sends into a .txt file with a chosen name.

Ported from the newbot Text-to-TXT converter. Gated like the other tools (owner or premium).
"""
import os
import re

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from Extractor.core.access import is_allowed


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "", name).strip().strip(".")
    return name[:60] or "output"


@app.on_message(filters.command("t2t"))
async def text_to_txt(client, m: Message):
    if not await is_allowed(m.from_user.id):
        await m.reply_text("🚫 This tool is for premium users. Contact the owner.")
        return
    await m.reply_text(
        "📝 Send the <b>text</b> you want saved as a .txt file.",
        quote=True,
    )
    try:
        body: Message = await app.listen(m.chat.id, timeout=300)
    except Exception:
        await m.reply_text("⌛ Timed out. Send /t2t again.")
        return
    if not body.text:
        await m.reply_text("❌ Please send plain text. Send /t2t again.")
        return

    await m.reply_text("✏️ Now send the <b>file name</b> (without .txt).")
    try:
        name_msg: Message = await app.listen(m.chat.id, timeout=120)
    except Exception:
        await m.reply_text("⌛ Timed out. Send /t2t again.")
        return

    path = f"{_safe_name(name_msg.text or 'output')}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.text)
    try:
        await client.send_document(m.chat.id, path, caption=f"📄 {path}")
    finally:
        if os.path.exists(path):
            os.remove(path)
