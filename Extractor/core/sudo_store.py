"""Sudo user list, persisted to a JSON file (SUDO_FILE env, default sudo_users.json).

Owner (config.OWNER_ID) is always staff and can never be removed. Sudo users get the same access as the
owner for the tools (premium-gated ones included), but cannot manage the sudo list.
"""
import json
import os
import threading

from config import OWNER_ID

SUDO_FILE = os.getenv("SUDO_FILE", "sudo_users.json")
_lock = threading.Lock()


def _load() -> list[int]:
    try:
        with open(SUDO_FILE, "r", encoding="utf-8") as f:
            return [int(x) for x in json.load(f)]
    except (FileNotFoundError, ValueError, TypeError):
        return []


def _save(ids: list[int]) -> None:
    tmp = SUDO_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(set(ids)), f)
    os.replace(tmp, SUDO_FILE)


def list_sudo() -> list[int]:
    with _lock:
        return _load()


def is_sudo(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in list_sudo()


def add_sudo(user_id: int) -> bool:
    """Returns False if the user is already in the list."""
    with _lock:
        ids = _load()
        if user_id in ids:
            return False
        ids.append(user_id)
        _save(ids)
        return True


def remove_sudo(user_id: int) -> bool:
    """Returns False if the user wasn't in the list. The owner can't be removed (they aren't stored)."""
    with _lock:
        ids = _load()
        if user_id not in ids:
            return False
        ids.remove(user_id)
        _save(ids)
        return True
