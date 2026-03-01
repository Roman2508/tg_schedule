from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.keyboards.navigation import main_menu_keyboard
from app.models import User

router = Router()


def get_welcome_text() -> str:
    return (
        "👋 <b>Вітаю!</b>\n\n"
        "Це бот для перегляду розкладу занять.\n\n"
        "• <b>Мій розклад</b> — переглянути збережені розклади\n"
        "• <b>Знайти розклад</b> — пошук по групі або викладачу"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User):
    await message.answer(
        get_welcome_text(),
        reply_markup=main_menu_keyboard(is_admin=db_user.is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, db_user: User):
    await call.message.edit_text(
        get_welcome_text(),
        reply_markup=main_menu_keyboard(is_admin=db_user.is_admin),
        parse_mode="HTML",
    )
    await call.answer()
