import webbrowser
from contextlib import contextmanager

import httpx
from nicegui import app, ui

from auth import logout
from identity import current_owner
from version import VERSION, DOWNLOAD_PAGE_URL, UPDATE_CHECK_URL

NAV = [
    ("/", "Today", "today"),
    ("/review", "Review", "fact_check"),
    ("/dashboard", "Dashboard", "insights"),
    ("/kanban", "Kanban", "view_kanban"),
    ("/matrix", "Matrix", "grid_view"),
    ("/habits", "Habits", "check_circle"),
    ("/pomodoro", "Pomodoro", "timer"),
    ("/download", "Get the app", "download"),
]


async def _check_for_updates() -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(UPDATE_CHECK_URL)
            latest = resp.json()["version"]
    except Exception:
        ui.notify("Couldn't check for updates — are you online?", color="negative")
        return

    if latest == VERSION:
        ui.notify(f"You're up to date (v{VERSION})", color="positive")
        return

    with ui.dialog() as dialog, ui.card().classes("gap-3"):
        ui.label(f"New version available: v{latest} (you have v{VERSION})").classes("font-medium")
        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Later", on_click=dialog.close).props("flat")
            ui.button(
                "Download", on_click=lambda: (webbrowser.open(DOWNLOAD_PAGE_URL), dialog.close())
            )
    dialog.open()


@contextmanager
def frame(title: str):
    ui.colors(primary="#6366f1")
    ui.dark_mode(True)
    ui.query("body").classes("bg-neutral-950")

    with ui.header().classes("items-center justify-between px-4 bg-neutral-900"):
        ui.label("fixme").classes("text-lg font-bold")
        with ui.row().classes("gap-1 items-center"):
            for path, label, icon in NAV:
                ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props(
                    "flat dense color=white"
                )
            if current_owner() == "local":
                ui.button(icon="system_update", on_click=_check_for_updates).props(
                    "flat dense round color=white"
                ).tooltip(f"Check for updates (v{VERSION})")
            try:
                if app.storage.user.get("authenticated", False):
                    ui.button("Logout", icon="logout", on_click=logout).props(
                        "flat dense color=white"
                    )
                else:
                    ui.button(
                        "Login", icon="login", on_click=lambda: ui.navigate.to("/login")
                    ).props("flat dense color=white")
            except RuntimeError:
                pass  # desktop app: no storage_secret configured, no login concept needed

    if current_owner().startswith("guest:"):
        with ui.row().classes(
            "w-full bg-amber-950/40 text-amber-200 text-xs px-4 py-1.5 items-center gap-2"
        ):
            ui.icon("info", size="xs")
            ui.label(
                "You're browsing as a guest — this demo data is private to your browser, "
                "not shared with anyone else."
            )

    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        ui.label(title).classes("text-2xl font-semibold")
        yield
