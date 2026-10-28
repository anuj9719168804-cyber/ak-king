"""/selftest (owner only): checks the TXT engine on THIS server, live.

Runs: required binaries present; ffmpeg can make a video and the m3u8 download path works; the result is
uploaded to you as a Telegram video; optional YouTube and plain-file checks run only if their URLs are set:
  SELFTEST_YT_URL     a short public YouTube video (tests yt-dlp)
  SELFTEST_FILE_URL   a small public PDF or file (tests the HTTP download and document upload)
"""
import asyncio
import os
import shutil
import subprocess
import tempfile

from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from config import OWNER_ID
from Extractor.core import txt_engine as E


def _make_sample(path: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest",
         "-c:v", "libx264", "-c:a", "aac", path],
        capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.isfile(path)


@app.on_message(filters.command("selftest") & filters.user(OWNER_ID))
async def selftest(client, m: Message):
    status = await m.reply_text("🧪 Running self-test…")
    report = []
    workdir = tempfile.mkdtemp(prefix="selftest_")
    try:
        missing = E.missing_tools()
        report.append("✅ binaries present" if not missing else f"❌ missing: {', '.join(missing)}")

        if "ffmpeg" not in missing:
            src = os.path.join(workdir, "src.mp4")
            if await asyncio.to_thread(_make_sample, src):
                report.append("✅ ffmpeg can make a video")
                try:
                    out = await E.download_video(src, "m3u8", os.path.join(workdir, "hls"), 480)
                    dur = E.probe_duration(out)
                    report.append(f"✅ ffmpeg download path ({dur}s)")
                    await client.send_video(m.chat.id, out, caption="🧪 selftest: Telegram video upload",
                                            duration=dur, supports_streaming=True)
                    report.append("✅ Telegram video upload")
                except E.DownloadError as e:
                    report.append(f"❌ ffmpeg download path: {e}")
                except Exception as e:
                    report.append(f"❌ Telegram upload: {type(e).__name__}: {e}")
            else:
                report.append("❌ ffmpeg could not make a test video")

        yt = os.getenv("SELFTEST_YT_URL", "").strip()
        if not yt:
            report.append("➖ YouTube: set SELFTEST_YT_URL to test yt-dlp")
        elif "yt-dlp" in missing:
            report.append("❌ YouTube: yt-dlp is not installed")
        else:
            try:
                out = await E.download_video(yt, "youtube", os.path.join(workdir, "yt"), 144)
                report.append(f"✅ YouTube download ({E.probe_duration(out)}s)")
            except E.DownloadError as e:
                report.append(f"❌ YouTube: {e}")

        fu = os.getenv("SELFTEST_FILE_URL", "").strip()
        if not fu:
            report.append("➖ file download: set SELFTEST_FILE_URL to test HTTP download")
        else:
            try:
                dest = os.path.join(workdir, "file" + (os.path.splitext(fu.split("?")[0])[1] or ".bin"))
                path = await E.download_file(fu, dest)
                await client.send_document(m.chat.id, path, caption="🧪 selftest: document upload")
                report.append(f"✅ file download and document upload ({os.path.getsize(path)} bytes)")
            except E.DownloadError as e:
                report.append(f"❌ file download: {e}")
            except Exception as e:
                report.append(f"❌ document upload: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    await status.edit_text("🧪 <b>Self-test</b>\n" + "\n".join(report))
