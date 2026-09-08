import os

from nicegui import app, ui


def logout() -> None:
    app.storage.user["authenticated"] = False
    ui.navigate.to("/")


@ui.page("/login")
def login_page() -> None:
    if app.storage.user.get("authenticated", False):
        ui.navigate.to("/")
        return

    def try_login() -> None:
        if username.value == os.environ.get("APP_USERNAME") and password.value == os.environ.get(
            "APP_PASSWORD"
        ):
            app.storage.user["authenticated"] = True
            ui.navigate.to("/")
        else:
            ui.notify("Wrong username or password", color="negative")

    with ui.card().classes("absolute-center gap-2 p-6"):
        ui.label("fixme").classes("text-xl font-bold")
        ui.label("Log in as the owner to see your real data.").classes(
            "text-xs text-neutral-400"
        )
        username = ui.input("Username").on("keydown.enter", try_login).classes("w-64")
        password = (
            ui.input("Password", password=True, password_toggle_button=True)
            .on("keydown.enter", try_login)
            .classes("w-64")
        )
        ui.button("Log in", on_click=try_login).classes("w-full")
