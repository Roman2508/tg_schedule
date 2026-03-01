from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.models.database import async_session_maker
from app.services.users import get_or_create_user


class UserMiddleware(BaseMiddleware):
    """Auto-register users and inject user object into handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        telegram_user = None
        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

        if telegram_user:
            async with async_session_maker() as session:
                user = await get_or_create_user(
                    session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    full_name=telegram_user.full_name,
                )
                data["db_user"] = user
                data["db_session"] = session
                return await handler(event, data)

        return await handler(event, data)
