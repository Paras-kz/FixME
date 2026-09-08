from datetime import date, timedelta

from nicegui import ui
from sqlmodel import select

from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import Habit, HabitLog

DAYS = 14


def _habits() -> list[Habit]:
    with get_session() as session:
        stmt = select(Habit).where(Habit.owner == current_owner()).order_by(Habit.name)
        return list(session.exec(stmt))


def _logged_dates(habit_id: int) -> set[date]:
    with get_session() as session:
        stmt = select(HabitLog).where(
            HabitLog.owner == current_owner(), HabitLog.habit_id == habit_id
        )
        return {log.log_date for log in session.exec(stmt)}


def _toggle(habit_id: int, day: date) -> None:
    with get_session() as session:
        if not get_owned(session, Habit, habit_id):
            return
        stmt = select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.log_date == day)
        existing = session.exec(stmt).first()
        if existing:
            session.delete(existing)
        else:
            session.add(HabitLog(owner=current_owner(), habit_id=habit_id, log_date=day))
        session.commit()
    _grid.refresh()


def _add_habit(name_input: ui.input) -> None:
    if not name_input.value:
        return
    with get_session() as session:
        session.add(Habit(owner=current_owner(), name=name_input.value))
        session.commit()
    name_input.value = ""
    _grid.refresh()


def _rename_habit(habit_id: int, name: str, dialog: ui.dialog) -> None:
    if not name:
        ui.notify("Name is required", color="negative")
        return
    with get_session() as session:
        habit = get_owned(session, Habit, habit_id)
        if not habit:
            return
        habit.name = name
        session.add(habit)
        session.commit()
    dialog.close()
    _grid.refresh()


def _delete_habit(habit_id: int, dialog: ui.dialog) -> None:
    with get_session() as session:
        habit = get_owned(session, Habit, habit_id)
        if not habit:
            return
        for log in session.exec(select(HabitLog).where(HabitLog.habit_id == habit_id)):
            session.delete(log)
        session.delete(habit)
        session.commit()
    dialog.close()
    _grid.refresh()


def _open_habit_dialog(habit: Habit) -> None:
    with ui.dialog() as dialog, ui.card().classes("gap-2 min-w-[280px]"):
        ui.label("Edit habit").classes("font-medium")
        name = ui.input("Name", value=habit.name).classes("w-full")
        with ui.row().classes("justify-between w-full"):
            ui.button(
                "Delete", icon="delete", on_click=lambda: _delete_habit(habit.id, dialog)
            ).props("flat color=red")
            with ui.row().classes("gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Save", on_click=lambda: _rename_habit(habit.id, name.value, dialog)
                )
    dialog.open()


@ui.refreshable
def _grid() -> None:
    habits = _habits()
    days = [date.today() - timedelta(days=i) for i in range(DAYS - 1, -1, -1)]
    if not habits:
        ui.label("No habits yet — add one below.").classes("text-neutral-400")
        return
    with ui.column().classes("gap-2 w-full"):
        with ui.row().classes("gap-1 pl-32"):
            for d in days:
                ui.label(d.strftime("%d")).classes("text-xs text-neutral-500 w-6 text-center")
        for habit in habits:
            logged = _logged_dates(habit.id)
            with ui.row().classes("items-center gap-1"):
                with ui.row().classes("items-center gap-1 w-32 cursor-pointer").on(
                    "click", lambda h=habit: _open_habit_dialog(h)
                ):
                    ui.label(habit.name).classes("text-sm truncate")
                    ui.icon("edit", size="xs").classes("text-neutral-500")
                for d in days:
                    done = d in logged
                    ui.button(
                        on_click=lambda h=habit.id, d=d: _toggle(h, d)
                    ).props(f"round dense size=sm color={'primary' if done else 'grey-9'}").classes(
                        "w-6 h-6"
                    )


@ui.page("/habits")
def habits_page() -> None:
    with frame("Habits"):
        _grid()
        with ui.row().classes("items-end gap-2"):
            name = ui.input("New habit")
            ui.button("Add", icon="add", on_click=lambda: _add_habit(name))
