from datetime import date, time
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Schedule, ScheduleSlot, ScheduleOverride


async def get_all_schedules(session: AsyncSession) -> list[Schedule]:
    result = await session.execute(
        select(Schedule).options(selectinload(Schedule.slots)).order_by(Schedule.is_default.desc(), Schedule.name)
    )
    return list(result.scalars().all())


async def get_default_schedule(session: AsyncSession) -> Optional[Schedule]:
    result = await session.execute(
        select(Schedule)
        .where(Schedule.is_default == True)
        .options(selectinload(Schedule.slots))
    )
    return result.scalar_one_or_none()


async def create_schedule(session: AsyncSession, name: str, slots: list[tuple[int, time, time]], set_default: bool = False) -> Schedule:
    if set_default:
        await session.execute(update(Schedule).values(is_default=False))

    sched = Schedule(name=name, is_default=set_default)
    session.add(sched)
    await session.flush()

    for num, start, end in slots:
        slot = ScheduleSlot(schedule_id=sched.id, lesson_number=num, start_time=start, end_time=end)
        session.add(slot)

    await session.commit()
    await session.refresh(sched)
    return sched


async def set_default_schedule(session: AsyncSession, schedule_id: int) -> bool:
    await session.execute(update(Schedule).values(is_default=False))
    result = await session.execute(
        update(Schedule).where(Schedule.id == schedule_id).values(is_default=True).returning(Schedule.id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


async def add_override(session: AsyncSession, target_date: date, schedule_id: int) -> ScheduleOverride:
    # Remove existing override for this date if any
    existing = await session.execute(
        select(ScheduleOverride).where(ScheduleOverride.override_date == target_date)
    )
    ex = existing.scalar_one_or_none()
    if ex:
        ex.schedule_id = schedule_id
    else:
        ex = ScheduleOverride(override_date=target_date, schedule_id=schedule_id)
        session.add(ex)
    await session.commit()
    return ex


def parse_schedule_file(content: str) -> tuple[Optional[str], list[tuple[int, time, time]]]:
    """
    Parse schedule txt file:
    назва=My Schedule Name
    1=08:00-09:20
    2=09:40-11:00
    ...
    Returns (name, [(lesson_number, start_time, end_time), ...])
    """
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
    name = None
    slots = []

    for line in lines:
        if not "=" in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key.lower() in ("назва", "name"):
            name = value
            continue

        try:
            lesson_num = int(key)
            parts = value.split("-")
            if len(parts) != 2:
                continue
            sh, sm = map(int, parts[0].strip().split(":"))
            eh, em = map(int, parts[1].strip().split(":"))
            slots.append((lesson_num, time(sh, sm), time(eh, em)))
        except (ValueError, AttributeError):
            continue

    slots.sort(key=lambda x: x[0])
    return name, slots
