"""/cookies and /getcookies: owner manages the YouTube cookies file used by /y2t.

Ported from the newbot / ADVANCE-TXT-UPLOADER / Saini-1 cookie handlers.
"""
import os

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from config import OWNER_ID

COOKIES_FILE_PATH = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")


@app.on_message(filters.command("cookies") & filters.private & filters.user(OWNER_ID))
async def cookies_upload(client, m: Message):
    await m.reply_text(
        "📂 Send the YouTube cookies file now (<code>.txt</code>, Netscape format).\n"
        "It replaces the current file. You have 2 minutes.",
        quote=True,
    )
    try:
        reply: Message = await app.listen(m.chat.id, timeout=120)
    except Exception:
        await m.reply_text("⌛ Timed out. Send /cookies again.")
        return

    doc = reply.document
    if not doc or not (doc.file_name or "").lower().endswith(".txt"):
        await m.reply_text("❌ Not a .txt file. Send /cookies again.")
        return

    tmp = await reply.download(file_name=COOKIES_FILE_PATH + ".tmp")
    try:
        with open(tmp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "youtube.com" not in content and "HTTP Cookie File" not in content:
            await m.reply_text("❌ This doesn't look like a YouTube cookies file. Nothing was changed.")
            return
        os.replace(tmp, COOKIES_FILE_PATH)
        await m.reply_text("✅ Cookies updated.")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@app.on_message(filters.command("getcookies") & filters.private & filters.user(OWNER_ID))
async def cookies_get(client, m: Message):
    if not os.path.exists(COOKIES_FILE_PATH):
        await m.reply_text("No cookies file is set yet. Use /cookies to upload one.")
        return
    await client.send_document(m.chat.id, COOKIES_FILE_PATH, caption="Current <code>youtube_cookies.txt</code>")
