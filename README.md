<div align="center">

# 📚 AK EXTRACTOR BOT

**All-in-one Telegram bot: extract course link lists, convert TXT ⇄ HTML, download and upload to Telegram.**

Version **3.1 (fixed)** · Python 3.10 · Pyrogram 2 · MongoDB · Docker-ready

</div>

---

## 📑 Table of Contents
1. [What is this?](#-what-is-this)
2. [Features](#-features)
3. [Supported sources](#-supported-sources)
4. [Command reference](#-command-reference)
5. [Project structure](#-project-structure)
6. [How it works](#-how-it-works)
7. [Requirements](#-requirements)
8. [Configuration (environment variables)](#-configuration-environment-variables)
9. [Deployment](#-deployment)
10. [TXT file format](#-txt-file-format)
11. [Access control & premium](#-access-control--premium)
12. [Adding a new module](#-adding-a-new-module)
13. [Troubleshooting](#-troubleshooting)
14. [Security notes](#-security-notes)
15. [Changelog](#-changelog)
16. [Disclaimer & credits](#-disclaimer--credits)

---

## 🔎 What is this?

A single Telegram bot built by merging several earlier projects (Extractor, vikas-bot, Saini-1, newbot, pw-pro-bot).
It logs in to supported learning apps (with the user's own credentials/token), lists batches and lectures,
writes them to a `.txt` file, and can then download the links and upload them to Telegram.
It also ships TXT ⇄ HTML converters, a YouTube playlist exporter, premium plans and an owner/sudo admin panel.

---

## ✨ Features

| Area | What you get |
|---|---|
| **Extractors** | Many learning-app extractors producing `Title:URL` `.txt` files (+ optional HTML player) |
| **No-login sources** | `/nologin`, `/study` browse-and-download mode |
| **TXT tools** | `/t2t`, `/e2t`, `/t2h`, `/txt2html`, `/html2txt`, `/enc`, `/dec` |
| **YouTube** | `/y2t` playlist/video to `.txt`, `/ytm` music download, cookie management |
| **TXT → Telegram** | `/king` (`/upload`), `/bravo`, `/spidy`, `/advance`, `/alpha`, `/tushar`, `/Txt` + `/stop` |
| **DB channel upload** | `/setdb`, `/dbupload`, `/dbinfo`, `/dbstop` (auto-post extracted batches as .txt in a channel) |
| **Plans** | Premium users with expiry (MongoDB), sudo list, force-join channel |
| **Admin** | broadcast, stats, logs, restart, eval/shell (owner only), selftest |
| **Hosting** | Dockerfile, Heroku (`heroku.yml`), Render, local; Flask keep-alive endpoint |

---

## 🎓 Supported sources

| Source | Command(s) | Module |
|---|---|---|
| PhysicsWallah | `/pw` | `pw.py`, `freepw.py` |
| Appx (v1 / v2 / v3 / v4, OTP, zip) | `/apiv1`, `/appx`, `/appxm`, `/appxotp` | `appex_v1-4.py`, `freeappx.py`, `getappxotp.py` |
| Classplus | `/cp`, `/extract` | `classplus.py`, `freecp.py` |
| CareerWill | `/cw`, `/ugcw` | `careerwill.py` |
| Utkarsh | `/utk`, `/utkarsh`, `/utk_dl` | `utk.py` |
| StudyIQ | `/iq` | `iq.py` |
| KD Campus / KD Live | `/kd` | `kdlive.py` |
| Khan GS, Exampur, Vision IAS, Adda247, MyPathshala | `/adda`, `/my`, … | `khan.py`, `exampur.py`, `vision.py`, `adda.py`, `mypathshala.py` |
| RG Vikramjeet | `/rgvikramjeet` | `rg_vikramjeet.py` |
| Others | `/ak`, `/imjadu2` | `ak.py`, `check.py`, `mix.py` |
| No-login: CareerWill, SelectionWay, Study IQ, KGS App, Unacademy, Next Toppers, RG Maxx | `/nologin`, `/nlx`, `/study`, `/cwfree`, `/sw`, `/iqfree`, `/kgsapp`, `/una`, `/nt`, `/rgmaxx` | `nlx_sources.py` |

> `amansir.py` is a **placeholder** (not implemented yet).
> Send `/apps` in the bot for the live list. Availability of each source depends on the platform's own API.

---

## 🧭 Command reference

### 👤 Everyone
| Command | Description |
|---|---|
| `/start` | Welcome menu (Commands / Features / Settings / Subscription) |
| `/help`, `/apps` | Command list, supported sources |
| `/id`, `/info` | Chat id, your Telegram details |
| `/myplan` | Check your premium plan |
| `/t2t` | Text → `.txt` file with a chosen name |
| `/e2t` | Tidy a `.txt` of `Title:link` lines |
| `/y2t`, `/yt2txt` | YouTube video/playlist → `.txt` |
| `/t2h`, `/txt2html`, `/html2txt` | TXT ⇄ HTML conversion |
| `/getapi` | Find an Appx API by name |

### 💎 Premium / sudo (needs an unexpired plan)
| Command | Description |
|---|---|
| `/pw`, `/cp`, `/utk`, `/iq`, `/appx`, … | Source extractors (see table above) |
| `/king` (`/upload`), `/bravo`, `/spidy`, `/alpha` | Send a `.txt`, bot downloads & uploads every link |
| `/advance` | Same, with a PW token prompt |
| `/tushar` | Show counts by link type, then download |
| `/nologin`, `/study` | No-login sources / Study Mode |
| `/enc`, `/dec`, `/enchelp` | Encrypt / decrypt helper |
| `/stop` | Cancel the running batch in this chat |

### 🛠️ Sudo
| Command | Description |
|---|---|
| `/extract`, `/cw`, `/ugcw` | Classplus / CareerWill batch extract |
| `/dbupload cw\|kgs`, `/dbstop`, `/dbinfo` | Database-channel auto-upload |
| `/addauth`, `/rmauth`, `/users` | Manage authorised users |
| `/add_premium`, `/remove_premium`, `/chk_premium`, `/premium_users` | Manage plans |
| `/stats` | Bot statistics |

### 👑 Owner only
| Command | Description |
|---|---|
| `/sudo add\|remove USER_ID`, `/userlist` | Manage sudo users |
| `/setdb cw\|kgs CHANNEL_ID` | Set database channel |
| `/broadcast`, `/announce`, `/forward` | Message all users |
| `/cookies`, `/getcookies` | Upload / download YouTube cookies |
| `/logs`, `/reset`, `/restart`, `/selftest` | Logs, reset state, restart, server self-test |
| `/eval`, `/x`, `/sh` | Run Python / shell (**dangerous**, owner only) |

---

## 🗂️ Project structure

```
FINAL_EXTRACTOR_COMPLETE/
├── Extractor/
│   ├── __init__.py            # creates the single shared Pyrogram Client (`app`)
│   ├── __main__.py            # entry: python -m Extractor (imports every module, graceful shutdown)
│   ├── modules/               # one file per feature (auto-imported)
│   │   ├── start.py, help_apps.py, commands.py, features.py, settings.py, upgrade.py   # menus & UI
│   │   ├── pw.py, freepw.py, classplus.py, freecp.py, appex_v1..v4.py, freeappx.py,
│   │   │   careerwill.py, utk.py, iq.py, kdlive.py, khan.py, exampur.py, vision.py,
│   │   │   adda.py, mypathshala.py, rg_vikramjeet.py, ak.py, mix.py, check.py        # extractors
│   │   ├── nlx_sources.py, nlx_dbupload.py                                              # no-login + DB upload
│   │   ├── txt2video.py, newbot_upload.py, drm_handler.py, saini*.py                    # TXT → Telegram uploaders
│   │   ├── txt2txt.py, e2t.py, html_handler.py, ytlinks.py, youtube_handler.py, enc.py # TXT / YouTube tools
│   │   ├── plans.py, premium.py, sudo.py, authorisation.py, aliases.py                  # access & plans
│   │   └── broadcast.py, stats.py, logs.py, restart.py, eval.py, cookies.py, selftest.py, userinfo.py  # admin
│   ├── core/
│   │   ├── mongo/             # plans_db (premium), usersdb
│   │   ├── txt_engine.py      # generic TXT → download → Telegram engine
│   │   ├── access.py          # is_allowed(): owner/sudo/premium check
│   │   ├── sudo_store.py      # sudo list (JSON file)
│   │   ├── func.py, utils.py, script.py, newbot_core.py, template.html
│   ├── html_converter/        # TXT ⇄ HTML (bot.py, botenc.py)
│   └── thumbs/                # default thumbnails
├── config.py                  # ALL settings, from environment variables
├── app.py                     # Flask keep-alive (gunicorn app:app)
├── run.py                     # local runner: web app + bot
├── secure.py, server.py, one.py   # helper scripts (one.py = code obfuscator for utk.py)
├── Dockerfile, heroku.yml, Procfile, app.json, runtime.txt
├── appxapis.json              # Appx API list
├── requirements.txt, .env.example, .gitignore
├── MANIFEST.json, CHANGES.md, README.md
├── masterdl.so, vidwater.ttf  # binary helper / watermark font
└── extras/                    # reference code from the source bots (NOT loaded by the bot)
```

---

## ⚙️ How it works

```
python -m Extractor
   │
   ├─ Extractor/__init__.py   → creates `app` (Pyrogram Client, pyromod listen)
   ├─ __main__.py             → imports every file in Extractor/modules (ALL_MODULES)
   │                             each module registers handlers on the shared `app`
   └─ idle()                  → runs until Ctrl+C / SIGTERM (graceful stop)

Docker CMD:  gunicorn app:app (keep-alive web)  &  python -m Extractor (bot)
```

* **Auth flow:** `core/access.py → is_allowed(user)`: owner/sudo always; others need a premium plan with a future `expire_date` in MongoDB.
* **TXT engine:** every `Title:URL` line is classified (YouTube, m3u8, video, PDF, image, zip, HTML, Drive) → downloaded with yt-dlp / ffmpeg / HTTP → uploaded with a numbered caption.
* **State:** premium plans in MongoDB; sudo list in `sudo_users.json`; sessions in `sessions/`.

---

## 📦 Requirements

* Python **3.10**
* System tools: `ffmpeg`, `aria2`, Bento4 `mp4decrypt` (the Dockerfile installs all of them)
* MongoDB database (Atlas free tier works)
* Telegram `API_ID` / `API_HASH` and a bot token
* Python packages: see `requirements.txt` (pyrogram 2.0.106, pyromod, tgcrypto, motor, yt-dlp, aiohttp, pycryptodome, PyJWT, PyPDF2, reportlab, flask, gunicorn, …)

---

## 🔐 Configuration (environment variables)

All secrets are **environment-only**. Copy `.env.example` → `.env` (local) or set them in the host dashboard.

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `API_ID` | ✅ | – | from https://my.telegram.org |
| `API_HASH` | ✅ | – | from https://my.telegram.org |
| `BOT_TOKEN` | ✅ | – | from @BotFather |
| `MONGO_URL` | ✅ | – | MongoDB connection string |
| `OWNER_ID` | ⭐ | built-in id | your Telegram user id |
| `SUDO_USERS` | – | owner | space/comma-separated ids |
| `CHANNEL_ID` | – | built-in | log channel |
| `CHANNEL_ID2` | – | built-in | force-join channel |
| `PREMIUM_LOGS` | – | built-in | premium log channel |
| `BOT_USERNAME`, `BOT_TEXT`, `THUMB_URL`, `ADMIN_BOT_USERNAME` | – | built-in | branding |
| `CREDIT` | – | built-in | credit shown in captions |
| `AUTH_USERS`, `TOTAL_USERS` | – | – | comma-separated ids |
| `COOKIES_FILE_PATH` | – | `youtube_cookies.txt` | YouTube cookies path |
| `SUDO_FILE` | – | `sudo_users.json` | sudo list file |
| `CW_TOKEN`, `CP_TOKEN` | – | empty | default CareerWill / Classplus tokens |
| `NEWBOT_UPLOAD_TOKEN_1/2`, `FREECP_TOKEN_1`, `FREEAPPX_TOKEN_1` | – | empty | module tokens |
| `UNSPLASH_ACCESS_KEY`, `UNSPLASH_QUERY` | – | empty / `animal baby` | random image API |
| `PORT` | – | `5000` | set automatically by Render/Heroku |

The bot **exits with a clear error** if a required variable is missing.

---

## 🚀 Deployment

### Render (Docker) — recommended
1. Push the project to GitHub.
2. Render → **New → Web Service** → connect repo → **Runtime: Docker**.
3. Add the environment variables above.
4. Deploy. Healthy start shows `» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ` in the logs.
> The Dockerfile uses `python:3.10-slim-bookworm` (the old *bullseye* image gives apt `404` errors).
> Free instances sleep when idle — ping `/` with an uptime monitor to keep it awake.

### Heroku
Uses `heroku.yml` (container stack): `heroku stack:set container`, set config vars, `git push heroku main`.

### VPS / Local
```bash
sudo apt install -y ffmpeg aria2 git          # + Bento4 mp4decrypt in PATH
python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                           # fill values
set -a && source .env && set +a
python -m Extractor
```
(Or `python run.py` to start the Flask app and the bot together.)

---

## 📄 TXT file format

One item per line:

```
Lecture 1 - Introduction:https://example.com/video.m3u8
Notes chapter 1:https://example.com/notes.pdf
```
The extractors produce this format; the uploader modes (`/king`, `/bravo`, …) consume it.

---

## 💳 Access control & premium

| Role | Access |
|---|---|
| **Owner** (`OWNER_ID`) | everything, cannot be removed |
| **Sudo** | all tools + plan/auth management, not the sudo list |
| **Premium user** | premium tools until `expire_date` |
| **Free user** | `/start`, `/help`, `/id`, `/t2t`, `/y2t`, … |

Grant a plan: `/add_premium USER_ID 30 day` (units: `min`, `hour`, `day`, `month`, `year`).

---

## 🧩 Adding a new module

1. Create `Extractor/modules/my_source.py`:
```python
from pyrogram import filters
from Extractor import app
from Extractor.core.access import is_allowed

@app.on_message(filters.command("mysource"))
async def my_source(client, m):
    if not await is_allowed(m.from_user.id):
        return await m.reply_text("Premium required.")
    await m.reply_text("Hello from my_source!")
```
2. Restart. Modules are auto-imported — no registration needed.
3. Avoid duplicate command names (first registered handler wins).

---

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| `Missing required environment variable(s)` | Set `API_ID`, `API_HASH`, `BOT_TOKEN`, `MONGO_URL` |
| Docker build: `404 Not Found` from deb.debian.org | Use the provided Dockerfile (bookworm base) |
| `ModuleNotFoundError: globals/vars/...` | Old stale `modules/main.py` is present — delete it |
| Bot silent / commands ignored | Check `OWNER_ID`, premium plan, and that no second instance uses the same token |
| `AUTH_KEY_DUPLICATED` / session errors | Delete `sessions/` and restart; run only one instance |
| `FloodWait` | Telegram rate limit — wait the stated seconds |
| YouTube "sign in to confirm you're not a bot" | Upload fresh cookies with `/cookies` |
| Video merge/convert fails | Make sure `ffmpeg` is installed and in `PATH` |
| `/premium_users` empty | No active plans in MongoDB |
| Render service sleeps | Free plan limitation; use an uptime pinger |

---

## 🔒 Security notes

* Never commit `.env`, `*.session`, `youtube_cookies.txt`, `device_private_key.txt`, `device_client_id_blob` (already in `.gitignore`).
* If any token/password was ever committed or shared, **rotate it** (BotFather → revoke, new MongoDB password).
* `/eval`, `/x`, `/sh` execute code on the server — keep `OWNER_ID` correct and private.
* Tokens users enter in the bot are used only for that session's extraction.

---

## 📝 Changelog

**v3.1 (fixed)**
* Removed stale/duplicate files (`modules/main.py`, `utils.py`, `saini_broadcast.py`, `core/video_core.py`, `core/uploader_core.py`, extra `masterdl.so`).
* Fixed shutdown handling, `/premium_users`, blocking `time.sleep` in async code, invalid escape sequence.
* Resolved duplicate command handlers; `/getcookies` is now owner-only.
* One config source (`config.py`), no hardcoded secrets; tokens moved to env vars.
* Dockerfile moved to Debian bookworm; `ADVANCE-app.json` repaired; manifest updated.

See [CHANGES.md](CHANGES.md).

---

## ⚖️ Disclaimer & credits

This project is provided for educational purposes. Use it **only with accounts and content you are authorised to access**,
and respect each platform's terms of service and your local laws. The authors are not responsible for misuse.

Built by merging work from: Extractor, vikas-bot, Saini-1 (Nikhil Saini), newbot, pw-pro-bot and contributors. Maintained by **Anuj**.
