from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.navigation import (
    calendar_type_keyboard, calendars_list_keyboard, saved_calendars_keyboard,
    view_mode_keyboard, after_schedule_keyboard, main_menu_keyboard
)
from app.models import User, CalendarType
from app.models.database import async_session_maker
from app.services.calendars import get_calendars_by_type, get_calendar
from app.services.users import get_saved_calendars, save_calendar, remove_saved_calendar

router = Router()

# Temporary in-memory store for paginated calendar lists (per user)
_user_calendar_cache: dict[int, list] = {}


# ── My Schedule ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_schedule")
async def cb_my_schedule(call: CallbackQuery, db_user: User):
    async with async_session_maker() as session:
        saved = await get_saved_calendars(session, db_user.id)

    if not saved:
        await call.message.edit_text(
            "У вас немає збережених розкладів.\n\n"
            "Скористайтесь <b>Знайти розклад</b> щоб знайти і зберегти потрібний.",
            reply_markup=main_menu_keyboard(is_admin=db_user.is_admin),
            parse_mode="HTML",
        )
        await call.answer()
        return

    if len(saved) == 1:
        # Go directly to day view for the single saved calendar
        cal_id = saved[0].calendar_id
        today = date.today()
        await call.message.edit_text(
            "Завантаження розкладу...",
        )
        from app.handlers.schedule_view import _render_day
        await _render_day(call, today, cal_id)
        return

    # Multiple saved — let user choose
    await call.message.edit_text(
        "📅 <b>Мої розклади</b>\n\nОберіть розклад для перегляду:",
        reply_markup=saved_calendars_keyboard(saved),
        parse_mode="HTML",
    )
    await call.answer()


# ── Search Schedule ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "search_schedule")
async def cb_search_schedule(call: CallbackQuery):
    await call.message.edit_text(
        "🔍 <b>Знайти розклад</b>\n\nОберіть тип:",
        reply_markup=calendar_type_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("filter_type:"))
async def cb_filter_type(call: CallbackQuery, db_user: User):
    type_str = call.data.split(":")[1]
    cal_type = CalendarType.GROUP if type_str == "group" else CalendarType.TEACHER
    type_label = "Групи" if type_str == "group" else "Викладачі"

    async with async_session_maker() as session:
        calendars = await get_calendars_by_type(session, cal_type)

    if not calendars:
        await call.answer("Немає доступних календарів цього типу", show_alert=True)
        return

    # Cache for pagination
    _user_calendar_cache[db_user.id] = calendars

    await call.message.edit_text(
        f"🔍 <b>{type_label}</b>\n\nОберіть зі списку:",
        reply_markup=calendars_list_keyboard(calendars, page=0),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("cal_page:"))
async def cb_cal_page(call: CallbackQuery, db_user: User):
    parts = call.data.split(":")
    page = int(parts[1])
    suffix = parts[2]
    calendars = _user_calendar_cache.get(db_user.id, [])
    await call.message.edit_reply_markup(
        reply_markup=calendars_list_keyboard(calendars, page=page, suffix=suffix)
    )
    await call.answer()


@router.callback_query(F.data.startswith("cal_select:"))
async def cb_cal_selected(call: CallbackQuery, db_user: User):
    calendar_id = int(call.data.split(":")[1])
    today = date.today()

    async with async_session_maker() as session:
        saved = await get_saved_calendars(session, db_user.id)
        cal = await get_calendar(session, calendar_id)

    is_saved = any(sc.calendar_id == calendar_id for sc in saved)

    await call.message.edit_text(
        f"📅 <b>{cal.name}</b>\n\nОберіть формат перегляду:",
        reply_markup=after_schedule_keyboard(calendar_id, today, is_saved),
        parse_mode="HTML",
    )
    await call.answer()


# ── Save / Unsave calendar ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("save_cal:"))
async def cb_save_cal(call: CallbackQuery, db_user: User):
    calendar_id = int(call.data.split(":")[1])

    async with async_session_maker() as session:
        saved = await save_calendar(session, db_user.id, calendar_id)
        cal = await get_calendar(session, calendar_id)

    if saved:
        await call.answer("⭐ Розклад збережено!", show_alert=False)
    else:
        await call.answer("Вже збережено", show_alert=False)

    # Refresh keyboard to show unsave button
    today = date.today()
    await call.message.edit_reply_markup(
        reply_markup=after_schedule_keyboard(calendar_id, today, is_saved=True)
    )


@router.callback_query(F.data.startswith("unsave_cal:"))
async def cb_unsave_cal(call: CallbackQuery, db_user: User):
    calendar_id = int(call.data.split(":")[1])

    async with async_session_maker() as session:
        removed = await remove_saved_calendar(session, db_user.id, calendar_id)

    if removed:
        await call.answer("🗑 Видалено зі збережених", show_alert=False)
    else:
        await call.answer("Не знайдено", show_alert=False)

    today = date.today()
    await call.message.edit_reply_markup(
        reply_markup=after_schedule_keyboard(calendar_id, today, is_saved=False)
    )
