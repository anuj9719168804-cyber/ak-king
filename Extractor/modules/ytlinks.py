"""/y2t: export a YouTube video or playlist as a .txt file of "title : url" lines.

Ported from the newbot / ADVANCE-TXT-UPLOADER / Saini-1 y2t / yt2txt commands, using yt-dlp in
flat mode (no downloads). Uses youtube_cookies.txt when it exists (set it with /cookies).
Gated like the other tools (owner or premium).
"""
import asyncio
import os
import re

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from Extractor.core.access import is_allowed
from Extractor.modules.cookies import COOKIES_FILE_PATH

_YT_RE = re.compile(r"(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be)/\S+", re.I)


def _extract(url: str) -> list[tuple[str, str]]:
    import yt_dlp  # imported here so the rest of the bot still loads without yt-dlp installed

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }
    if os.path.exists(COOKIES_FILE_PATH):
        opts["cookiefile"] = COOKIES_FILE_PATH
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries")
    items = []
    if entries is not None:  # playlist
        for e in entries:
            if not e:
                continue
            vid = e.get("url") or e.get("id")
            link = vid if str(vid).startswith("http") else f"https://www.youtube.com/watch?v={vid}"
            items.append((e.get("title") or "Untitled", link))
    else:  # single video
        items.append((info.get("title") or "Untitled", info.get("webpage_url") or url))
    return items


@app.on_message(filters.command(["y2t", "yt2txt"]))
async def youtube_to_txt(client, m: Message):
    if not await is_allowed(m.from_user.id):
        await m.reply_text("🚫 This tool is for premium users. Contact the owner.")
        return
    if len(m.command) > 1:
        url = m.command[1]
    else:
        await m.reply_text("📺 Send the YouTube video or playlist link.", quote=True)
        try:
            reply: Message = await app.listen(m.chat.id, timeout=120)
        except Exception:
            await m.reply_text("⌛ Timed out. Send /y2t again.")
            return
        url = (reply.text or "").strip()

    if not _YT_RE.search(url):
        await m.reply_text("❌ That isn't a YouTube link.")
        return

    status = await m.reply_text("⏳ Reading YouTube…")
    try:
        items = await asyncio.to_thread(_extract, url)
    except Exception as e:
        await status.edit_text(f"❌ Could not read that link: <code>{type(e).__name__}</code>")
        return
    if not items:
        await status.edit_text("❌ Nothing found at that link.")
        return

    path = "youtube_links.txt"
    with open(path, "w", encoding="utf-8") as f:
        for title, link in items:
            f.write(f"{title} : {link}\n")
    try:
        await status.delete()
        await client.send_document(m.chat.id, path, caption=f"📄 {len(items)} video(s)")
    finally:
        if os.path.exists(path):
            os.remove(path)
