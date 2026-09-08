from datetime import datetime

from nicegui import ui
from sqlmodel import select

from db import get_session
from identity import current_owner, get_owned
from layout import frame
from models import PomodoroSession, Task

WORK_SECONDS = 25 * 60
BREAK_SECONDS = 5 * 60


def _open_tasks() -> list[Task]:
    with get_session() as session:
        stmt = select(Task).where(Task.owner == current_owner(), Task.kanban_status != "done")
        return list(session.exec(stmt))


@ui.page("/pomodoro")
def pomodoro_page() -> None:
    state = {"remaining": WORK_SECONDS, "kind": "work", "running": False, "task_id": None}

    with frame("Pomodoro"):
        task_select = ui.select(
            {t.id: t.title for t in _open_tasks()}, label="Attach to task (optional)"
        ).classes("w-full")
        kind_label = ui.label("Work session").classes("text-neutral-400")
        clock = ui.label("25:00").classes("text-6xl font-bold")
        progress = ui.linear_progress(value=1.0).classes("w-full")

        def render() -> None:
            m, s = divmod(state["remaining"], 60)
            clock.text = f"{m:02d}:{s:02d}"
            total = WORK_SECONDS if state["kind"] == "work" else BREAK_SECONDS
            progress.value = state["remaining"] / total
            kind_label.text = "Work session" if state["kind"] == "work" else "Break"
            if state["running"]:
                toggle_btn.text, toggle_btn.icon = "Pause", "pause"
            elif state["remaining"] == total:
                toggle_btn.text, toggle_btn.icon = "Start", "play_arrow"
            else:
                toggle_btn.text, toggle_btn.icon = "Continue", "play_arrow"

        def finish() -> None:
            with get_session() as session:
                session.add(
                    PomodoroSession(
                        owner=current_owner(),
                        task_id=state["task_id"],
                        kind=state["kind"],
                        completed=True,
                        ended_at=datetime.utcnow(),
                    )
                )
                if state["kind"] == "work" and state["task_id"]:
                    task = get_owned(session, Task, state["task_id"])
                    if task:
                        task.completed_pomodoros += 1
                        session.add(task)
                session.commit()
            state["kind"] = "break" if state["kind"] == "work" else "work"
            state["remaining"] = BREAK_SECONDS if state["kind"] == "break" else WORK_SECONDS
            state["running"] = False
            ui.notify("Session complete!")
            render()

        def tick() -> None:
            if not state["running"]:
                return
            state["remaining"] -= 1
            if state["remaining"] <= 0:
                finish()
            else:
                render()

        def toggle() -> None:
            if state["running"]:
                state["running"] = False
            else:
                state["task_id"] = task_select.value
                state["running"] = True
            render()

        def reset() -> None:
            state["running"] = False
            state["kind"] = "work"
            state["remaining"] = WORK_SECONDS
            render()

        ui.timer(1.0, tick)

        with ui.row().classes("gap-2"):
            toggle_btn = ui.button("Start", icon="play_arrow", on_click=toggle)
            ui.button("Reset", icon="replay", on_click=reset)
