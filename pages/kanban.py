from nicegui import ui
from sqlmodel import select

from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import Task

COLUMNS = [("backlog", "Backlog"), ("todo", "Todo"), ("in_progress", "In Progress"), ("done", "Done")]


def _tasks() -> list[Task]:
    with get_session() as session:
        stmt = select(Task).where(Task.owner == current_owner()).order_by(Task.created_at)
        return list(session.exec(stmt))


def _move(task_id: int, direction: int) -> None:
    order = [c[0] for c in COLUMNS]
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        idx = order.index(task.kanban_status) + direction
        if 0 <= idx < len(order):
            task.kanban_status = order[idx]
            session.add(task)
            session.commit()
    _board.refresh()


@ui.refreshable
def _board() -> None:
    tasks = _tasks()
    with ui.row().classes("w-full gap-4 items-start"):
        for status, label in COLUMNS:
            with ui.column().classes("flex-1 gap-2"):
                ui.label(label).classes("font-medium text-neutral-300")
                for task in [t for t in tasks if t.kanban_status == status]:
                    with ui.card().classes("w-full p-3 gap-1"):
                        ui.label(task.title).classes("font-medium")
                        if task.category:
                            ui.badge(task.category).props("color=primary")
                        with ui.row().classes("gap-1 justify-end w-full"):
                            ui.button(
                                icon="arrow_back",
                                on_click=lambda t=task.id: _move(t, -1),
                            ).props("flat dense round size=sm")
                            ui.button(
                                icon="arrow_forward",
                                on_click=lambda t=task.id: _move(t, 1),
                            ).props("flat dense round size=sm")


@ui.page("/kanban")
def kanban_page() -> None:
    with frame("Kanban"):
        _board()
