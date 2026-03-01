from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserRole, UserSavedCalendar, Calendar


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None, full_name: str = None) -> User:
    result = await session.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update info if changed
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == telegram_id))
    return result.scalar_one_or_none()


async def set_user_admin(session: AsyncSession, telegram_id: int, is_admin: bool) -> bool:
    user = await get_user(session, telegram_id)
    if not user:
        return False
    user.role = UserRole.ADMIN if is_admin else UserRole.USER
    await session.commit()
    return True


async def get_all_admins(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.role == UserRole.ADMIN))
    return list(result.scalars().all())


async def get_saved_calendars(session: AsyncSession, user_id: int) -> list[UserSavedCalendar]:
    result = await session.execute(
        select(UserSavedCalendar)
        .where(UserSavedCalendar.user_id == user_id)
        .options(selectinload(UserSavedCalendar.calendar))
    )
    return list(result.scalars().all())


async def save_calendar(session: AsyncSession, user_id: int, calendar_id: int, label: str = None) -> bool:
    """Save calendar for user. Returns False if already saved."""
    existing = await session.execute(
        select(UserSavedCalendar).where(
            UserSavedCalendar.user_id == user_id,
            UserSavedCalendar.calendar_id == calendar_id,
        )
    )
    if existing.scalar_one_or_none():
        return False
    entry = UserSavedCalendar(user_id=user_id, calendar_id=calendar_id, custom_label=label)
    session.add(entry)
    await session.commit()
    return True


async def remove_saved_calendar(session: AsyncSession, user_id: int, calendar_id: int) -> bool:
    result = await session.execute(
        delete(UserSavedCalendar).where(
            UserSavedCalendar.user_id == user_id,
            UserSavedCalendar.calendar_id == calendar_id,
        ).returning(UserSavedCalendar.id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None
