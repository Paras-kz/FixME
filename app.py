import os

from dotenv import load_dotenv

load_dotenv()

from nicegui import ui  # noqa: E402

import models  # noqa: E402,F401  registers tables on SQLModel.metadata before create_all
from db import init_db  # noqa: E402

init_db()
import auth  # noqa: E402,F401  registers the login page + auth middleware
import pages  # noqa: E402,F401

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        title="fixme",
        storage_secret=os.environ.get("STORAGE_SECRET", "dev-secret-change-me"),
    )
