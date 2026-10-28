"""Generic TXT -> download -> Telegram engine, shared by the TXT-TO-VIDEO modes (/king /bravo /spidy /advance /alpha).

Each line of the TXT is "Title:https://url". For every link the engine:
  * rewrites Google Drive and youtube-nocookie links to direct forms,
  * classifies the link (YouTube, m3u8, plain video, PDF, image, zip, HTML, Drive file),
  * downloads it with yt-dlp / ffmpeg / HTTP and sends it to the chat with a numbered caption.

Site-specific DRM and scraping branches of the original TXT-TO-VIDEO bot are NOT included here.
"""
import asyncio
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from urllib.parse import urlparse

import shutil
import time

import requests

COOKIES_FILE = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")
CREDIT = os.getenv("TXT_CREDIT", "Extractor")          # shown as "Extracted By"
BRAND = os.getenv("TXT_BRAND", "")                      # shown under each item, optional
ALLOWED_HEIGHTS = {"144": 144, "240": 240, "360": 360, "480": 480, "720": 720, "1080": 1080}
DEFAULT_HEIGHT = 480
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


@dataclass
class ModeOptions:
    name: str
    ask_token: bool = False       # /advance asks for a PW token
    show_counts: bool = False     # /tushar shows how many of each type before downloading


# ---------- parsing ----------

def clean_title(raw: str) -> str:
    """Same character clean-up the original bot applied to each title."""
    s = raw
    for ch in ("\t", ":", "/", "+", "#", "|", "@", "*", "."):
        s = s.replace(ch, "")
    s = s.replace("https", "").replace("http", "")
    return s.strip()


# Hosts whose links are wrapped: the real URL follows the prefix (original TXT-TO-VIDEO behaviour)
_WRAPPED_PREFIXES = (
    "https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/",
    "https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/",
)


def normalise_url(url: str) -> str:
    url = (url.replace("file/d/", "uc?export=download&id=")
              .replace("www.youtube-nocookie.com/embed", "youtu.be")
              .replace("?modestbranding=1", "")
              .replace("/view?usp=sharing", ""))
    # YouTube embed links with a playlist suffix -> plain embed of the single video
    if "?list" in url and "/embed/" in url:
        vid = url.split("/embed/", 1)[1].split("?", 1)[0]
        url = f"https://www.youtube.com/embed/{vid}"
    for prefix in _WRAPPED_PREFIXES:
        if url.startswith(prefix) and url[len(prefix):].startswith(("http://", "https://")):
            url = url[len(prefix):]
    return url


def parse_txt(text: str) -> list[tuple[str, str]]:
    """Return (title, url) pairs. Lines without '://' are skipped, like the original."""
    items = []
    for line in text.splitlines():
        if "://" not in line:
            continue
        head, tail = line.split("://", 1)
        title = clean_title(head) or "Untitled"
        url = normalise_url("https://" + tail.strip())
        items.append((title, url))
    return items


def classify(url: str) -> str:
    low = url.lower()
    path = urlparse(url).path.lower()
    ext = os.path.splitext(path)[1]
    if "drive.google.com" in low or "uc?export=download" in low:
        return "drive"
    if "youtu.be" in low or "youtube.com" in low:
        return "youtube"
    if ext == ".pdf" or ".pdf" in low:
        return "pdf"
    if ext in (".png", ".jpg", ".jpeg"):
        return "image"
    if ext == ".zip" or ".zip" in low:
        return "zip"
    if ext in (".html", ".htm"):
        return "html"
    if ".m3u8" in low:
        return "m3u8"
    return "video"


def resolution_height(text: str) -> int:
    return ALLOWED_HEIGHTS.get((text or "").strip(), DEFAULT_HEIGHT)


def safe_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]+", "", name).strip()[:90] or "file"


# ---------- commands ----------

def build_video_cmd(url: str, kind: str, out_base: str, height: int) -> str:
    """Shell command that writes out_base.mp4 (or .mkv/.webm, which the caller also checks)."""
    fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
    cookies = f"--cookies {shlex.quote(COOKIES_FILE)} " if os.path.exists(COOKIES_FILE) else ""
    if kind == "m3u8":
        return f'ffmpeg -y -i {shlex.quote(url)} -c copy -bsf:a aac_adtstoasc {shlex.quote(out_base + ".mp4")}'
    if kind == "youtube":
        return (f"yt-dlp {cookies}-f {shlex.quote(fmt)} --merge-output-format mp4 "
                f"{shlex.quote(url)} -o {shlex.quote(out_base + '.%(ext)s')}")
    headers = ""
    if "webvideos.classplusapp." in url:   # plain HLS needs the web-player referer
        headers = '--add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" '
    return (f"yt-dlp {headers}-f {shlex.quote(fmt)} --merge-output-format mp4 --no-warnings "
            f"{shlex.quote(url)} -o {shlex.quote(out_base + '.%(ext)s')}")


def find_output(out_base: str) -> str | None:
    for ext in (".mp4", ".mkv", ".webm", ".mp4.webm"):
        if os.path.isfile(out_base + ext):
            return out_base + ext
    return None


MAX_UPLOAD_BYTES = 2 * 1024 ** 3   # Telegram upload limit for bots
RETRIES = 3                         # total attempts per download
TIMEOUT_SECS = 3600


class DownloadError(Exception):
    """A download failed for a reason we can show to the user."""


def missing_tools() -> list[str]:
    """Binaries the engine needs. Empty list means everything is installed."""
    return [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None] + \
           ([] if shutil.which("yt-dlp") else ["yt-dlp"])


async def run_shell(cmd: str, timeout: int = TIMEOUT_SECS) -> tuple[int, str]:
    """Run a shell command. Returns (exit code, last useful line of stderr)."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, "timed out"
    lines = [l.strip() for l in err.decode(errors="ignore").splitlines() if l.strip()]
    return proc.returncode, (lines[-1] if lines else "")


async def download_video(url: str, kind: str, out_base: str, height: int, retries: int = RETRIES) -> str:
    """Download a video to out_base.<ext>. Retries with backoff. Raises DownloadError on failure."""
    tool = "ffmpeg" if kind == "m3u8" else "yt-dlp"
    if shutil.which(tool) is None:
        raise DownloadError(f"{tool} is not installed on the server")
    cmd = build_video_cmd(url, kind, out_base, height)
    last = ""
    for attempt in range(1, retries + 1):
        rc, tail = await run_shell(cmd)
        if rc == 0:
            out = find_output(out_base)
            if out:
                return out
            last = "tool finished but produced no file"
        else:
            last = tail or f"exit code {rc}"
        if attempt < retries:
            await asyncio.sleep(2 ** attempt)
    raise DownloadError(f"{tool} failed after {retries} tries: {last[:200]}")


def _http_get_to_file(url: str, dest: str, retries: int) -> None:
    headers = {"User-Agent": UA}
    last = ""
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(15, 120)) as r:
                if r.status_code != 200:
                    # 4xx will not fix itself on retry; 5xx might
                    if r.status_code < 500:
                        raise DownloadError(f"HTTP {r.status_code} for this link")
                    last = f"HTTP {r.status_code}"
                else:
                    size = int(r.headers.get("Content-Length") or 0)
                    if size and size > MAX_UPLOAD_BYTES:
                        raise DownloadError("file is larger than Telegram's 2 GB limit")
                    total = 0
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1 << 16):
                            total += len(chunk)
                            if total > MAX_UPLOAD_BYTES:
                                raise DownloadError("file is larger than Telegram's 2 GB limit")
                            f.write(chunk)
                    return
        except requests.RequestException as e:
            last = type(e).__name__
        if attempt < retries:
            time.sleep(2 ** attempt)
    raise DownloadError(f"download failed after {retries} tries: {last}")


async def download_file(url: str, dest: str, retries: int = RETRIES) -> str:
    """Download a plain file (PDF, zip, image, html, Drive file). Raises DownloadError on failure."""
    await asyncio.to_thread(_http_get_to_file, url, dest, retries)
    return dest


async def download_thumb(url: str, dest: str = "thumb.jpg") -> str | None:
    """Thumbnail from a URL, or None when the answer was not a URL (meaning 'no thumbnail')."""
    if not url.startswith(("http://", "https://")):
        return None
    try:
        return await download_file(url, dest, retries=2)
    except DownloadError:
        return None


# ---------- media helpers ----------

def probe_duration(path: str) -> int:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(float(out)) if out else 0
    except (subprocess.SubprocessError, ValueError, OSError):
        return 0


def make_thumbnail(video: str) -> str | None:
    """Grab a frame: at 12s like the original, falling back to 1s for shorter clips."""
    for ss in ("00:00:12", "00:00:01"):
        out = video + ".jpg"
        subprocess.run(["ffmpeg", "-y", "-ss", ss, "-i", video, "-vframes", "1", out],
                       capture_output=True, timeout=60)
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
    return None


# ---------- captions ----------

def caption(kind: str, num: int, title: str, batch: str, credit: str = "", extra: str = "") -> str:
    label = {"video": "VID_ID", "pdf": "PDF_ID"}.get(kind, "FILE_ID")
    icon = "🎞️" if kind == "video" else "📁"
    lines = [f"{icon} {label}: {num:03d}",
             f"📝 Title: {title}",
             f"📚 Batch Name: {batch}",
             f"📥 Extracted By : {credit or CREDIT}"]
    if extra:
        lines.insert(3, extra)
    if BRAND:
        lines.append(f"━━━━━✦{BRAND}✦━━━━━")
    return "\n\n".join(lines)
