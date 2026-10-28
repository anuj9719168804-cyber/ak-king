"""/e2t: tidy up a .txt file of "Title:link" lines and "- topic" lines.

Ported from the newbot / ADVANCE-TXT-UPLOADER editor. Groups links by title, sorts titles and topics,
then sends the result back. Gated like the other tools (owner, sudo or premium).
"""
import os
import re

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from Extractor.core.access import is_allowed


def edit_lines(lines: list[str]) -> list[str]:
    """Pure function: parse and re-emit the editor's format. Returns the output lines."""
    subjects: dict = {}
    current = None
    for raw in lines:
        line = raw.strip()
        if line and ":" in line:
            title, url = (p.strip() for p in line.split(":", 1))
            subjects.setdefault(title, {"links": [], "topics": []})["links"].append(url)
            current = title
        elif line.startswith("-") and current:
            subjects[current]["topics"].append(line.strip("- ").strip())
    out = []
    for title, data in sorted(subjects.items()):
        for link in data["links"]:
            out.append(f"{title}:{link}")
        for topic in sorted(data["topics"]):
            out.append(f"- {topic}")
    return out


def _safe(name: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "", name).strip().strip(".")
    return name[:60] or "edited"


@app.on_message(filters.command("e2t"))
async def edit_txt(client, m: Message):
    if not await is_allowed(m.from_user.id):
        await m.reply_text("🚫 This tool is for premium users. Contact the owner.")
        return
    await m.reply_text("📝 Send your <b>.txt</b> file (titles, links and <code>- topic</code> lines).", quote=True)
    try:
        doc_msg: Message = await app.listen(m.chat.id, timeout=180)
    except Exception:
        await m.reply_text("⌛ Timed out. Send /e2t again.")
        return
    if not doc_msg.document or not (doc_msg.document.file_name or "").lower().endswith(".txt"):
        await m.reply_text("🚨 Please send a .txt file. Send /e2t again.")
        return

    original = _safe(os.path.splitext(doc_msg.document.file_name)[0])
    src = await doc_msg.download()
    try:
        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            result = edit_lines(f.readlines())
    finally:
        if os.path.exists(src):
            os.remove(src)

    await m.reply_text("🔄 Send the new file name, or <code>d</code> to keep <b>" + original + "</b>.")
    try:
        name_msg: Message = await app.listen(m.chat.id, timeout=120)
        choice = (name_msg.text or "d").strip()
    except Exception:
        choice = "d"
    name = original if choice.lower() == "d" else _safe(choice)

    path = f"{name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(result) + ("\n" if result else ""))
    try:
        await client.send_document(m.chat.id, path, caption="📥 Edited file")
    finally:
        if os.path.exists(path):
            os.remove(path)
