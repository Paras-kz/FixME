from pathlib import Path

from nicegui import app, ui
from starlette.responses import FileResponse

from layout import frame
from version import VERSION

EXE_PATH = Path(__file__).parent.parent / "static" / "downloads" / "fixme.exe"


@app.get("/download/fixme.exe")
def download_exe() -> FileResponse:
    return FileResponse(EXE_PATH, filename="fixme.exe", media_type="application/octet-stream")


@app.get("/version")
def version_endpoint() -> dict:
    return {"version": VERSION}


@ui.page("/download")
def download_page() -> None:
    with frame("Download"):
        with ui.card().classes("max-w-md gap-3 p-6"):
            ui.label("fixme desktop app").classes("text-xl font-bold")
            ui.label(
                "A standalone Windows app — no install, no login, no account. "
                "Your data stays on your own machine."
            ).classes("text-neutral-400")
            ui.button(
                "Download for Windows",
                icon="download",
                on_click=lambda: ui.navigate.to("/download/fixme.exe"),
            ).classes("w-full")
