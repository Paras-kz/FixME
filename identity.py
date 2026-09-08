import secrets
from typing import TypeVar

from nicegui import app
from sqlmodel import Session

OWNER = "owner"

T = TypeVar("T")


def current_owner() -> str:
    """Whose data the current visitor should see.

    Logged-in owner -> the fixed OWNER id (their real, persistent data).
    Anonymous web visitor -> a random id stashed in their browser session, so they get
    their own private guest sandbox without ever needing an account.
    Desktop app (no storage_secret configured, so app.storage.user isn't available at
    all) -> falls back to a single fixed local identity, since it's always one person.
    """
    try:
        if app.storage.user.get("authenticated", False):
            return OWNER
        if "guest_id" not in app.storage.user:
            app.storage.user["guest_id"] = secrets.token_hex(8)
        return f"guest:{app.storage.user['guest_id']}"
    except RuntimeError:
        return "local"


def get_owned(session: Session, model: type[T], obj_id: int) -> T | None:
    """Fetch a row by id, but only if it belongs to the current visitor — prevents one
    guest (or a stranger) from editing/deleting another user's data by guessing an id."""
    obj = session.get(model, obj_id)
    if obj is None or getattr(obj, "owner", None) != current_owner():
        return None
    return obj
