"""Shared access helper: owner and sudo users always allowed; other users need an unexpired premium plan."""
import datetime

from Extractor.core.mongo import plans_db
from Extractor.core.sudo_store import is_sudo


async def is_allowed(user_id: int) -> bool:
    if is_sudo(user_id):
        return True
    data = await plans_db.check_premium(user_id)
    if not data or not data.get("expire_date"):
        return False
    exp = data["expire_date"]
    now = datetime.datetime.now(datetime.timezone.utc)
    if exp.tzinfo is None:  # Mongo may return naive UTC datetimes
        exp = exp.replace(tzinfo=datetime.timezone.utc)
    return exp > now
