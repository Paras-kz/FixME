from nicegui import native, ui

import models  # noqa: F401  registers tables on SQLModel.metadata before create_all
from db import init_db

init_db()
import pages  # noqa: E402,F401

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        native=True,
        window_size=(1200, 800),
        title="fixme",
        reload=False,
        port=native.find_open_port(),
    )
