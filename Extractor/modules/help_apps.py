"""/help and /apps: command list and the list of supported sources. Ported from newbot."""
from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from config import OWNER_ID
from Extractor.core.sudo_store import is_sudo


@app.on_message(filters.command("help"))
async def help_cmd(client, m: Message):
    lines = [
        "<b>Commands</b>",
        "/start : start the bot",
        "/apps : supported sources",
        "/id : chat id",
        "/info : your details",
        "/t2t : text to .txt",
        "/e2t : tidy a .txt file",
        "/y2t (or /yt2txt) : YouTube video or playlist to .txt",
        "/myplan : your premium plan",
        "/nologin : without-login sources (CareerWill, SelectionWay, Study IQ, KGS App, Unacademy, Next Toppers)",
        "/cwfree /sw /iqfree /kgsapp /una /nt /rgmaxx : open one of those sources directly (/maxx = RG Maxx, gives TXT + HTML player)",
        "/study : Study Mode - browse a batch, pick a lecture, download + upload it here",
        "",
        "<b>TXT to video</b> (send a .txt, then answer the prompts)",
        "/king or /upload, /bravo, /spidy, /alpha : download and upload every link",
        "/advance : same, with a PW token prompt",
        "/tushar : show counts by type, then download",
        "/stop : cancel the running batch in this chat",
    ]
    if is_sudo(m.from_user.id):
        lines += ["", "<b>Sudo / owner</b>", "/extract : Classplus batch extract", "/cw : CareerWill", "/ugcw : CareerWill (other flow)",
                  "/dbupload cw|kgs : extract every batch/course and post each as a .txt in the database channel",
                  "/dbstop : stop a running /dbupload", "/dbinfo : show the database channels"]
    if m.from_user.id == OWNER_ID:
        lines += [
            "", "<b>Owner only</b>",
            "/cookies : upload YouTube cookies", "/getcookies : get YouTube cookies",
            "/setdb cw|kgs CHANNEL_ID : set the database channel for /dbupload",
            "/sudo add|remove USER_ID", "/userlist : list sudo users", "/restart : restart the bot",
            "/selftest : live check of the download and upload path on this server",
        ]
    await m.reply_text("\n".join(lines), quote=True)


@app.on_message(filters.command("apps"))
async def apps_cmd(client, m: Message):
    await m.reply_text(
        "<b>Supported sources</b>\n\n"
        "• PhysicsWallah (/pw)\n"
        "• Appx / Appx OTP / Appx Zip (/appx, /appxotp, /appxm)\n"
        "• Classplus (/cp)\n"
        "• Utkarsh (/utk)\n"
        "• StudyIQ (/iq)\n"
        "• Khan GS, Exampur, Vision IAS, MyPathshala, Adda247 and more\n"
        "• Without login (/nologin): CareerWill, SelectionWay, Study IQ, KGS App, Unacademy, Next Toppers, RG Maxx (+ /study mode)\n"
        "• CareerWill (/ugcw, /cw)\n"
        "• YouTube playlists to .txt (/y2t)\n",
        disable_web_page_preview=True,
        quote=True,
    )
