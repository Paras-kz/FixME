from datetime import date, timedelta

from nicegui import ui
from sqlmodel import select

from components import stat_tile
from db import get_session
from identity import current_owner
from layout import frame
from models import HabitLog, PomodoroSession, Task

BLOCKS = [("Morning", 6, 12), ("Afternoon", 12, 17), ("Evening", 17, 21), ("Night", 21, 30)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _block_for(hour: int) -> int:
    for i, (_, start, end) in enumerate(BLOCKS):
        if start <= hour < end or (end > 24 and hour < end - 24):
            return i
    return len(BLOCKS) - 1


def _reviewed_tasks(since: date) -> list[Task]:
    with get_session() as session:
        stmt = select(Task).where(
            Task.owner == current_owner(),
            Task.scheduled_date >= since,
            Task.review_status.is_not(None),
        )
        return list(session.exec(stmt))


def _adherence_pct(tasks: list[Task]) -> float:
    if not tasks:
        return 0.0
    score = sum(1.0 if t.review_status == "followed" else 0.5 if t.review_status == "partial" else 0.0 for t in tasks)
    return round(100 * score / len(tasks), 1)


def _weekly_series() -> tuple[list[str], list[float]]:
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    tasks = _reviewed_tasks(days[0])
    by_day = {d: [t for t in tasks if t.scheduled_date == d] for d in days}
    labels = [d.strftime("%a %d") for d in days]
    values = [_adherence_pct(by_day[d]) for d in days]
    return labels, values


def _heatmap_data() -> list[list[int | float]]:
    tasks = [t for t in _reviewed_tasks(date.today() - timedelta(days=27)) if t.start_time]
    buckets: dict[tuple[int, int], list[Task]] = {}
    for t in tasks:
        key = (t.scheduled_date.weekday(), _block_for(t.start_time.hour))
        buckets.setdefault(key, []).append(t)
    return [
        [wd, blk, _adherence_pct(items)]
        for (wd, blk), items in buckets.items()
    ]


def _pomodoro_stats(since: date) -> tuple[int, int]:
    with get_session() as session:
        stmt = select(Task).where(Task.owner == current_owner(), Task.scheduled_date >= since)
        tasks = session.exec(stmt).all()
    return sum(t.estimated_pomodoros for t in tasks), sum(t.completed_pomodoros for t in tasks)


def _habit_calendar() -> list[list]:
    since = date.today() - timedelta(days=29)
    with get_session() as session:
        stmt = select(HabitLog).where(HabitLog.owner == current_owner(), HabitLog.log_date >= since)
        logs = session.exec(stmt).all()
    counts: dict[date, int] = {}
    for log in logs:
        counts[log.log_date] = counts.get(log.log_date, 0) + 1
    return [[d.isoformat(), c] for d, c in counts.items()]


def _summary_text() -> str:
    this_week = _adherence_pct(_reviewed_tasks(date.today() - timedelta(days=6)))
    last_week = _adherence_pct(
        [
            t
            for t in _reviewed_tasks(date.today() - timedelta(days=13))
            if t.scheduled_date < date.today() - timedelta(days=6)
        ]
    )
    delta = round(this_week - last_week, 1)
    trend = "up" if delta > 0 else "down" if delta < 0 else "flat"

    heat = _heatmap_data()
    weakest = min(heat, key=lambda r: r[2], default=None)
    weak_text = (
        f"Your weakest slot is {WEEKDAYS[weakest[0]]} {BLOCKS[weakest[1]][0]} ({weakest[2]}% followed)."
        if weakest
        else "Not enough reviewed data yet to spot a weak slot."
    )
    return f"This week's adherence is {this_week}% ({trend} {abs(delta)} pts vs last week). {weak_text}"


@ui.page("/dashboard")
def dashboard_page() -> None:
    with frame("Dashboard"):
        ui.label(_summary_text()).classes("text-neutral-300")

        labels, values = _weekly_series()
        ui.echart(
            {
                "xAxis": {"type": "category", "data": labels},
                "yAxis": {"type": "value", "max": 100, "name": "% followed"},
                "series": [{"type": "bar", "data": values, "itemStyle": {"color": "#6366f1"}}],
            }
        ).classes("w-full h-64")

        heat = _heatmap_data()
        ui.echart(
            {
                "tooltip": {"position": "top"},
                "grid": {"height": "60%", "top": "10%"},
                "xAxis": {"type": "category", "data": WEEKDAYS, "splitArea": {"show": True}},
                "yAxis": {
                    "type": "category",
                    "data": [b[0] for b in BLOCKS],
                    "splitArea": {"show": True},
                },
                "visualMap": {
                    "min": 0,
                    "max": 100,
                    "calculable": True,
                    "orient": "horizontal",
                    "bottom": 0,
                    "inRange": {"color": ["#3f3f46", "#6366f1"]},
                },
                "series": [
                    {
                        "type": "heatmap",
                        "data": heat,
                        "label": {"show": False},
                    }
                ],
            }
        ).classes("w-full h-64")

        planned, completed = _pomodoro_stats(date.today() - timedelta(days=6))
        with ui.row().classes("gap-4"):
            stat_tile("Pomodoros planned", str(planned), "flag")
            stat_tile("Pomodoros completed", str(completed), "local_fire_department")

        cal_range = [(date.today() - timedelta(days=29)).isoformat(), date.today().isoformat()]
        ui.echart(
            {
                "tooltip": {},
                "visualMap": {
                    "min": 0,
                    "max": 5,
                    "calculable": True,
                    "orient": "horizontal",
                    "bottom": 0,
                    "inRange": {"color": ["#3f3f46", "#22c55e"]},
                },
                "calendar": {"range": cal_range, "cellSize": [16, 16]},
                "series": [
                    {"type": "heatmap", "coordinateSystem": "calendar", "data": _habit_calendar()}
                ],
            }
        ).classes("w-full h-40")
