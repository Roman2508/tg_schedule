from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Calendar, CalendarType


async def get_all_calendars(session: AsyncSession, active_only: bool = True) -> list[Calendar]:
    q = select(Calendar)
    if active_only:
        q = q.where(Calendar.is_active == True)
    q = q.order_by(Calendar.type, Calendar.name)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_calendars_by_type(session: AsyncSession, cal_type: CalendarType, active_only: bool = True) -> list[Calendar]:
    q = select(Calendar).where(Calendar.type == cal_type)
    if active_only:
        q = q.where(Calendar.is_active == True)
    q = q.order_by(Calendar.name)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_calendar(session: AsyncSession, calendar_id: int) -> Optional[Calendar]:
    result = await session.execute(select(Calendar).where(Calendar.id == calendar_id))
    return result.scalar_one_or_none()


async def create_calendar(session: AsyncSession, name: str, ical_url: str, cal_type: CalendarType) -> Calendar:
    cal = Calendar(name=name, ical_url=ical_url, type=cal_type)
    session.add(cal)
    await session.commit()
    await session.refresh(cal)
    return cal


async def toggle_calendar(session: AsyncSession, calendar_id: int) -> Optional[bool]:
    cal = await get_calendar(session, calendar_id)
    if not cal:
        return None
    cal.is_active = not cal.is_active
    await session.commit()
    return cal.is_active


async def delete_calendar(session: AsyncSession, calendar_id: int) -> bool:
    result = await session.execute(
        delete(Calendar).where(Calendar.id == calendar_id).returning(Calendar.id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


def build_ical_url(raw: str) -> str:
    """Build full iCal URL from raw input (full URL or calendar ID)."""
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    calendar_id = raw.replace("@", "%40")
    return f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics"


def parse_calendars_file(content: str) -> tuple[Optional[CalendarType], list[tuple[str, str]]]:
    """
    Parse txt file with format:
    тип=група|викладач
    Name=ical_url_or_id
    ...
    Returns (type, [(name, url), ...])
    """
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
    if not lines:
        return None, []

    cal_type = None
    entries = []

    for line in lines:
        if line.lower().startswith("тип="):
            value = line.split("=", 1)[1].strip().lower()
            if value in ("група", "group"):
                cal_type = CalendarType.GROUP
            elif value in ("викладач", "teacher"):
                cal_type = CalendarType.TEACHER
            continue
        if "=" in line:
            name, url_or_id = line.split("=", 1)
            entries.append((name.strip(), build_ical_url(url_or_id.strip())))

    return cal_type, entries
