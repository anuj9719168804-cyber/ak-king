import os, re, sys, json, pytz, asyncio, requests, subprocess, random
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
import Extractor.modules.globals as globals
from Extractor.modules.logs import logging
from Extractor.modules.html_handler import register_html_handlers
from Extractor.modules.drm_handler import register_drm_handlers
from Extractor.modules.text_handler import register_text_handlers
from Extractor.modules.features import register_feature_handlers
from Extractor.modules.upgrade import register_upgrade_handlers
from Extractor.modules.commands import register_commands_handlers
from Extractor.modules.settings import register_settings_handlers
from Extractor.modules.youtube_handler import register_youtube_handlers
from Extractor.modules.authorisation import register_authorisation_handlers
from Extractor.modules.vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

# Use the shared Pyrogram client of this project (no second Client / no bot.run())
from Extractor import app as bot

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎙️ Commands", callback_data="cmd_command")],
            [InlineKeyboardButton("💎 Features", callback_data="feat_command"), InlineKeyboardButton("⚙️ Settings", callback_data="setttings")],
            [InlineKeyboardButton("💳 Suscribation", callback_data="upgrade_command")],
            [InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}"), InlineKeyboardButton(text="🛠️ Repo", url="https://github.com/nikhilsainiop/saini-txt-direct")],
        ])      

    
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("back_to_main_menu"))
async def back_to_main_menu(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = (
        f"𝐇𝐞𝐥𝐥𝐨 **{first_name}** 👋!\n\n"
        f"➠ 𝐈 𝐚𝐦 𝐚 𝐓𝐞𝐱𝐭 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
        f"➠ Can Extract Videos & PDFs From Your Text File and Upload to Telegram!\n\n"
        f"╭────────⊰◆⊱────────╮\n"
        f"➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : [{CREDIT}](tg://openmessage?user_id={OWNER}) 💻\n"
        f"╰────────⊰◆⊱────────╯\n"
    )
    
    await callback_query.message.edit_media(
      InputMediaPhoto(
        media="https://envs.sh/GVI.jpg",
        caption=caption
      ),
      reply_markup=keyboard
    )
    await callback_query.answer()  

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,


# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,


# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["logs"]))
async def send_logs(client: Client, m: Message):  # Correct parameter name
    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(f"**Error sending logs:**\n<blockquote>{e}</blockquote>")

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["reset"]))
async def restart_handler(_, m):
    if m.chat.id != OWNER:
        return
    else:
        await m.reply_text("𝐁𝐨𝐭 𝐢𝐬 𝐑𝐞𝐬𝐞𝐭𝐢𝐧𝐠...", True)
        os.execl(sys.executable, sys.executable, *sys.argv)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,


#=================================================================

register_text_handlers(bot)
register_html_handlers(bot)
register_feature_handlers(bot)
register_settings_handlers(bot)
register_upgrade_handlers(bot)
register_commands_handlers(bot)
register_youtube_handlers(bot)
register_authorisation_handlers(bot)
register_drm_handlers(bot)
#==================================================================

def notify_owner():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": OWNER,
        "text": "𝐁𝐨𝐭 𝐑𝐞𝐬𝐭𝐚𝐫𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 ✅"
    }
    requests.post(url, data=data)

def reset_and_set_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"

    # General users ke liye commands
    general_commands = [
        {"command": "start", "description": "✅ Check Alive the Bot"},
        {"command": "stop", "description": "🚫 Stop the ongoing process"},
        {"command": "id", "description": "🆔 Get Your ID"},
        {"command": "info", "description": "ℹ️ Check Your Information"},
        {"command": "cookies", "description": "📁 Upload YT Cookies"},
        {"command": "y2t", "description": "🔪 YouTube → .txt Converter"},
        {"command": "ytm", "description": "🎶 YouTube → .mp3 downloader"},
        {"command": "t2t", "description": "📟 Text → .txt Generator"},
        {"command": "t2h", "description": "🌐 .txt → .html Converter"},
        {"command": "logs", "description": "👁️ View Bot Activity"},
    ]
    # Owner ke liye extra commands
    owner_commands = general_commands + [
        {"command": "broadcast", "description": "📢 Broadcast to All Users"},
        {"command": "broadusers", "description": "👨‍❤️‍👨 All Broadcasting Users"},
        {"command": "addauth", "description": "▶️ Add Authorisation"},
        {"command": "rmauth", "description": "⏸️ Remove Authorisation "},
        {"command": "users", "description": "👨‍👨‍👧‍👦 All Premium Users"},
        {"command": "reset", "description": "✅ Reset the Bot"}
    ]

    # General users ke liye set commands (scope default)
    requests.post(url, json={
        "commands": general_commands,
        "scope": {"type": "default"},
        "language_code": "en"
    })

    # Owner ke liye set commands (scope user)
    requests.post(url, json={
        "commands": owner_commands,
        "scope": {"type": "chat", "chat_id": OWNER},  # OWNER variable me chat id hona chahiye
        "language_code": "en"
    })
    

