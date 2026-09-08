from nicegui import ui

REVIEW_COLORS = {"followed": "green", "partial": "amber", "skipped": "red"}

CATEGORIES = ["Work", "Personal", "Health", "Learning", "Errands", "Social", "Chores"]


def category_select(value: str | None = None, label: str = "Category") -> ui.select:
    """Dropdown of common categories; typing a new one and pressing enter adds it."""
    return (
        ui.select(CATEGORIES, value=value, label=label, new_value_mode="add-unique")
        .props("clearable")
        .classes("w-32")
    )


def time_field(label: str, value: str = "") -> ui.input:
    """Text input showing HH:MM, with a clock icon that opens a Quasar time-picker popup."""
    with ui.input(label, value=value).classes("w-24") as field:
        with field.add_slot("append"):
            icon = ui.icon("schedule").classes("cursor-pointer")
        with ui.menu() as menu:
            ui.time().bind_value(field)
        icon.on("click", menu.open)
    return field


def link_time_range(start: ui.input, end: ui.input) -> None:
    """When start changes and end is still empty, default end to 1h later (same am/pm),
    so its picker opens already on the right half of the clock. User can still override."""

    def on_start_change(e) -> None:
        if not e.value or end.value:
            return
        hour, minute = map(int, e.value.split(":"))
        end.value = f"{min(hour + 1, 23):02d}:{minute:02d}"

    start.on_value_change(on_start_change)


def stat_tile(label: str, value: str, icon: str = "insights") -> None:
    with ui.card().classes("items-center p-4 min-w-[140px]"):
        ui.icon(icon).classes("text-2xl text-primary")
        ui.label(value).classes("text-xl font-bold")
        ui.label(label).classes("text-xs text-neutral-400")


def task_card(task, on_change) -> None:
    with ui.card().classes("w-full p-3 gap-1"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(task.title).classes("font-medium")
            if task.category:
                ui.badge(task.category).props("color=primary")
        if task.notes:
            ui.label(task.notes).classes("text-xs text-neutral-400")
        on_change(task)
