"""/sudo add|remove <user_id> and /userlist (owner only for changes). Ported from newbot's sudo commands."""
from pyrogram import filters
from pyrogram.types import Message

from Extractor import app
from config import OWNER_ID
from Extractor.core.sudo_store import add_sudo, remove_sudo, list_sudo

USAGE = "Usage: <code>/sudo add USER_ID</code> or <code>/sudo remove USER_ID</code>"


@app.on_message(filters.command("sudo"))
async def sudo_cmd(client, m: Message):
    if m.from_user.id != OWNER_ID:
        await m.reply_text("🚫 Only the owner can change the sudo list.")
        return
    if len(m.command) != 3 or m.command[1].lower() not in ("add", "remove") or not m.command[2].lstrip("-").isdigit():
        await m.reply_text(USAGE)
        return
    action, uid = m.command[1].lower(), int(m.command[2])
    if action == "add":
        ok = add_sudo(uid)
        msg = f"✅ <code>{uid}</code> added to sudo." if ok else f"⚠️ <code>{uid}</code> is already sudo."
    else:
        if uid == OWNER_ID:
            msg = "🚫 The owner can't be removed."
        else:
            ok = remove_sudo(uid)
            msg = f"✅ <code>{uid}</code> removed from sudo." if ok else f"⚠️ <code>{uid}</code> isn't in the sudo list."
    await m.reply_text(msg)


@app.on_message(filters.command("userlist") & filters.user(OWNER_ID))
async def userlist_cmd(client, m: Message):
    ids = list_sudo()
    if not ids:
        await m.reply_text("No sudo users.")
        return
    await m.reply_text("👥 <b>Sudo users:</b>\n" + "\n".join(f"• <code>{i}</code>" for i in ids))
