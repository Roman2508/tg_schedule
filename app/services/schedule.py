from datetime import date, time, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Schedule, ScheduleSlot, ScheduleOverride


async def get_schedule_for_date(session: AsyncSession, target_date: date) -> Optional[Schedule]:
    """Return the bell schedule applicable for a given date."""
    # Check override first
    override_result = await session.execute(
        select(ScheduleOverride)
        .where(ScheduleOverride.override_date == target_date)
        .options(selectinload(ScheduleOverride.schedule).selectinload(Schedule.slots))
    )
    override = override_result.scalar_one_or_none()
    if override:
        return override.schedule

    # Fall back to default schedule
    result = await session.execute(
        select(Schedule)
        .where(Schedule.is_default == True)
        .options(selectinload(Schedule.slots))
    )
    return result.scalar_one_or_none()


def match_lesson_number(event_start_time: str, slots: list[ScheduleSlot]) -> Optional[int]:
    """Find lesson number by matching event start time to a slot (±5 min tolerance)."""
    try:
        h, m = map(int, event_start_time.split(":"))
        event_minutes = h * 60 + m
    except Exception:
        return None

    for slot in slots:
        slot_minutes = slot.start_time.hour * 60 + slot.start_time.minute
        if abs(event_minutes - slot_minutes) <= 5:
            return slot.lesson_number

    return None


LESSON_EMOJIS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣"}


def format_lesson_number(n: Optional[int]) -> str:
    if n and n in LESSON_EMOJIS:
        return LESSON_EMOJIS[n]
    return "▪️"
