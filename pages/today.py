from datetime import date, datetime, time

from nicegui import ui
from sqlmodel import select

from components import category_select, link_time_range, time_field
from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import Task

HOUR_WIDTH = 90  # px per hour of the horizontal strip
VISIBLE_HOURS = 11  # how many hours are visible before you need to scroll
LANE_HEIGHT = 52  # px per overlapping-task row
HEADER_HEIGHT = 24  # px for the hour-label row


def _today_tasks() -> list[Task]:
    with get_session() as session:
        stmt = (
            select(Task)
            .where(Task.owner == current_owner(), Task.scheduled_date == date.today())
            .order_by(Task.start_time)
        )
        return list(session.exec(stmt))


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _time_str(t: time | None) -> str:
    return t.strftime("%H:%M") if t else ""


def _parse_time(value: str) -> time | None:
    return datetime.strptime(value, "%H:%M").time() if value else None


def _assign_lanes(tasks: list[Task]) -> list[tuple[Task, int]]:
    """Greedily stack overlapping tasks into separate lanes, like a calendar's side-by-side events."""
    ordered = sorted(tasks, key=lambda t: _minutes(t.start_time))
    lane_ends: list[int] = []
    result: list[tuple[Task, int]] = []
    for task in ordered:
        start = _minutes(task.start_time)
        end = max(start + 20, _minutes(task.end_time or task.start_time))
        for lane, lane_end in enumerate(lane_ends):
            if start >= lane_end:
                lane_ends[lane] = end
                result.append((task, lane))
                break
        else:
            lane_ends.append(end)
            result.append((task, len(lane_ends) - 1))
    return result


@ui.refreshable
def _day_strip(selecting: bool = False) -> None:
    tasks = _today_tasks()
    scheduled = [t for t in tasks if t.start_time]
    unscheduled = [t for t in tasks if not t.start_time]

    placed = _assign_lanes(scheduled)
    num_lanes = max([lane for _, lane in placed], default=-1) + 1
    content_height = HEADER_HEIGHT + max(1, num_lanes) * LANE_HEIGHT
    total_width = 24 * HOUR_WIDTH

    def scroll(direction: int) -> None:
        scroller.run_method("scrollBy", {"left": direction * HOUR_WIDTH * 4, "behavior": "smooth"})

    with ui.row().classes("items-center gap-1 w-full flex-nowrap"):
        ui.button(icon="chevron_left", on_click=lambda: scroll(-1)).props("flat dense round")
        with ui.element("div").classes("overflow-x-auto").style(
            f"max-width:{VISIBLE_HOURS * HOUR_WIDTH}px"
        ) as scroller:
            with ui.element("div").classes("relative").style(
                f"width:{total_width}px; height:{content_height}px"
            ):
                for hour in range(25):
                    left = hour * HOUR_WIDTH
                    ui.label(f"{hour:02d}:00").classes(
                        "absolute text-xs text-neutral-500"
                    ).style(f"left:{left}px; top:0px")
                    ui.element("div").classes("absolute border-l border-neutral-800").style(
                        f"left:{left}px; top:{HEADER_HEIGHT}px; bottom:0px"
                    )

                for task, lane in placed:
                    left = _minutes(task.start_time) / 60 * HOUR_WIDTH
                    end = task.end_time or task.start_time
                    duration = max(20, _minutes(end) - _minutes(task.start_time))
                    width = duration / 60 * HOUR_WIDTH
                    top = HEADER_HEIGHT + lane * LANE_HEIGHT
                    with ui.card().classes(
                        "absolute p-1 gap-0 cursor-pointer overflow-hidden hover:brightness-125"
                    ).style(
                        f"left:{left}px; width:{width}px; top:{top}px; height:{LANE_HEIGHT - 6}px"
                    ).on("click", lambda t=task: _open_edit_dialog(t)):
                        ui.label(task.title).classes("text-xs font-medium truncate")
                        ui.label(
                            f"{_time_str(task.start_time)}–{_time_str(task.end_time)}"
                        ).classes("text-[10px] text-neutral-400 truncate")
        ui.button(icon="chevron_right", on_click=lambda: scroll(1)).props("flat dense round")

    now_hour = datetime.now().hour
    scroller.run_method("scrollTo", {"left": max(0, (now_hour - 2) * HOUR_WIDTH), "behavior": "auto"})

    with ui.card().classes("w-full p-4 gap-2 mt-2"):
        ui.label("Add a task").classes("font-medium")
        with ui.row().classes("items-end gap-2 w-full"):
            title = ui.input("Title").classes("flex-grow")
            start = time_field("Start", datetime.now().strftime("%H:%M"))
            end = time_field("End")
            link_time_range(start, end)
            category = category_select()
            notes = ui.input("Notes")
            ui.button(
                "Add", icon="add", on_click=lambda: _add(title, start, end, category, notes)
            )

    checkboxes: dict[int, ui.checkbox] = {}

    def select_all(value: bool) -> None:
        for cb in checkboxes.values():
            cb.value = value

    def delete_selected() -> None:
        ids = [tid for tid, cb in checkboxes.items() if cb.value]
        _confirm_delete(ids, f"Delete {len(ids)} selected task(s)? This can't be undone.")

    def clear_schedule() -> None:
        ids = [t.id for t in tasks]
        _confirm_delete(ids, f"Clear all {len(ids)} of today's tasks? This can't be undone.")

    if tasks:
        with ui.row().classes("items-center justify-end gap-2 mt-2 w-full"):
            if selecting:
                ui.checkbox("Select all", on_change=lambda e: select_all(e.value))
                ui.button("Delete selected", icon="delete", on_click=delete_selected).props(
                    "flat color=red dense"
                )
                ui.button("Delete all", icon="delete_sweep", on_click=clear_schedule).props(
                    "flat color=red dense"
                )
                ui.button("Cancel", on_click=lambda: _day_strip.refresh(False)).props(
                    "flat dense"
                )
            else:
                ui.button(
                    "Select", icon="checklist", on_click=lambda: _day_strip.refresh(True)
                ).props("flat dense")

    if scheduled:
        ui.label("Today's tasks").classes("text-sm text-neutral-400 mt-2")
        for task in scheduled:
            with ui.row().classes("items-center gap-2 w-full"):
                if selecting:
                    checkboxes[task.id] = ui.checkbox()
                with ui.card().classes(
                    "flex-grow p-3 cursor-pointer hover:brightness-125"
                ).on("click", lambda t=task: _open_edit_dialog(t)):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-3"):
                            ui.label(
                                f"{_time_str(task.start_time)}–{_time_str(task.end_time)}"
                            ).classes("text-xs text-neutral-400 w-24")
                            ui.label(task.title).classes("font-medium")
                        if task.category:
                            ui.badge(task.category).props("color=primary")

    if unscheduled:
        ui.label("Unscheduled today").classes("text-sm text-neutral-400 mt-2")
        for task in unscheduled:
            with ui.row().classes("items-center gap-2 w-full"):
                if selecting:
                    checkboxes[task.id] = ui.checkbox()
                with ui.row().classes(
                    "items-center gap-2 cursor-pointer hover:brightness-125"
                ).on("click", lambda t=task: _open_edit_dialog(t)):
                    ui.icon("event_busy").classes("text-neutral-500")
                    ui.label(task.title)


def _delete(task_id: int) -> None:
    _delete_many([task_id])


def _delete_many(task_ids: list[int]) -> None:
    with get_session() as session:
        for task_id in task_ids:
            task = get_owned(session, Task, task_id)
            if task:
                session.delete(task)
        session.commit()
    _day_strip.refresh(False)  # exit selection mode after deleting


def _confirm_delete(task_ids: list[int], message: str) -> None:
    if not task_ids:
        ui.notify("Nothing selected", color="warning")
        return
    with ui.dialog() as dialog, ui.card().classes("gap-2"):
        ui.label(message).classes("font-medium")
        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Delete",
                icon="delete",
                on_click=lambda: (_delete_many(task_ids), dialog.close()),
            ).props("color=red")
    dialog.open()


def _save_edit(task_id: int, title, category, start, end, notes, dialog: ui.dialog) -> None:
    if not title.value:
        ui.notify("Title is required", color="negative")
        return
    with get_session() as session:
        task = get_owned(session, Task, task_id)
        if not task:
            return
        task.title = title.value
        task.category = category.value or None
        task.start_time = _parse_time(start.value)
        task.end_time = _parse_time(end.value)
        task.notes = notes.value or None
        session.add(task)
        session.commit()
    dialog.close()
    _day_strip.refresh()


def _open_edit_dialog(task: Task) -> None:
    with ui.dialog() as dialog, ui.card().classes("gap-2 min-w-[320px]"):
        ui.label("Edit task").classes("font-medium")
        title = ui.input("Title", value=task.title).classes("w-full")
        with ui.row().classes("gap-2"):
            start = time_field("Start", _time_str(task.start_time))
            end = time_field("End", _time_str(task.end_time))
            link_time_range(start, end)
            category = category_select(task.category)
        notes = ui.input("Notes", value=task.notes or "").classes("w-full")
        with ui.row().classes("justify-between w-full"):
            ui.button("Delete", icon="delete", on_click=lambda: (_delete(task.id), dialog.close())).props(
                "flat color=red"
            )
            with ui.row().classes("gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Save",
                    on_click=lambda: _save_edit(task.id, title, category, start, end, notes, dialog),
                )
    dialog.open()


def _add(title: ui.input, start, end, category, notes: ui.input) -> None:
    if not title.value:
        ui.notify("Title is required", color="negative")
        return
    with get_session() as session:
        session.add(
            Task(
                owner=current_owner(),
                title=title.value,
                notes=notes.value or None,
                category=category.value or None,
                scheduled_date=date.today(),
                start_time=_parse_time(start.value),
                end_time=_parse_time(end.value),
            )
        )
        session.commit()
    _day_strip.refresh()


@ui.page("/")
def today_page() -> None:
    with frame("Today"):
        _day_strip()
