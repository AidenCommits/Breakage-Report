
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from database import get_connection

LOCAL_TIMEZONE = ZoneInfo("America/New_York")


def get_financial_events():
    """Retrieve financial events from SQLite."""

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                f.event_id,
                f.item_id,
                f.event_type,
                f.amount,
                f.recorded_at,
                d.job_id,
                d.job_name,
                d.cost_type
            FROM financial_events AS f
            JOIN damaged_items AS d
              ON f.item_id = d.item_id
            ORDER BY f.recorded_at, f.event_id
        """).fetchall()

    events = []

    for row in rows:
        event = dict(row)

        event["amount"] = Decimal(event["amount"])

        event["recorded_at"] = datetime.fromisoformat(
            event["recorded_at"].replace("Z", "+00:00")
        )

        events.append(event)

    return events


def get_week_start(date):
    """Return Monday at midnight in Eastern time."""

    local_date = date.astimezone(LOCAL_TIMEZONE)

    return (
        local_date - timedelta(days=local_date.weekday())
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def calculate_analytics(events, now=None):
    """Calculate financial metrics for the previous completed week."""

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Previous completed Monday-Sunday period.
    current_week_start = get_week_start(now)
    week_start = current_week_start - timedelta(days=7)
    week_end = current_week_start

    weekly_total = Decimal("0")
    cumulative_total = Decimal("0")

    weekly_by_job = defaultdict(lambda: Decimal("0"))
    weekly_history = defaultdict(lambda: Decimal("0"))

    for event in events:
        amount = event["amount"]
        recorded_at = event["recorded_at"]

        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        # Ignore future-dated events.
        if recorded_at > now:
            continue

        cumulative_total += amount

        event_week = get_week_start(recorded_at)
        weekly_history[event_week] += amount

        if week_start <= recorded_at < week_end:
            weekly_total += amount

            job_name = event["job_name"] or event["job_id"]
            weekly_by_job[job_name] += amount

    # Build history through the previous completed week.
    if weekly_history:
        first_week = min(weekly_history)
    else:
        first_week = week_start

    history = []
    current_week = first_week

    while current_week < week_end:
        history.append({
            "week_start": current_week,
            "total": weekly_history[current_week],
        })

        current_week += timedelta(days=7)

    if history:
        average_weekly_loss = (
            sum(
                (week["total"] for week in history),
                Decimal("0"),
            ) / Decimal(len(history))
        )
    else:
        average_weekly_loss = Decimal("0")

    # Calculate projections AFTER weekly totals are finalized.
    annualized_projection = weekly_total * Decimal("52")
    annualized_historical = average_weekly_loss * Decimal("52")

    return {
        "week_start": week_start,
        "week_end": week_end,
        "weekly_total": weekly_total,
        "cumulative_total": cumulative_total,
        "weekly_by_job": dict(weekly_by_job),
        "weekly_history": history,
        "average_weekly_loss": average_weekly_loss,
        "annualized_projection": annualized_projection,
        "annualized_historical": annualized_historical,
    }
