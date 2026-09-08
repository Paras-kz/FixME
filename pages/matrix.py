from datetime import date, datetime

from nicegui import ui
from sqlmodel import select

from components import link_time_range, time_field
from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import Task

QUADRANTS = [
    (True, True, "Do now", "red"),
    (True, False, "Delegate", "amber"),
    (False, True, "Schedule", "primary"),
    (False, False, "Delete / ignore", "neutral"),
]


def _open_tasks() -> list[Task]:
    with get_session() as session:
        stmt = select(Task).where(Task.owner == current_owner(), Task.kanban_status != "done")
        return list(session.exec(stmt))


def _toggle(task_id: int, field: str) -> None:
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        setattr(task, field, not getattr(task, field))
        session.add(task)
        session.commit()
    _grid.refresh()


def _schedule(task_id: int, start: ui.input, end: ui.input, dialog: ui.dialog) -> None:
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        task.scheduled_date = date.today()
        task.start_time = datetime.strptime(start.value, "%H:%M").time() if start.value else None
        task.end_time = datetime.strptime(end.value, "%H:%M").time() if end.value else None
        session.add(task)
        session.commit()
    dialog.close()
    ui.notify(f'"{task.title}" scheduled for today')
    _grid.refresh()


def _open_schedule_dialog(task: Task) -> None:
    with ui.dialog() as dialog, ui.card().classes("gap-2"):
        ui.label(f'Schedule "{task.title}"').classes("font-medium")
        with ui.row().classes("gap-2"):
            start = time_field("Start")
            end = time_field("End")
            link_time_range(start, end)
        with ui.row().classes("justify-end w-full"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Schedule", on_click=lambda: _schedule(task.id, start, end, dialog))
    dialog.open()


@ui.refreshable
def _grid() -> None:
    tasks = _open_tasks()
    with ui.grid(columns=2).classes("w-full gap-4"):
        for urgent, important, label, color in QUADRANTS:
            with ui.card().classes("p-3 gap-2"):
                ui.label(label).classes(f"font-medium text-{color}-400")
                quadrant_tasks = [
                    t for t in tasks if t.is_urgent == urgent and t.is_important == important
                ]
                if not quadrant_tasks:
                    ui.label("—").classes("text-neutral-500 text-sm")
                for task in quadrant_tasks:
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(task.title).classes("text-sm")
                        with ui.row().classes("gap-1"):
                            ui.button(
                                icon="bolt",
                                on_click=lambda t=task.id: _toggle(t, "is_urgent"),
                            ).props("flat dense round size=sm").tooltip("Toggle urgent")
                            ui.button(
                                icon="star",
                                on_click=lambda t=task.id: _toggle(t, "is_important"),
                            ).props("flat dense round size=sm").tooltip("Toggle important")
                            ui.button(
                                icon="event",
                                on_click=lambda t=task: _open_schedule_dialog(t),
                            ).props("flat dense round size=sm").tooltip("Schedule")


@ui.page("/matrix")
def matrix_page() -> None:
    with frame("Eisenhower matrix"):
        _grid()
