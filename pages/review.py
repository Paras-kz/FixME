from datetime import date, timedelta

from nicegui import ui
from sqlmodel import select

from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import Task

STATUS_OPTIONS = {"followed": "Followed", "partial": "Partial", "skipped": "Skipped"}


def _tasks_for(day: date) -> list[Task]:
    with get_session() as session:
        stmt = (
            select(Task)
            .where(Task.owner == current_owner(), Task.scheduled_date == day)
            .order_by(Task.start_time)
        )
        return list(session.exec(stmt))


def _set_status(task_id: int, status: str) -> None:
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        task.review_status = status
        session.add(task)
        session.commit()


def _set_note(task_id: int, note: str) -> None:
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        task.review_note = note or None
        session.add(task)
        session.commit()


@ui.refreshable
def _review_list(day: date) -> None:
    tasks = _tasks_for(day)
    if not tasks:
        ui.label("No tasks scheduled that day.").classes("text-neutral-400")
        return
    for task in tasks:
        with ui.card().classes("w-full p-3 gap-2"):
            with ui.row().classes("items-center justify-between w-full"):
                span = f"{task.start_time or ''}–{task.end_time or ''}".strip("–")
                ui.label(f"{task.title}  ({span})").classes("font-medium")
                ui.toggle(
                    STATUS_OPTIONS,
                    value=task.review_status,
                    on_change=lambda e, t=task.id: _set_status(t, e.value),
                )
            ui.input(
                "Note",
                value=task.review_note or "",
                on_change=lambda e, t=task.id: _set_note(t, e.value),
            ).classes("w-full")


@ui.page("/review")
def review_page() -> None:
    state = {"day": date.today()}

    def set_day(new_day: date) -> None:
        state["day"] = new_day
        day_label.text = new_day.strftime("%A, %b %d")
        _review_list.refresh(new_day)
        if calendar.value != new_day.isoformat():
            calendar.value = new_day.isoformat()

    with frame("End-of-day review"):
        with ui.row().classes("w-full gap-4 items-start flex-nowrap"):
            with ui.column().classes("flex-grow gap-2 min-w-0"):
                with ui.row().classes("items-center gap-1"):
                    ui.button(
                        icon="chevron_left", on_click=lambda: set_day(state["day"] - timedelta(days=1))
                    ).props("flat dense round")
                    day_label = ui.label(state["day"].strftime("%A, %b %d")).classes(
                        "text-lg font-medium min-w-[190px] text-center"
                    )
                    ui.button(
                        icon="chevron_right", on_click=lambda: set_day(state["day"] + timedelta(days=1))
                    ).props("flat dense round")
                _review_list(state["day"])

            with ui.card().classes("shrink-0 p-2"):
                calendar = ui.date(
                    value=state["day"].isoformat(),
                    on_change=lambda e: set_day(date.fromisoformat(e.value)),
                ).props("today-btn")
