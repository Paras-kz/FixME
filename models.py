from datetime import date, datetime, time

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner: str = "owner"
    title: str
    notes: str | None = None
    category: str | None = None

    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None

    kanban_status: str = "backlog"  # backlog|todo|in_progress|done
    is_urgent: bool = False
    is_important: bool = False

    estimated_pomodoros: int = 0
    completed_pomodoros: int = 0

    review_status: str | None = None  # followed|partial|skipped
    actual_start: time | None = None
    actual_end: time | None = None
    review_note: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Habit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner: str = "owner"
    name: str
    color: str = "primary"


class HabitLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner: str = "owner"
    habit_id: int = Field(foreign_key="habit.id")
    log_date: date


class PomodoroSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner: str = "owner"
    task_id: int | None = Field(default=None, foreign_key="task.id")
    kind: str = "work"  # work|break
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    completed: bool = False
