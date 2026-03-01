from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import aiohttp
import recurring_ical_events
from icalendar import Calendar as iCalendar

from app.config import settings
from app.services.cache import cache

TZ = ZoneInfo(settings.TIMEZONE)


def _to_local_datetime(dt_value) -> Optional[datetime]:
    """Convert ical datetime/date to local timezone aware datetime."""
    if dt_value is None:
        return None
    if isinstance(dt_value, datetime):
        if dt_value.tzinfo is None:
            return dt_value.replace(tzinfo=TZ)
        return dt_value.astimezone(TZ)
    if isinstance(dt_value, date):
        return datetime(dt_value.year, dt_value.month, dt_value.day, tzinfo=TZ)
    return None


async def fetch_ical(url: str) -> bytes:
    """Download iCal content from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            return await resp.read()


def parse_events_for_range(ical_bytes: bytes, start: date, end: date) -> list[dict]:
    """Parse iCal and return events between start and end dates (inclusive)."""
    cal = iCalendar.from_ical(ical_bytes)
    events = recurring_ical_events.of(cal).between(
        datetime(start.year, start.month, start.day, 0, 0, tzinfo=TZ),
        datetime(end.year, end.month, end.day, 23, 59, tzinfo=TZ),
    )

    result = []
    for event in events:
        dtstart = _to_local_datetime(event.get("DTSTART").dt if event.get("DTSTART") else None)
        dtend = _to_local_datetime(event.get("DTEND").dt if event.get("DTEND") else None)
        if not dtstart:
            continue

        result.append({
            "summary": str(event.get("SUMMARY", "Без назви")),
            "location": str(event.get("LOCATION", "")) or None,
            "description": str(event.get("DESCRIPTION", "")) or None,
            "start": dtstart.isoformat(),
            "end": dtend.isoformat() if dtend else None,
            "date": dtstart.date().isoformat(),
            "start_time": dtstart.strftime("%H:%M"),
            "end_time": dtend.strftime("%H:%M") if dtend else None,
        })

    result.sort(key=lambda e: e["start"])
    return result


async def get_events(ical_url: str, start: date, end: date) -> list[dict]:
    """Get events with caching."""
    start_str = start.isoformat()
    end_str = end.isoformat()

    cached = await cache.get_events(ical_url, start_str, end_str)
    if cached is not None:
        return cached

    raw = await fetch_ical(ical_url)
    events = parse_events_for_range(raw, start, end)
    await cache.set_events(ical_url, start_str, end_str, events)
    return events
