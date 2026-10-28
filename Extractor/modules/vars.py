#🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌
# Add your details here and then deploy by clicking on HEROKU Deploy button
import os
from os import environ

# Single source of truth: /config.py (env vars only, no hardcoded secrets)
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

OWNER = int(environ.get("OWNER") or OWNER_ID)
CREDIT = environ.get("CREDIT", "『A』『N』『N』『U』")
cookies_file_path = os.getenv("cookies_file_path", "youtube_cookies.txt")

TOTAL_USERS = [int(u) for u in os.environ.get('TOTAL_USERS', '999999').split(',') if u.strip()]

AUTH_USERS = [int(u) for u in os.environ.get('AUTH_USERS', '').split(',') if u.strip()]
if int(OWNER) not in AUTH_USERS:
    AUTH_USERS.append(int(OWNER))



