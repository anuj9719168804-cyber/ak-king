# Extractor/modules/premium.py

from config import OWNER_ID

# Premium users dictionary (simple storage, aap DB bhi use kar sakte ho)
premium_users = {}

# Ye function sirf define hai, decorator yahan mat lagao
async def add_premium_handler(message, dp):
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Sirf owner hi premium add kar sakta hai.")
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply("⚠️ Usage: /add_premium user_id time")
        return

    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("❌ User ID numeric hona chahiye.")
        return

    time = " ".join(args[1:])
    premium_users[user_id] = time

    await message.reply(f"✅ User {user_id} ko {time} ke liye premium diya gaya.")
