"""
No-login sources ported from pw-pro-bot (vipstudy_bot_v22-1.py) into the Pyrogram Extractor.

Commands (premium / sudo / owner, same rule as the other tools):
  /nologin  : menu with all sources below
  /cwfree   : CareerWill (without login)
  /sw       : SelectionWay
  /iqfree   : Study IQ (without login)
  /kgsapp   : KGS App
  /una      : Unacademy (studyuk.site)
  /nt       : Next Toppers
  /rgmaxx   : RG Maxx (also /maxx)

Every source lists its batches (paged, with search where it makes sense), you tap one and
get back a .txt in the usual "Title:https://url" format, ready for /txt2video, /t2h etc.
"""
import asyncio
import html as _html
import os
import re
import shutil
import socket
import tempfile
import time
import urllib.parse
from datetime import datetime

import aiohttp
import pytz
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from pyrogram import StopPropagation, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Extractor import app
from Extractor.core import txt_engine as E
from Extractor.core.access import is_allowed
from Extractor.modules.txt2video import _send_one      # same download/upload path as /king, /txt2video
from config import PREMIUM_LOGS

# ───────────────────────── APIs (same endpoints as pw-pro-bot) ─────────────────────────
CW_ALL = "https://cw-ut-apia-9001c26847a7.herokuapp.com/api/batches"
CW_BATCH = "https://cw-api-website.vercel.app/batch/{}"
CW_TOPIC = "https://cw-api-website.vercel.app/batch?batchid={}&topicid={}&full=true"
CW_VIDEO = "https://cw-vid-virid.vercel.app/get_video_details?name={}"

SW_BASE = "https://raj-selectionwayapi.onrender.com"

IQ_VALID = "https://raw.githubusercontent.com/dev-raj009/Vipiq/refs/heads/main/valid_courses.json"
IQ_DETAILS = "https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={}&languageId={}"
IQ_DETAILS_P = "https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={}&languageId=&parentId={}"
IQ_LESSON = "https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={}&courseId={}"

KGS_BASE = "https://kgs-main-api-scamer.vercel.app"

UNA_BASE = "https://studyuk.site/offline/"
UNA_BATCHES = UNA_BASE + "batches.php"
UNA_DETAILS = UNA_BASE + "batch-details.php?batch_id={}"
UNA_LECTURES = UNA_BASE + "teacher-detail.php?batch_id={}&teacher={}"

NT_BASE = "https://nt-spidyuniverse.onrender.com/api"

RG_BASE = "https://rgmaxx-api.vercel.app/api"
RG_KEY, RG_IV = b"638udh3829162018", b"fedcba9876543210"          # Appx AES key used by the RG Maxx API
RG_PLAY = os.environ.get("RGMAXX_PLAY_BASE", "weathered-forest-6f0e.adityalkkumar4321.workers.dev/mp4")

PAGE = 10
IST = pytz.timezone("Asia/Kolkata")
_UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", "Accept": "application/json"}
_UA_HTML = {"User-Agent": _UA["User-Agent"], "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


# ───────────────────────── helpers ─────────────────────────
async def _get(session, url, *, headers=None, as_json=True, retries=3):
    """GET with retries. Returns parsed JSON (or text), or None when every try failed."""
    for i in range(retries):
        try:
            async with session.get(url, headers=headers or _UA, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    return await r.json(content_type=None) if as_json else await r.text()
                if r.status == 429:
                    await asyncio.sleep(2 ** i)
        except Exception:
            pass
        if i < retries - 1:
            await asyncio.sleep(0.5)
    return None


def _new_session(key=None):
    if key == "rg":
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(family=socket.AF_INET, ssl=False))
    return aiohttp.ClientSession()


def _t(s):
    """Title safe for the 'Title:url' format (no newlines, no '://')."""
    s = re.sub(r"\s+", " ", str(s or "")).strip().replace(":", " -")
    return re.sub(r"\s{2,}", " ", s) or "Untitled"


def _line(label, title, url):
    return f"[{_t(label)}] {_t(title)}:{str(url).strip()}"


def _safe_name(s, n=60):
    return re.sub(r'[\\/*?:"<>|\s]+', "_", str(s)).strip("_")[:n] or "batch"


def _bar(done, total):
    pct = int(done / max(total, 1) * 100)
    return "🟩" * (pct // 10) + "⬜" * (10 - pct // 10), pct


def _res(lines=None, v=0, p=0, fv=0, fp=0):
    return {"lines": lines or [], "v": v, "p": p, "fv": fv, "fp": fp}


def _merge(total, part):
    total["lines"].extend(part["lines"])
    for k in ("v", "p", "fv", "fp"):
        total[k] += part[k]


# ───────────────────────── CareerWill (no login) ─────────────────────────
async def cw_list(session):
    raw = await _get(session, CW_ALL)
    if not isinstance(raw, dict):
        return []
    items = [{"id": str(k), "title": str(v)} for k, v in raw.items()]
    items.sort(key=lambda x: int(x["id"]) if x["id"].isdigit() else 0, reverse=True)
    return items


async def _cw_video_url(session, video_id):
    data = await _get(session, CW_VIDEO.format(video_id))
    if not isinstance(data, dict):
        return None
    try:
        link = data["data"]["link"] if "data" in data and "link" in data["data"] else data.get("link")
        if isinstance(link, dict):
            return link.get("file_url") or link.get("url")
    except Exception:
        pass
    return None


async def _cw_topic(session, bid, topic, sem):
    tid, tname = topic.get("id"), topic.get("topicName", "Unknown")
    async with sem:
        data = await _get(session, CW_TOPIC.format(bid, tid))
    out = _res()
    if not isinstance(data, dict):
        return out
    classes = [c for c in data.get("classes", []) if c.get("video_url")]

    async def one(c):
        async with sem:
            return await _cw_video_url(session, c["video_url"])

    urls = await asyncio.gather(*[one(c) for c in classes])
    for c, u in zip(classes, urls):
        if u:
            out["lines"].append(_line(tname, f"Class {c.get('class_no', '?')} | {c.get('title', '?')}", u))
            out["v"] += 1
        else:
            out["fv"] += 1
    for n in data.get("notes", []):
        pdf = n.get("view_url") or n.get("download_url") or n.get("file_url") or n.get("pdf_url")
        if pdf:
            out["lines"].append(_line(tname, f"PDF | {n.get('title', '?')}", pdf))
            out["p"] += 1
        else:
            out["fp"] += 1
    return out


async def cw_extract(session, bid, bname, report):
    batch = await _get(session, CW_BATCH.format(bid))
    topics = (batch or {}).get("topics", []) if isinstance(batch, dict) else []
    if not topics:
        return _res()
    sem, total, done = asyncio.Semaphore(10), _res(), 0
    tasks = [asyncio.create_task(_cw_topic(session, bid, t, sem)) for t in topics]
    for fut in asyncio.as_completed(tasks):
        try:
            _merge(total, await fut)
        except Exception:
            pass
        done += 1
        await report(done, len(topics), total)
    return total


# ───────────────────────── SelectionWay ─────────────────────────
async def sw_list(session):
    data = await _get(session, f"{SW_BASE}/allbatch")
    if not isinstance(data, dict) or not data.get("success"):
        return []
    return [{"id": str(b.get("id", "")), "title": b.get("title", "Unknown")} for b in data.get("data", []) if b.get("id")]


async def _sw_topics(session, bid):
    """{topicName: result} for one SelectionWay batch (videos first, then PDFs, like the bot)."""
    ch, pd = await asyncio.gather(_get(session, f"{SW_BASE}/chapter/{bid}"), _get(session, f"{SW_BASE}/pdf/{bid}"))
    topics = {}
    if isinstance(ch, dict) and ch.get("success"):
        for t in ch.get("classes", []):
            tn = t.get("topicName", "?")
            out = topics.setdefault(tn, _res())
            for c in t.get("classes", []):
                if c.get("class_link"):
                    out["lines"].append(_line(tn, f"Video | {c.get('title', '?')}", c["class_link"]))
                    out["v"] += 1
                else:
                    out["fv"] += 1
    if isinstance(pd, dict) and pd.get("success"):
        for t in pd.get("topics", []):
            tn = t.get("topicName", "?")
            out = topics.setdefault(tn, _res())
            for f in t.get("pdfs", []):
                if f.get("uploadPdf"):
                    out["lines"].append(_line(tn, f"PDF | {f.get('title', '?')}", f["uploadPdf"]))
                    out["p"] += 1
                else:
                    out["fp"] += 1
    return topics


async def sw_extract(session, bid, bname, report):
    total = _res()
    for part in (await _sw_topics(session, bid)).values():
        _merge(total, part)
    await report(1, 1, total)
    return total


# ───────────────────────── Study IQ (no login) ─────────────────────────
async def iq_list(session):
    raw = await _get(session, IQ_VALID)
    if not isinstance(raw, list):
        return []
    return [{"id": str(b.get("id", "")), "title": b.get("title", "Unknown")} for b in raw if b.get("id") is not None]


async def _iq_items(session, items, label, bid, sem):
    out = _res()

    async def lesson(cid):
        async with sem:
            return await _get(session, IQ_LESSON.format(cid, bid))

    ids = [i.get("contentId") for i in items]
    notes = await asyncio.gather(*[lesson(c) if c else asyncio.sleep(0) for c in ids])
    for item, nr in zip(items, notes):
        if item.get("videoUrl"):
            out["lines"].append(_line(label, f"Video | {item.get('name', '?')}", item["videoUrl"]))
            out["v"] += 1
        if isinstance(nr, dict):
            for opt in nr.get("options") or []:
                for ud in opt.get("urls") or []:
                    if ud.get("name") and ud.get("url"):
                        out["lines"].append(_line(label, f"PDF | {ud['name']}", ud["url"]))
                        out["p"] += 1
    return out


async def iq_extract(session, bid, bname, report):
    master = await _get(session, IQ_DETAILS.format(bid, ""))
    topics = (master or {}).get("data") if isinstance(master, dict) else None
    if not topics:
        return _res()
    sem, total = asyncio.Semaphore(8), _res()
    for n, topic in enumerate(topics, 1):
        tid, tname = topic.get("contentId"), topic.get("name", "Unknown")
        pd = await _get(session, IQ_DETAILS_P.format(bid, tid))
        subs = (pd or {}).get("data") if isinstance(pd, dict) else None
        if subs:
            if not any(x.get("subFolderOrderId") is not None for x in subs):
                _merge(total, await _iq_items(session, subs, tname, bid, sem))
            else:
                for sub in subs:
                    vd = await _get(session, IQ_DETAILS_P.format(bid, f"{tid}/{sub.get('contentId')}"))
                    if isinstance(vd, dict) and vd.get("data"):
                        _merge(total, await _iq_items(session, vd["data"], f"{tname} > {sub.get('name', tname)}", bid, sem))
        await report(n, len(topics), total)
    return total


# ───────────────────────── KGS App ─────────────────────────
async def kgs_list(session):
    raw = await _get(session, f"{KGS_BASE}/get-courses")
    courses = raw.get("courses", []) if isinstance(raw, dict) else raw
    if not isinstance(courses, list):
        return []
    return [{"id": str(c.get("id", "")), "title": c.get("title", "Unknown")} for c in courses if c.get("id") is not None]


async def _kgs_subject(session, sem, subj):
    async with sem:
        lessons = await _get(session, f"{KGS_BASE}/lessons/{subj.get('id', '')}")
    out, sname = _res(), subj.get("name", "?")
    for les in lessons if isinstance(lessons, list) else []:
        lname = les.get("name", "?")
        if les.get("video_url"):
            out["lines"].append(_line(sname, f"Video | {lname}", les["video_url"]))
            out["v"] += 1
        else:
            out["fv"] += 1
        pdfs = les.get("pdfs")
        if isinstance(pdfs, dict):
            if pdfs.get("url"):
                out["lines"].append(_line(sname, f"PDF | {lname}", pdfs["url"]))
                out["p"] += 1
            else:
                out["fp"] += 1
    return out


async def kgs_extract(session, bid, bname, report):
    subjects = await _get(session, f"{KGS_BASE}/subjects/{bid}")
    if not isinstance(subjects, list):
        return _res()
    sem, total = asyncio.Semaphore(8), _res()
    tasks = [asyncio.create_task(_kgs_subject(session, sem, s)) for s in subjects]
    for n, fut in enumerate(asyncio.as_completed(tasks), 1):
        try:
            _merge(total, await fut)
        except Exception:
            pass
        await report(n, len(subjects), total)
    return total


# ───────────────────────── Unacademy (studyuk.site) ─────────────────────────
async def una_list(session):
    page = await _get(session, UNA_BATCHES, headers=_UA_HTML, as_json=False)
    if not page:
        return []
    soup, out = BeautifulSoup(page, "html.parser"), []
    for card in soup.select(".batch-card"):
        bid, name = card.get("data-batch-id", "").strip(), card.get("data-batch-name", "").strip()
        if bid and name:
            out.append({"id": bid, "title": name})
    return out


def _una_teachers(page):
    return [e.get_text(strip=True) for e in BeautifulSoup(page, "html.parser").select(".teacher-card .teacher-name") if e.get_text(strip=True)]


def _una_real_url(href):
    href = (href or "").strip()
    if "url=" in href:
        try:
            real = urllib.parse.parse_qs(href.split("?", 1)[1] if "?" in href else href).get("url", [""])[0]
            if real:
                return urllib.parse.unquote(real).strip()
        except Exception:
            pass
    return href


def _una_lectures(page):
    out = []
    for card in BeautifulSoup(page, "html.parser").select(".content-card"):
        h3, vb, pb = card.select_one("h3"), card.select_one(".video-btn"), card.select_one(".pdf-btn")
        pdf = pb.get("href", "").strip() if pb else ""
        if pdf and not pdf.startswith("http"):
            pdf = UNA_BASE + pdf.lstrip("/")
        out.append({"title": (h3.get_text(strip=True) if h3 else "") or "Untitled",
                    "video": _una_real_url(vb.get("href", "")) if vb else "", "pdf": pdf})
    return out


async def _una_teacher_list(session, bid):
    page = await _get(session, UNA_DETAILS.format(bid), headers={**_UA_HTML, "Referer": UNA_BATCHES}, as_json=False)
    return _una_teachers(page) if page else []


async def _una_teacher(session, bid, t):
    url = UNA_LECTURES.format(bid, urllib.parse.quote(t, safe=""))
    lp = await _get(session, url, headers={**_UA_HTML, "Referer": UNA_DETAILS.format(bid)}, as_json=False)
    out = _res()
    for lec in _una_lectures(lp) if lp else []:
        if lec["video"]:
            out["lines"].append(_line(t, f"Video | {lec['title']}", lec["video"]))
            out["v"] += 1
        else:
            out["fv"] += 1
        if lec["pdf"]:
            out["lines"].append(_line(t, f"PDF | {lec['title']}", lec["pdf"]))
            out["p"] += 1
    return out


async def una_extract(session, bid, bname, report):
    teachers, total = await _una_teacher_list(session, bid), _res()
    for n, t in enumerate(teachers, 1):
        _merge(total, await _una_teacher(session, bid, t))
        await report(n, len(teachers), total)
    return total


# ───────────────────────── Next Toppers ─────────────────────────
async def nt_list(session):
    raw = await _get(session, f"{NT_BASE}/batches")
    if not isinstance(raw, dict) or not raw.get("success"):
        return []
    return [{"id": str(b["batch_id"]), "title": b.get("title", "Unknown Batch")} for b in raw.get("data", []) if b.get("batch_id") is not None]


async def _nt_walk(session, folder_id, path, sem, depth=0):
    """Folder -> files (stream_url) and sub-folders, up to 5 levels (the bot only did 2)."""
    async with sem:
        raw = await _get(session, f"{NT_BASE}/folders/{folder_id}")
    out = _res()
    if not isinstance(raw, dict) or not raw.get("success"):
        return out
    subs = []
    for item in raw.get("data", []) or []:
        if item.get("type") == "file":
            url, title = item.get("stream_url", ""), item.get("title", "File")
            if not url:
                continue
            is_vid = ".m3u8" in url.lower()
            out["lines"].append(_line(" > ".join(path), f"{'Video' if is_vid else 'PDF'} | {title}", url))
            out["v" if is_vid else "p"] += 1
        elif item.get("folder_id") is not None and depth < 4:
            subs.append(asyncio.create_task(_nt_walk(session, item["folder_id"], path + [item.get("title", "Folder")], sem, depth + 1)))
    for part in await asyncio.gather(*subs):
        _merge(out, part)
    return out


async def _nt_subjects(session, bid):
    raw = await _get(session, f"{NT_BASE}/batches/{bid}")
    return ((raw or {}).get("data") or {}).get("subjects", []) if isinstance(raw, dict) else []


async def nt_extract(session, bid, bname, report):
    subjects = await _nt_subjects(session, bid)
    sem, total = asyncio.Semaphore(8), _res()
    for n, s in enumerate(subjects, 1):
        if s.get("subject_id") is not None:
            _merge(total, await _nt_walk(session, s["subject_id"], [s.get("subject_name", "Subject")], sem))
        await report(n, len(subjects), total)
    return total


# ───────────────────────── RG Maxx ─────────────────────────
def _rg_decrypt(text):
    """AES-128-CBC (hex or base64 input, PKCS7). Returns the input unchanged if it can't be decrypted."""
    if not text:
        return ""
    try:
        try:
            raw = bytes.fromhex(text)
        except ValueError:
            import base64
            raw = base64.b64decode(text)
        out = AES.new(RG_KEY, AES.MODE_CBC, RG_IV).decrypt(raw)
        if 1 <= out[-1] <= 16:
            out = out[:-out[-1]]
        return out.decode("utf-8", "ignore").strip()
    except Exception:
        return text


def _rg_batches(data):
    """Find the [{id, name}] list wherever the API nests it."""
    if isinstance(data, list):
        found = []
        for it in data:
            if isinstance(it, dict):
                bid = it.get("id") or it.get("courseid") or it.get("course_id")
                name = it.get("name") or it.get("batch_name") or it.get("course_name")
                if bid is not None and name is not None:
                    found.append({"id": str(bid), "title": str(name)})
        if found:
            return found
    if isinstance(data, dict):
        for v in data.values():
            r = _rg_batches(v)
            if r:
                return r
    return []


def _rg_list_of(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


async def rg_list(session):
    return _rg_batches(await _get(session, f"{RG_BASE}/all-batches"))


async def _rg_video(session, cid, sname, tname, video, sem):
    out = _res()
    vid = video.get("id") or video.get("video_id")
    name = video.get("name") or video.get("title") or video.get("video_name") or "Untitled"
    label = f"{sname} > {tname}"
    async with sem:
        det = await _get(session, f"{RG_BASE}/get-video-details?course_id={cid}&video_id={vid}")
    url = ""
    if isinstance(det, dict):
        enc_link, enc_key = det.get("encrypted_links") or det.get("link"), det.get("key")
        if isinstance(enc_link, str) and enc_link:
            dec = _rg_decrypt(enc_link)
            key = _rg_decrypt(str(enc_key)) if enc_key else ""
            if dec:
                url = f"https://{RG_PLAY}?key={key}&url={dec}"
    if url:
        out["lines"].append(_line(label, f"Video | {name}", url))
        out["v"] += 1
    else:
        out["fv"] += 1
    for n, k in ((1, ("pdf_link", "pdf1")), (2, ("pdf_link2", "pdf2"))):
        enc = next((video.get(x) for x in k if video.get(x)), "")
        pdf = _rg_decrypt(enc) if enc else ""
        if pdf:
            out["lines"].append(_line(label, f"PDF | {name} - Notes {n}", pdf))
            out["p"] += 1
    return out


async def _rg_subject(session, cid, subj, sem):
    out = _res()
    sid, sname = subj.get("id") or subj.get("subjectid"), subj.get("name") or subj.get("subject_name")
    if not sid or not sname:
        return out
    async with sem:
        topics = _rg_list_of(await _get(session, f"{RG_BASE}/get-topics?courseid={cid}&subjectid={sid}"))

    async def one_topic(t):
        tid, tname = t.get("id") or t.get("topicid"), t.get("name") or t.get("topic_name")
        if not tid or not tname:
            return _res()
        async with sem:
            videos = _rg_list_of(await _get(session, f"{RG_BASE}/get-videos?courseid={cid}&subjectid={sid}&topicid={tid}"))
        part = _res()
        for r in await asyncio.gather(*[_rg_video(session, cid, sname, tname, v, sem) for v in videos], return_exceptions=True):
            if isinstance(r, dict):
                _merge(part, r)
        return part

    for r in await asyncio.gather(*[one_topic(t) for t in topics], return_exceptions=True):
        if isinstance(r, dict):
            _merge(out, r)
    return out


async def _rg_subjects(session, cid):
    return _rg_list_of(await _get(session, f"{RG_BASE}/get-subjects?courseid={cid}"))


async def rg_extract(session, bid, bname, report):
    subjects = await _rg_subjects(session, bid)
    sem, total = asyncio.Semaphore(15), _res()
    tasks = [asyncio.create_task(_rg_subject(session, bid, s, sem)) for s in subjects]
    for n, fut in enumerate(asyncio.as_completed(tasks), 1):
        try:
            _merge(total, await fut)
        except Exception:
            pass
        await report(n, len(subjects), total)
    return total


async def rg_groups(session, bid):
    return [{"title": s.get("name") or s.get("subject_name") or "?", "raw": s} for s in await _rg_subjects(session, bid)
            if (s.get("id") or s.get("subjectid")) and (s.get("name") or s.get("subject_name"))]


async def rg_items(session, bid, g):
    return await _rg_subject(session, bid, g["raw"], asyncio.Semaphore(15))


# ───────────────────────── Study Mode data (batch -> group -> lectures) ─────────────────────────
async def cw_groups(session, bid):
    b = await _get(session, CW_BATCH.format(bid))
    topics = b.get("topics", []) if isinstance(b, dict) else []
    return [{"title": t.get("topicName", "Unknown"), "raw": t} for t in topics]


async def cw_items(session, bid, g):
    return await _cw_topic(session, bid, g["raw"], asyncio.Semaphore(10))


async def sw_groups(session, bid):
    return [{"title": n, "res": r} for n, r in (await _sw_topics(session, bid)).items()]


async def sw_items(session, bid, g):
    return g["res"]


async def kgs_groups(session, bid):
    subs = await _get(session, f"{KGS_BASE}/subjects/{bid}")
    return [{"title": s.get("name", "?"), "raw": s} for s in subs] if isinstance(subs, list) else []


async def kgs_items(session, bid, g):
    return await _kgs_subject(session, asyncio.Semaphore(8), g["raw"])


async def una_groups(session, bid):
    return [{"title": t} for t in await _una_teacher_list(session, bid)]


async def una_items(session, bid, g):
    return await _una_teacher(session, bid, g["title"])


async def nt_groups(session, bid):
    return [{"title": s.get("subject_name", "Subject"), "id": s["subject_id"]}
            for s in await _nt_subjects(session, bid) if s.get("subject_id") is not None]


async def nt_items(session, bid, g):
    return await _nt_walk(session, g["id"], [g["title"]], asyncio.Semaphore(8))


_LINE_RE = re.compile(r"^\[(.*?)\] (.*?):(https?://.*)$")
HEIGHTS = {"144": 144, "360": 360, "480": 480, "720": 720, "1080": 1080, "best": 2160}


def _items_from(res):
    """Turn extractor lines ('[label] Title:url') back into lecture dicts for the Study Mode list."""
    out = []
    for line in res["lines"]:
        m = _LINE_RE.match(line)
        if m:
            label, title, url = m.groups()
            out.append({"title": re.sub(r"^(Video|PDF) \| ", "", title), "label": label, "url": url, "pdf": title.startswith("PDF |")})
    return out


# ───────────────────────── registry ─────────────────────────
SRC = {
    "cw":  {"name": "CareerWill",          "emoji": "📚", "cmd": "cwfree", "list": cw_list,  "extract": cw_extract,  "search": True, "groups": cw_groups,  "items": cw_items},
    "sw":  {"name": "SelectionWay",        "emoji": "🏆", "cmd": "sw",     "list": sw_list,  "extract": sw_extract,  "search": True, "groups": sw_groups,  "items": sw_items},
    "iq":  {"name": "Study IQ (Free)",     "emoji": "📘", "cmd": "iqfree", "list": iq_list,  "extract": iq_extract,  "search": True},
    "kgs": {"name": "KGS App",             "emoji": "🎓", "cmd": "kgsapp", "list": kgs_list, "extract": kgs_extract, "search": True, "groups": kgs_groups, "items": kgs_items},
    "una": {"name": "Unacademy",           "emoji": "🟢", "cmd": "una",    "list": una_list, "extract": una_extract, "search": True, "groups": una_groups, "items": una_items},
    "nt":  {"name": "Next Toppers",        "emoji": "🚀", "cmd": "nt",     "list": nt_list,  "extract": nt_extract,  "search": True, "groups": nt_groups,  "items": nt_items},
    "rg":  {"name": "RG Maxx",             "emoji": "💎", "cmd": "rgmaxx", "list": rg_list,  "extract": rg_extract,  "search": True, "groups": rg_groups,  "items": rg_items, "html": True},
}
CMD_TO_KEY = {v["cmd"]: k for k, v in SRC.items()}
CMD_TO_KEY["maxx"] = "rg"       # the original RG Maxx bot used /maxx
STUDY_KEYS = [k for k, v in SRC.items() if v.get("groups")]
_STUDY = {}       # (uid, key) -> {"batch", "groups", "gi", "items", "ts"}

_CACHE = {}      # (uid, key) -> {"all": [...], "view": [...], "ts": float}
_RUNNING = set()  # uids with an extraction in progress
CACHE_TTL = 1800
NOT_ALLOWED = "🚫 This tool is for premium users. Contact the owner."


def _menu_kb():
    keys = list(SRC)
    rows = [[InlineKeyboardButton(f"{SRC[k]['emoji']} {SRC[k]['name']}", callback_data=f"nlx|{k}|open") for k in keys[i:i + 2]]
            for i in range(0, len(keys), 2)]
    rows.append([InlineKeyboardButton("📖 Study Mode (video download + upload)", callback_data="nlx|smenu")])
    rows.append([InlineKeyboardButton("𝐁 𝐀 𝐂 𝐊", callback_data="custom_")])
    return InlineKeyboardMarkup(rows)


def _study_menu_kb():
    rows = [[InlineKeyboardButton(f"{SRC[k]['emoji']} {SRC[k]['name']}", callback_data=f"nlx|{k}|sopen") for k in STUDY_KEYS[i:i + 2]]
            for i in range(0, len(STUDY_KEYS), 2)]
    rows.append([InlineKeyboardButton("🔙 Sources", callback_data="nlx|menu")])
    return InlineKeyboardMarkup(rows)


def _list_kb(key, view, page, study=False):
    tp, s, rows = max(1, (len(view) + PAGE - 1) // PAGE), page * PAGE, []
    for i in range(s, min(s + PAGE, len(view))):
        t = view[i]["title"]
        rows.append([InlineKeyboardButton(f"{SRC[key]['emoji']} {t[:46] + '…' if len(t) > 46 else t}", callback_data=f"nlx|{key}|{'st' if study else 'ex'}|{i}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nlx|{key}|pg|{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{tp}", callback_data="nlx|noop"))
    if s + PAGE < len(view):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"nlx|{key}|pg|{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🔍 Search", callback_data=f"nlx|{key}|search"),
                 InlineKeyboardButton("🔙 Back", callback_data="nlx|smenu" if study else "nlx|menu")])
    return InlineKeyboardMarkup(rows)


def _list_text(key, view, page, query=None, study=False):
    tp = max(1, (len(view) + PAGE - 1) // PAGE)
    head = f"{'📖 Study — ' if study else ''}{SRC[key]['emoji']} <b>{SRC[key]['name']}</b>"
    if query:
        head += f" — 🔍 <code>{_html.escape(query)}</code>"
    return f"{head}\n\n📦 Batches: <code>{len(view)}</code> | 📄 <code>{page + 1}/{tp}</code>\n\n<i>Tap a batch to {'study' if study else 'extract'} 👇</i>"


async def _edit(msg, text, markup=None):
    try:
        await msg.edit_text(text, reply_markup=markup)
    except Exception:
        pass


async def _open_source(message, uid, key, edit=False, study=False):
    """Fetch the batch list for `key` and show page 0. `message` is where the list is shown."""
    if not await is_allowed(uid):
        await message.reply_text(NOT_ALLOWED)
        return
    src = SRC[key]
    note = await (message.edit_text if edit else message.reply_text)(f"⏳ <b>{src['name']}</b> batches load ho rahe hain...")
    async with _new_session(key) as session:
        try:
            batches = await src["list"](session)
        except Exception:
            batches = []
    if not batches:
        await _edit(note, f"❌ <b>{src['name']}</b>: batch list nahi mili (API down ho sakti hai). Thodi der baad try karo.")
        return
    _CACHE[(uid, key)] = {"all": batches, "view": batches, "ts": time.time(), "study": study}
    await _edit(note, _list_text(key, batches, 0, study=study), _list_kb(key, batches, 0, study))


def _cache(uid, key):
    c = _CACHE.get((uid, key))
    return c if c and time.time() - c["ts"] < CACHE_TTL else None


async def _send_result(message, key, bid, bname, res, t0):
    src, lines = SRC[key], res["lines"]
    path = os.path.join(tempfile.gettempdir(), f"{_safe_name(bname)}_{key}_{int(time.time())}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    el = time.time() - t0
    me = (await app.get_me()).username
    caption = (
        f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
        f"📱 <b>APP:</b> {src['name']}\n"
        f"📚 <b>BATCH:</b> {_html.escape(bname)} (ID: {_html.escape(str(bid))})\n"
        f"⏱ <b>EXTRACTION TIME:</b> {int(el // 60):02d}:{int(el % 60):02d}\n"
        f"📅 <b>DATE:</b> {datetime.now(IST).strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
        f"📊 <b>CONTENT STATS</b>\n"
        f"├─ 📁 Total Links: {len(lines)}\n"
        f"├─ 🎬 Videos: {res['v']}\n"
        f"├─ 📄 PDFs: {res['p']}\n"
        f"└─ ⚠️ Not available: {res['fv'] + res['fp']}\n\n"
        f"🚀 <b>Extracted by:</b> @{me}\n\n"
        f"<code>╾───• A K  Extractor Pro •───╼</code>"
    )
    html_path = None
    if src.get("html"):
        try:
            from Extractor.html_converter.bot import categorize_urls, extract_names_and_urls, generate_html
            videos, pdfs, others = categorize_urls(extract_names_and_urls("\n".join(lines)))
            html_path = path[:-4] + ".html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(generate_html(os.path.basename(path), videos, pdfs, others))
        except Exception:
            html_path = None
    try:
        await message.reply_document(document=path, caption=caption)
        if html_path:
            await message.reply_document(document=html_path, caption="✨ <b>HTML player</b> (videos + PDFs, dark UI)")
        try:
            await app.send_document(PREMIUM_LOGS, path, caption=caption)
            if html_path:
                await app.send_document(PREMIUM_LOGS, html_path, caption=caption)
        except Exception:
            pass
    finally:
        for fp in (path, html_path):
            try:
                if fp:
                    os.remove(fp)
            except OSError:
                pass


async def _do_extract(message, uid, key, item):
    if uid in _RUNNING:
        await message.reply_text("⏳ Ek extraction already chal raha hai. Pehle usko khatam hone do.")
        return
    src, bid, bname = SRC[key], item["id"], item["title"]
    _RUNNING.add(uid)
    prog = await message.reply_text(f"✅ <b>Batch Selected</b>\n\n📌 <b>{_html.escape(bname)}</b>\n\n⚙️ Extracting...")
    t0, last = time.time(), [0.0]

    async def report(done, total, cur):
        now = time.time()
        if done < total and now - last[0] < 4:
            return
        last[0] = now
        bar, pct = _bar(done, total)
        await _edit(prog, f"⚙️ <b>{src['name']} — {_html.escape(bname)}</b>\n\n{bar} <code>{pct}%</code>\n\n"
                          f"📁 <code>{done}/{total}</code>\n🎬 <code>{cur['v']}</code> | 📄 <code>{cur['p']}</code>\n"
                          f"📦 <code>{len(cur['lines'])}</code> | ⏱ <code>{now - t0:.0f}s</code>")

    try:
        async with _new_session(key) as session:
            res = await src["extract"](session, bid, bname, report)
        if not res["lines"]:
            await _edit(prog, "❌ Koi content nahi mila (batch khaali hai ya API ne response nahi diya).")
            return
        await _send_result(message, key, bid, bname, res, t0)
        try:
            await prog.delete()
        except Exception:
            pass
    except Exception as e:
        await _edit(prog, f"❌ <b>Error:</b> <code>{_html.escape(str(e)[:200])}</code>")
    finally:
        _RUNNING.discard(uid)


# ───────────────────────── Study Mode UI ─────────────────────────
def _paged_kb(rows_src, page, cb_item, cb_page, back_row, per=PAGE):
    tp, s, rows = max(1, (len(rows_src) + per - 1) // per), page * per, []
    for i in range(s, min(s + per, len(rows_src))):
        rows.append([InlineKeyboardButton(rows_src[i][:56], callback_data=cb_item.format(i))])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=cb_page.format(page - 1)))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{tp}", callback_data="nlx|noop"))
    if s + per < len(rows_src):
        nav.append(InlineKeyboardButton("➡️", callback_data=cb_page.format(page + 1)))
    rows.append(nav)
    rows.append(back_row)
    return InlineKeyboardMarkup(rows)


def _study_state(uid, key):
    st = _STUDY.get((uid, key))
    return st if st and time.time() - st["ts"] < CACHE_TTL else None


async def _show_groups(msg, key, st, page):
    labels = [f"📂 {g['title']}" for g in st["groups"]]
    kb = _paged_kb(labels, page, f"nlx|{key}|sg|{{}}", f"nlx|{key}|gp|{{}}",
                   [InlineKeyboardButton("🔙 Batches", callback_data=f"nlx|{key}|sopen")])
    await _edit(msg, f"📖 <b>{_html.escape(st['batch']['title'])}</b>\n\n📂 <code>{len(st['groups'])}</code> topics/teachers\n\n<i>Choose karo 👇</i>", kb)


async def _show_items(msg, key, st, page):
    g = st["groups"][st["gi"]]
    labels = [f"{'📄' if it['pdf'] else '🎬'} {it['title']}" for it in st["items"]]
    kb = _paged_kb(labels, page, f"nlx|{key}|si|{{}}", f"nlx|{key}|ip|{{}}",
                   [InlineKeyboardButton("🔙 Topics", callback_data=f"nlx|{key}|sb")])
    await _edit(msg, f"📂 <b>{_html.escape(g['title'])}</b>\n\n🎬 <code>{len(st['items'])}</code> items\n\n<i>Choose karo 👇</i>", kb)


async def _study_download(message, uid, st, item, num, quality):
    if uid in _RUNNING:
        await message.reply_text("⏳ Ek download/extraction already chal raha hai. Pehle usko khatam hone do.")
        return
    if not item["pdf"]:
        missing = E.missing_tools()
        if missing:
            await message.reply_text("⚠️ Server pe ye tools nahi hain: <code>" + ", ".join(missing) + "</code>. Admin se install karwao.")
            return
    _RUNNING.add(uid)
    workdir = tempfile.mkdtemp(prefix="study_")
    status = await message.reply_text(f"⏳ <b>{_html.escape(item['title'])}</b>\n\nDownload ho raha hai...")
    try:
        kind = E.classify(item["url"])
        base = os.path.join(workdir, E.safe_filename(f"{num:03d}) {item['title'][:60]}"))
        await _send_one(app, message.chat.id, kind, item["url"], base, HEIGHTS.get(quality, 720), num,
                        item["title"], st["batch"]["title"], "", None)
        try:
            await status.delete()
        except Exception:
            pass
    except E.DownloadError as e:
        await _edit(status, f"❌ <i>{_html.escape(str(e)[:300])}</i>")
    except Exception as e:
        await _edit(status, f"❌ <code>{type(e).__name__}: {_html.escape(str(e)[:200])}</code>")
    finally:
        _RUNNING.discard(uid)
        shutil.rmtree(workdir, ignore_errors=True)


async def _study_inner(q, uid, key, action, parts):
    src, st = SRC[key], _study_state(uid, key)
    if action == "sopen":
        await _open_source(q.message, uid, key, edit=True, study=True)
        return
    if action == "st":                                   # batch chosen -> list its topics/teachers
        c = _cache(uid, key)
        i = int(parts[3])
        if not c or not 0 <= i < len(c["view"]):
            await _open_source(q.message, uid, key, edit=True, study=True)
            return
        batch = c["view"][i]
        await _edit(q.message, f"⏳ <b>{_html.escape(batch['title'])}</b>\n\nTopics load ho rahe hain...")
        async with _new_session(key) as session:
            groups = await src["groups"](session, batch["id"])
        if not groups:
            await _edit(q.message, "❌ Is batch mein koi topic nahi mila.", _list_kb(key, c["view"], 0, True))
            return
        st = _STUDY[(uid, key)] = {"batch": batch, "groups": groups, "gi": 0, "items": [], "ts": time.time()}
        await _show_groups(q.message, key, st, 0)
        return
    if not st:
        await _edit(q.message, "⌛ Session expire ho gaya. Dubara shuru karo 👇", _study_menu_kb())
        return
    if action == "gp":
        await _show_groups(q.message, key, st, int(parts[3]))
    elif action == "sb":
        await _show_groups(q.message, key, st, 0)
    elif action == "sg":                                 # topic chosen -> list its lectures
        j = int(parts[3])
        if not 0 <= j < len(st["groups"]):
            return
        await _edit(q.message, f"⏳ <b>{_html.escape(st['groups'][j]['title'])}</b>\n\nLectures load ho rahe hain...")
        async with _new_session(key) as session:
            res = await src["items"](session, st["batch"]["id"], st["groups"][j])
        items = _items_from(res)
        if not items:
            await _show_groups(q.message, key, st, 0)
            await q.message.reply_text("⚠️ Is topic mein koi lecture nahi mila.")
            return
        st["gi"], st["items"], st["ts"] = j, items, time.time()
        await _show_items(q.message, key, st, 0)
    elif action == "ip":
        await _show_items(q.message, key, st, int(parts[3]))
    elif action in ("si", "sd", "sl", "sq"):
        k = int(parts[3])
        if not 0 <= k < len(st["items"]):
            return
        item = st["items"][k]
        back = InlineKeyboardButton("🔙 Back", callback_data=f"nlx|{key}|ip|{k // PAGE}")
        if action == "si":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Download & Upload", callback_data=f"nlx|{key}|{'sq' if item['pdf'] else 'sd'}|{k}" + ("|best" if item["pdf"] else ""))],
                [InlineKeyboardButton("🔗 Sirf Link", callback_data=f"nlx|{key}|sl|{k}")],
                [back]])
            g = st["groups"][st["gi"]]
            await _edit(q.message, f"{'📄' if item['pdf'] else '🎬'} <b>{_html.escape(item['title'])}</b>\n\n"
                                   f"📂 {_html.escape(g['title'])}\n📚 {_html.escape(st['batch']['title'])}\n\n<i>Kya karna hai? 👇</i>", kb)
        elif action == "sd":
            qs = [("🎯 144p (Smallest)", "144"), ("📱 360p (Low)", "360"), ("📺 480p (Medium)", "480"),
                  ("🔥 720p (HD)", "720"), ("💎 1080p (Full HD)", "1080"), ("⚡ Best (Auto)", "best")]
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=f"nlx|{key}|sq|{k}|{v}")] for t, v in qs]
                                      + [[InlineKeyboardButton("🔙 Back", callback_data=f"nlx|{key}|si|{k}")]])
            await _edit(q.message, f"🎬 <b>{_html.escape(item['title'])}</b>\n\n<b>Quality choose karo 👇</b>", kb)
        elif action == "sl":
            await q.message.reply_text(f"🔗 <b>Link:</b>\n\n<code>{_html.escape(item['url'])}</code>")
        else:
            await _study_download(q.message, uid, st, item, k + 1, parts[4] if len(parts) > 4 else "720")


# ───────────────────────── handlers ─────────────────────────
@app.on_message(filters.command(list(CMD_TO_KEY)) & filters.private, group=-1)
async def nlx_cmd(client, m):
    if not m.from_user:
        return
    await _open_source(m, m.from_user.id, CMD_TO_KEY[m.command[0].lower()])


@app.on_message(filters.command("study") & filters.private, group=-1)
async def nlx_study_cmd(client, m):
    if not m.from_user:
        return
    if not await is_allowed(m.from_user.id):
        await m.reply_text(NOT_ALLOWED)
        return
    await m.reply_text("📖 <b>Study Mode</b>\n\nBatch browse karo, lecture chuno, aur seedha yahin download + upload karo.\n\n<i>Source choose karo 👇</i>",
                       reply_markup=_study_menu_kb())


@app.on_message(filters.command(["nologin", "nlx"]) & filters.private, group=-1)
async def nlx_menu_cmd(client, m):
    if not m.from_user:
        return
    if not await is_allowed(m.from_user.id):
        await m.reply_text(NOT_ALLOWED)
        return
    await m.reply_text("🔏 <b>Without Login Sources</b>\n\n<i>Source choose karo 👇</i>", reply_markup=_menu_kb())


async def _nlx_inner(q, uid, parts):
    if parts[1] == "noop":
        return
    if parts[1] == "menu":
        if not await is_allowed(uid):
            await q.message.reply_text(NOT_ALLOWED)
        else:
            await _edit(q.message, "🔏 <b>Without Login Sources</b>\n\n<i>Source choose karo 👇</i>", _menu_kb())
        return
    if parts[1] == "smenu":
        if not await is_allowed(uid):
            await q.message.reply_text(NOT_ALLOWED)
        else:
            await _edit(q.message, "📖 <b>Study Mode</b>\n\nBatch browse karo, lecture chuno, aur seedha yahin download + upload karo.\n\n<i>Source choose karo 👇</i>", _study_menu_kb())
        return
    key, action = parts[1], parts[2]
    if key not in SRC:
        return
    if not await is_allowed(uid):
        await q.message.reply_text(NOT_ALLOWED)
        return
    if action in ("sopen", "st", "gp", "sb", "sg", "ip", "si", "sd", "sl", "sq"):
        if key in STUDY_KEYS:
            await _study_inner(q, uid, key, action, parts)
        return
    if action == "open":
        await _open_source(q.message, uid, key, edit=True)
        return
    c = _cache(uid, key)
    if not c:
        await _open_source(q.message, uid, key, edit=True)
        return
    if action == "pg":
        page = int(parts[3])
        await _edit(q.message, _list_text(key, c["view"], page, c.get("query"), c.get("study", False)), _list_kb(key, c["view"], page, c.get("study", False)))
    elif action == "ex":
        i = int(parts[3])
        if 0 <= i < len(c["view"]):
            await _do_extract(q.message, uid, key, c["view"][i])
    elif action == "search":
        ask = await q.message.reply_text("🔍 <b>Search</b>\n\nKeyword bhejo (2 min mein). <code>/cancel</code> se band karo.")
        try:
            resp = await app.listen(chat_id=q.message.chat.id, timeout=120)
        except Exception:
            resp = None
        if not resp or not resp.text or resp.text.startswith("/"):
            await _edit(ask, "Search band.")
            return
        kw = resp.text.strip().lower()
        view = [b for b in c["all"] if kw in b["title"].lower()]
        if not view:
            await _edit(ask, f"❌ <code>{_html.escape(kw)}</code> nahi mila.")
            return
        c["view"], c["query"] = view, kw
        await _edit(ask, _list_text(key, view, 0, kw, c.get("study", False)), _list_kb(key, view, 0, c.get("study", False)))


@app.on_callback_query(filters.regex(r"^nlx\|"), group=-1)
async def nlx_cb(client, q):
    """Always ends in StopPropagation so start.py's catch-all callback handler never sees nlx| buttons."""
    try:
        await q.answer()
        await _nlx_inner(q, q.from_user.id, q.data.split("|"))
    except StopPropagation:
        raise
    except Exception as e:
        try:
            await q.message.reply_text(f"❌ <code>{_html.escape(str(e)[:150])}</code>")
        except Exception:
            pass
    finally:
        raise StopPropagation
