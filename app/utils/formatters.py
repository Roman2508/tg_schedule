from datetime import date, timedelta
from typing import Optional

from app.services.schedule import match_lesson_number, format_lesson_number
from app.models import ScheduleSlot

UA_WEEKDAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
UA_MONTHS = [
    "", "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
]
SHORT_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def format_date_ua(d: date) -> str:
    weekday = UA_WEEKDAYS[d.weekday()]
    return f"{weekday}, {d.day} {UA_MONTHS[d.month]} {d.year}"


def format_date_short(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}"


def format_week_range(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    if week_start.month == week_end.month:
        return f"{week_start.day}–{week_end.day} {UA_MONTHS[week_start.month]} {week_start.year}"
    return f"{week_start.day} {UA_MONTHS[week_start.month]} – {week_end.day} {UA_MONTHS[week_end.month]} {week_start.year}"


def get_week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def format_day_schedule(
    calendar_name: str,
    target_date: date,
    events: list[dict],
    slots: list[ScheduleSlot],
) -> str:
    header = f"📅 <b>{calendar_name}</b>\n{format_date_ua(target_date)}\n"

    if not events:
        return header + "\n🎉 Занять немає"

    lines = [header]
    for event in events:
        lesson_num = match_lesson_number(event["start_time"], slots)
        emoji = format_lesson_number(lesson_num)

        time_str = event["start_time"]
        if event["end_time"]:
            time_str += f"–{event['end_time']}"

        lines.append(f"{emoji}  <b>{time_str}</b>")
        lines.append(f"     {event['summary']}")

        details = []
        if event.get("location"):
            details.append(f"📍 {event['location']}")
        if event.get("description"):
            desc = event["description"][:100].strip()
            if desc:
                details.append(desc)
        if details:
            lines.append(f"     {' | '.join(details)}")

        lines.append("")  # spacing between lessons

    return "\n".join(lines).rstrip()


def format_week_schedule(
    calendar_name: str,
    week_start: date,
    events_by_date: dict[str, list[dict]],
    slots: list[ScheduleSlot],
) -> str:
    week_end = week_start + timedelta(days=6)
    header = f"📅 <b>{calendar_name}</b>\n{format_week_range(week_start)}\n"
    lines = [header]

    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.isoformat()
        weekday_name = f"{UA_WEEKDAYS[day.weekday()]}, {day.day} {UA_MONTHS[day.month]}"

        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📆 <b>{weekday_name}</b>")

        day_events = events_by_date.get(day_str, [])
        if not day_events:
            lines.append("     Занять немає 🎉")
        else:
            for event in day_events:
                lesson_num = match_lesson_number(event["start_time"], slots)
                emoji = format_lesson_number(lesson_num)
                lines.append(f"{emoji} {event['start_time']}  {event['summary']}")

        lines.append("")

    return "\n".join(lines).rstrip()
