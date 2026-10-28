"""TXT-TO-VIDEO modes: /king (alias /upload), /bravo, /spidy, /advance, /alpha.

All five run the same TXT flow (send TXT, choose start, batch name, resolution, credit, thumbnail, then
download and upload each link). /advance also asks for a PW token, as the original did; note that the
original TXT-TO-VIDEO code stores that token but never uses it, so this port doesn't use it either.

Gated like the other tools: owner, sudo or premium.
"""
import os
import shutil
import tempfile
import asyncio

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from Extractor import app
from Extractor.core.access import is_allowed
from Extractor.core import txt_engine as E

MODES = {
    "tushar": E.ModeOptions("tushar", show_counts=True),
    "king": E.ModeOptions("king"),
    "bravo": E.ModeOptions("bravo"),
    "spidy": E.ModeOptions("spidy"),
    "advance": E.ModeOptions("advance", ask_token=True),
    "alpha": E.ModeOptions("alpha"),
}


RUNNING: dict[int, bool] = {}   # chat id -> True while a batch is running in that chat


def request_stop(chat_id: int) -> bool:
    """Ask the running batch in this chat to stop after the current item. Returns False if none is running."""
    if RUNNING.get(chat_id):
        RUNNING[chat_id] = False
        return True
    return False


async def _ask(app_, chat_id, timeout):
    try:
        return await app_.listen(chat_id, timeout=timeout)
    except Exception:
        return None


async def run_mode(client, m: Message, opts: E.ModeOptions):
    if not await is_allowed(m.from_user.id):
        await m.reply_text("🚫 This tool is for premium users. Contact the owner.")
        return
    chat = m.chat.id
    if RUNNING.get(chat):
        await m.reply_text("⏳ A batch is already running in this chat. Send /stop to cancel it first.")
        return
    missing = E.missing_tools()
    if missing:
        await m.reply_text("⚠️ The server is missing: <code>" + ", ".join(missing) +
                           "</code>. Ask the admin to install it.")
        return

    # 1. TXT file
    await m.reply_text(f"🔹 <b>{opts.name}</b> mode. Send the <b>TXT</b> file.", quote=True)
    doc = await _ask(app, chat, 300)
    if not doc or not doc.document or not (doc.document.file_name or "").lower().endswith(".txt"):
        await m.reply_text("❌ Please send a .txt file. Start again with the command.")
        return
    workdir = tempfile.mkdtemp(prefix="txt2video_")
    try:
        src = await doc.download(file_name=os.path.join(workdir, "input.txt"))
        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            items = E.parse_txt(f.read())
        batch_default = os.path.splitext(doc.document.file_name)[0]
        if not items:
            await m.reply_text("❌ No links found in that file (each line needs Title:https://...).")
            return
        if opts.show_counts:
            kinds = [E.classify(u) for _, u in items]
            vids = sum(k in ("video", "youtube", "m3u8") for k in kinds)
            await m.reply_text(
                f"📊 <b>Links:</b> {len(items)}\n"
                f"🎞️ Videos: {vids}\n"
                f"📄 PDFs: {kinds.count('pdf')}\n"
                f"🖼️ Images: {kinds.count('image')}\n"
                f"🗜️ Zips: {kinds.count('zip')}\n"
                f"🌐 HTML: {kinds.count('html')}\n"
                f"📁 Other files: {kinds.count('drive')}")

        # 2. start index
        await m.reply_text(f"📊 Total links found: <b>{len(items)}</b>\n\nSend the number to start from (1 = first).")
        ans = await _ask(app, chat, 120)
        try:
            start = min(max(int((ans.text or "1").strip()), 1), len(items))
        except ValueError:
            start = 1

        # 3. batch name
        await m.reply_text("📚 Send the <b>batch name</b>, or <code>d</code> to use the file name.")
        ans = await _ask(app, chat, 120)
        batch = batch_default if not ans or (ans.text or "").strip().lower() == "d" else ans.text.strip()

        # 4. resolution
        await m.reply_text("🎚️ Send the resolution: <code>144</code>, <code>240</code>, <code>360</code>, "
                           "<code>480</code>, <code>720</code> or <code>1080</code>.")
        ans = await _ask(app, chat, 120)
        height = E.resolution_height(ans.text if ans else "")

        # 5. credit
        await m.reply_text("✍️ Send your name for <b>Extracted By</b>, or <code>de</code> for the default.")
        ans = await _ask(app, chat, 120)
        credit = "" if not ans or (ans.text or "").strip().lower() == "de" else ans.text.strip()

        # 6. PW token (advance only)
        if opts.ask_token:
            await m.reply_text("🔑 Send the PW token for MPD URLs, or <code>unknown</code> for default.")
            ans = await _ask(app, chat, 120)
            _token = None if not ans or (ans.text or "").strip().lower() == "unknown" else ans.text.strip()

        # 7. thumbnail
        await m.reply_text("🖼️ Send a <b>thumbnail URL</b>, or <code>no</code> to take a frame from each video.")
        ans = await _ask(app, chat, 120)
        thumb_url = (ans.text or "").strip() if ans else "no"
        thumb = None
        if thumb_url.startswith(("http://", "https://")):
            thumb = await E.download_thumb(thumb_url, os.path.join(workdir, "thumb.jpg"))

        # Pin the batch name when starting from the first link (original behaviour)
        if start == 1:
            try:
                note = await client.send_message(chat, f"📌 <b>Batch:</b> {batch}")
                await client.pin_chat_message(chat, note.id)
            except Exception:
                pass

        status = await m.reply_text(f"⏳ Starting from <b>{start}</b> of <b>{len(items)}</b>…\n"
                                    "Send /stop to cancel.")
        done = failed = 0
        RUNNING[chat] = True
        stopped = False
        for i in range(start - 1, len(items)):
            if not RUNNING.get(chat):
                stopped = True
                break
            title, url = items[i]
            num = i + 1
            kind = E.classify(url)
            base = os.path.join(workdir, E.safe_filename(f"{num:03d}) {title[:60]}"))
            label = f"{num:03d}) {title[:60]}"
            await status.edit_text(f"⏳ {num}/{len(items)}  <code>{label}</code>")
            for attempt in (1, 2):
                try:
                    await _send_one(client, chat, kind, url, base, height, num, title, batch, credit, thumb)
                    done += 1
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except E.DownloadError as e:
                    failed += 1
                    await m.reply_text(f"❌ {label}\n<i>{e}</i>")
                    break
                except Exception as e:
                    if attempt == 2:
                        failed += 1
                        await m.reply_text(f"❌ {label}\n<i>{type(e).__name__}: {e}</i>")
            await asyncio.sleep(1)

        head = "🛑 Stopped" if stopped else "🔰 Done"
        await status.edit_text(f"{head}. Sent <b>{done}</b>, failed <b>{failed}</b>.")
    finally:
        RUNNING.pop(chat, None)
        shutil.rmtree(workdir, ignore_errors=True)


async def _send_one(client, chat, kind, url, base, height, num, title, batch, credit, thumb):
    if kind in ("video", "youtube", "m3u8"):
        out = await E.download_video(url, kind, base, height)
        if os.path.getsize(out) > E.MAX_UPLOAD_BYTES:
            os.remove(out)
            raise E.DownloadError("video is larger than Telegram's 2 GB limit")
        frame = None
        use_thumb = thumb or (frame := E.make_thumbnail(out))
        try:
            await client.send_video(
                chat, out, caption=E.caption("video", num, title, batch, credit),
                supports_streaming=True, duration=E.probe_duration(out), thumb=use_thumb)
        except Exception:
            await client.send_document(chat, out, caption=E.caption("video", num, title, batch, credit))
        finally:
            for p in (out, frame):
                if p and os.path.exists(p):
                    os.remove(p)
        return

    ext = {"pdf": ".pdf", "zip": ".zip", "html": ".html", "image": ".jpg"}.get(kind, "")
    if kind == "drive":
        ext = os.path.splitext(url.split("?")[0])[1] or ".bin"
    if kind == "image":
        ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    dest = base + ext
    path = await E.download_file(url, dest)
    try:
        cap = E.caption("pdf" if kind == "pdf" else "file", num, title, batch, credit)
        if kind == "image":
            await client.send_photo(chat, path, caption=cap)
        else:
            await client.send_document(chat, path, caption=cap)
    finally:
        if os.path.exists(path):
            os.remove(path)


@app.on_message(filters.command(["king", "upload"]))
async def king_mode(client, m: Message):
    await run_mode(client, m, MODES["king"])


@app.on_message(filters.command("bravo"))
async def bravo_mode(client, m: Message):
    await run_mode(client, m, MODES["bravo"])


@app.on_message(filters.command("spidy"))
async def spidy_mode(client, m: Message):
    await run_mode(client, m, MODES["spidy"])


@app.on_message(filters.command("advance"))
async def advance_mode(client, m: Message):
    await run_mode(client, m, MODES["advance"])


@app.on_message(filters.command("tushar"))
async def tushar_mode(client, m: Message):
    await run_mode(client, m, MODES["tushar"])


@app.on_message(filters.command("stop"))
async def stop_batch(client, m: Message):
    if not await is_allowed(m.from_user.id):
        return
    if request_stop(m.chat.id):
        await m.reply_text("🛑 Stopping after the current item…")
    else:
        await m.reply_text("Nothing is running in this chat.")


@app.on_message(filters.command("alpha"))
async def alpha_mode(client, m: Message):
    await run_mode(client, m, MODES["alpha"])
