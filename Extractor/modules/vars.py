#🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌
# Add your details here and then deploy by clicking on HEROKU Deploy button
import os
from os import environ

API_ID = int(environ.get("API_ID", "22182189"))
API_HASH = environ.get("API_HASH", "5e7c4088f8e23d0ab61e29ae11960bf5")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

OWNER = int(environ.get("OWNER", "6059771769"))
CREDIT = environ.get("CREDIT", "『A』『N』『N』『U』")
cookies_file_path = os.getenv("cookies_file_path", "youtube_cookies.txt")

TOTAL_USERS = [int(u) for u in os.environ.get('TOTAL_USERS', '999999').split(',') if u.strip()]

AUTH_USERS = [int(u) for u in os.environ.get('AUTH_USERS', '').split(',') if u.strip()]
if int(OWNER) not in AUTH_USERS:
    AUTH_USERS.append(int(OWNER))



