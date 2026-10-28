"""
Database channel auto-upload, ported from pw-pro-bot (db_upload_careerwill / db_upload_kgs).

Extracts EVERY CareerWill batch (or KGS App course) and posts each one as a .txt in a channel,
with a pinned "update" message that turns into a summary when the run finishes.

Owner / sudo only:
  /setdb cw|kgs <channel_id>   (owner) set the target channel. The bot must be an admin there.
  /dbinfo                      show the channel set for each source
  /dbupload cw|kgs             start the upload (one run at a time)
  /dbstop                      stop after the current batch

The channel can also come from the DB_CHANNEL_CW / DB_CHANNEL_KGS environment variables.
"""
import asyncio
import html as _html
import io
import json
import os
import time

import aiohttp
from pyrogram import filters
from pyrogram.errors import FloodWait

from Extractor import app
from Extractor.core.sudo_store import is_sudo
from Extractor.modules.nlx_sources import SRC, _bar, _safe_name
from config import OWNER_ID

SETTINGS_FILE = os.environ.get("NLX_SETTINGS_FILE", "nlx_settings.json")
PLATFORMS = {
    "cw":  {"name": "CareerWill", "unit": "batches", "emoji": "🎯", "prefix": "CW",  "env": "DB_CHANNEL_CW"},
    "kgs": {"name": "KGS App",    "unit": "courses", "emoji": "🎓", "prefix": "KGS", "env": "DB_CHANNEL_KGS"},
}
_STOP = {"flag": False}
_RUNNING = {"key": None}


def _load():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_channel(key):
    val = _load().get(key) or os.environ.get(PLATFORMS[key]["env"], "")
    try:
        return int(val) if val else None
    except (TypeError, ValueError):
        return None


def _allowed(uid):
    return uid == OWNER_ID or is_sudo(uid)


async def _noop(done, total, cur):
    return None


async def _edit(msg, text):
    try:
        await msg.edit_text(text)
    except Exception:
        pass


async def _send_doc(ch, data, fname, caption):
    for _ in range(3):
        try:
            buf = io.BytesIO(data)
            buf.name = fname
            await app.send_document(ch, buf, file_name=fname, caption=caption)
            return True
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception:
            await asyncio.sleep(2)
    return False


async def run_db_upload(message, key):
    plat, src = PLATFORMS[key], SRC[key]
    ch = get_channel(key)
    if not ch:
        await message.reply_text(f"❌ {plat['name']} ka channel set nahi hai.\n<code>/setdb {key} -100xxxxxxxxxx</code> chalao (bot ko us channel ka admin banao).")
        return
    if _RUNNING["key"]:
        await message.reply_text(f"⏳ Ek DB upload ({PLATFORMS[_RUNNING['key']]['name']}) already chal raha hai. /dbstop se roko.")
        return
    _RUNNING["key"], _STOP["flag"] = key, False
    pin = None
    try:
        try:
            pin = await app.send_message(
                ch, f"📌 <b>{plat['name']} — Full Database Update</b>\n\n🕐 Started: <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"⏳ Sare {plat['unit']} extract ho rahe hain...")
            await app.pin_chat_message(ch, pin.id, disable_notification=True)
        except Exception as e:
            await message.reply_text(f"⚠️ Channel pe pin/message fail: <code>{_html.escape(str(e)[:150])}</code>\nExtract continue kar raha hoon...")

        prog = await message.reply_text(f"⏳ {plat['name']} {plat['unit']} fetch ho rahe hain...")
        async with aiohttp.ClientSession() as session:
            items = await src["list"](session)
            if not items:
                await _edit(prog, f"❌ {plat['name']} ki list fetch fail (API down ho sakti hai).")
                return
            total, done, ok, t0 = len(items), 0, 0, time.time()
            await _edit(prog, f"📦 <b>{total}</b> {plat['unit']} mile!\n\n⚙️ Extracting & uploading... (/dbstop se rok sakte ho)")
            for it in items:
                if _STOP["flag"]:
                    break
                try:
                    res = await src["extract"](session, it["id"], it["title"], _noop)
                    if res["lines"]:
                        hdr = ("════════════════════════════\n"
                               f"  Extractor — {plat['name']}\n  Batch: {it['title']}\n  ID: {it['id']}\n"
                               f"  Videos: {res['v']} | PDFs: {res['p']} | Total: {len(res['lines'])}\n"
                               "════════════════════════════\n\n")
                        fname = f"{plat['prefix']}_{_safe_name(it['title'])}_{it['id']}.txt"
                        cap = (f"{plat['emoji']} <b>{plat['name']}</b>\n📌 <b>{_html.escape(it['title'])}</b>\n🆔 <code>{_html.escape(str(it['id']))}</code>\n"
                               f"🎥 <code>{res['v']}</code> Videos | 📄 <code>{res['p']}</code> PDFs | 📦 <code>{len(res['lines'])}</code> Total")
                        ok += await _send_doc(ch, (hdr + "\n".join(res["lines"])).encode("utf-8"), fname, cap)
                except Exception:
                    pass
                done += 1
                if done % 5 == 0:
                    bar, pct = _bar(done, total)
                    await _edit(prog, f"⚙️ <b>{plat['name']} DB Upload</b>\n\n{bar} <code>{pct}%</code>\n"
                                      f"📁 <code>{done}/{total}</code> | ✅ <code>{ok}</code> uploaded\n⏱ <code>{time.time() - t0:.0f}s</code>")
                await asyncio.sleep(0.5)
        head = "🛑 Stopped" if _STOP["flag"] else "✅ Complete"
        summary = (f"{head} — <b>{plat['name']} DB Upload</b>\n\n📦 {plat['unit'].capitalize()} checked: <code>{done}/{total}</code>\n"
                   f"✅ Uploaded: <code>{ok}</code>\n⏱ Time: <code>{time.time() - t0:.0f}s</code>")
        await _edit(prog, summary)
        if pin:
            try:
                await app.edit_message_text(ch, pin.id, summary)
            except Exception:
                pass
    finally:
        _RUNNING["key"] = None


@app.on_message(filters.command("setdb") & filters.private, group=-1)
async def setdb_cmd(client, m):
    if not m.from_user or m.from_user.id != OWNER_ID:
        return
    args = m.command[1:]
    if len(args) != 2 or args[0].lower() not in PLATFORMS or not args[1].lstrip("-").isdigit():
        await m.reply_text("Usage: <code>/setdb cw|kgs -100xxxxxxxxxx</code>")
        return
    key, data = args[0].lower(), _load()
    data[key] = int(args[1])
    await m.reply_text(f"✅ {PLATFORMS[key]['name']} channel set: <code>{args[1]}</code>" if _save(data)
                       else "❌ Settings file save nahi hui (disk read-only?). DB_CHANNEL_CW / DB_CHANNEL_KGS env var use karo.")


@app.on_message(filters.command("dbinfo") & filters.private, group=-1)
async def dbinfo_cmd(client, m):
    if not m.from_user or not _allowed(m.from_user.id):
        return
    lines = [f"{p['emoji']} {p['name']}: <code>{get_channel(k) or 'not set'}</code>" for k, p in PLATFORMS.items()]
    await m.reply_text("🗄 <b>Database channels</b>\n\n" + "\n".join(lines) + "\n\n<code>/setdb cw|kgs -100…</code> (owner)  |  <code>/dbupload cw|kgs</code>")


@app.on_message(filters.command("dbupload") & filters.private, group=-1)
async def dbupload_cmd(client, m):
    if not m.from_user or not _allowed(m.from_user.id):
        return
    key = (m.command[1].lower() if len(m.command) > 1 else "")
    if key not in PLATFORMS:
        await m.reply_text("Usage: <code>/dbupload cw</code> ya <code>/dbupload kgs</code>")
        return
    asyncio.create_task(run_db_upload(m, key))


@app.on_message(filters.command("dbstop") & filters.private, group=-1)
async def dbstop_cmd(client, m):
    if not m.from_user or not _allowed(m.from_user.id):
        return
    if _RUNNING["key"]:
        _STOP["flag"] = True
        await m.reply_text("🛑 Current batch ke baad ruk jayega.")
    else:
        await m.reply_text("Koi DB upload nahi chal raha.")
