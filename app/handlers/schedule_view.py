from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.navigation import day_nav_keyboard, week_nav_keyboard
from app.keyboards.calendar_widget import build_calendar, DAY_SELECT, WEEK_SELECT, MONTH_NAV, CAL_PREFIX
from app.models import User
from app.models.database import async_session_maker
from app.services.calendars import get_calendar
from app.services.ical import get_events
from app.services.schedule import get_schedule_for_date
from app.utils.formatters import format_day_schedule, format_week_schedule, get_week_start

router = Router()


async def _render_day(call: CallbackQuery, target_date: date, calendar_id: int):
    async with async_session_maker() as session:
        cal = await get_calendar(session, calendar_id)
        if not cal:
            await call.answer("Календар не знайдено", show_alert=True)
            return

        bell = await get_schedule_for_date(session, target_date)
        slots = bell.slots if bell else []

    try:
        events = await get_events(cal.build_ical_url(), target_date, target_date)
    except Exception as e:
        await call.answer(f"Помилка завантаження: {e}", show_alert=True)
        return

    text = format_day_schedule(cal.name, target_date, events, slots)
    keyboard = day_nav_keyboard(target_date, calendar_id)

    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()


async def _render_week(call: CallbackQuery, week_start: date, calendar_id: int):
    week_end = week_start + timedelta(days=6)

    async with async_session_maker() as session:
        cal = await get_calendar(session, calendar_id)
        if not cal:
            await call.answer("Календар не знайдено", show_alert=True)
            return

        # Use slots from Monday's schedule as representative for the week
        bell = await get_schedule_for_date(session, week_start)
        slots = bell.slots if bell else []

    try:
        events = await get_events(cal.build_ical_url(), week_start, week_end)
    except Exception as e:
        await call.answer(f"Помилка завантаження: {e}", show_alert=True)
        return

    events_by_date: dict[str, list] = {}
    for event in events:
        d = event["date"]
        events_by_date.setdefault(d, []).append(event)

    text = format_week_schedule(cal.name, week_start, events_by_date, slots)
    keyboard = week_nav_keyboard(week_start, calendar_id)

    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()


# ── Day navigation ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("day:"))
async def cb_day_view(call: CallbackQuery):
    _, date_str, cal_id_str = call.data.split(":", 2)
    target_date = date.fromisoformat(date_str)
    calendar_id = int(cal_id_str)
    await _render_day(call, target_date, calendar_id)


@router.callback_query(F.data.startswith("my_cal_view:"))
async def cb_my_cal_view(call: CallbackQuery):
    # my_cal_view:calendar_id:date
    parts = call.data.split(":")
    calendar_id = int(parts[1])
    target_date = date.fromisoformat(parts[2])
    await _render_day(call, target_date, calendar_id)


# ── Week navigation ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("week:"))
async def cb_week_view(call: CallbackQuery):
    _, week_start_str, cal_id_str = call.data.split(":", 2)
    week_start = date.fromisoformat(week_start_str)
    calendar_id = int(cal_id_str)
    await _render_week(call, week_start, calendar_id)


# ── Date picker callbacks ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pick_day_date:"))
async def cb_pick_day_date(call: CallbackQuery):
    # pick_day_date:year:month:calendar_id
    parts = call.data.split(":")
    year, month, cal_id = int(parts[1]), int(parts[2]), parts[3]
    kb = build_calendar(year, month, mode="day", context=cal_id)
    await call.message.edit_text("🗓 Оберіть дату:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("pick_week_date:"))
async def cb_pick_week_date(call: CallbackQuery):
    # pick_week_date:year:month:calendar_id
    parts = call.data.split(":")
    year, month, cal_id = int(parts[1]), int(parts[2]), parts[3]
    kb = build_calendar(year, month, mode="week", context=cal_id)
    await call.message.edit_text(
        "🗓 Оберіть будь-який день потрібного тижня:",
        reply_markup=kb
    )
    await call.answer()


@router.callback_query(F.data.startswith(MONTH_NAV))
async def cb_month_nav(call: CallbackQuery):
    # datepicker:month:year:month:mode:context
    parts = call.data.split(":")
    year, month, mode = int(parts[2]), int(parts[3]), parts[4]
    context = ":".join(parts[5:])
    kb = build_calendar(year, month, mode=mode, context=context)
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith(DAY_SELECT))
async def cb_day_selected(call: CallbackQuery):
    # datepicker:day:YYYY-MM-DD:calendar_id
    parts = call.data.split(":")
    date_str = parts[2]
    cal_id = int(parts[3])
    target_date = date.fromisoformat(date_str)
    await _render_day(call, target_date, cal_id)


@router.callback_query(F.data.startswith(WEEK_SELECT))
async def cb_week_selected(call: CallbackQuery):
    # datepicker:week:YYYY-MM-DD:calendar_id
    parts = call.data.split(":")
    week_start_str = parts[2]
    cal_id = int(parts[3])
    week_start = date.fromisoformat(week_start_str)
    await _render_week(call, week_start, cal_id)


@router.callback_query(F.data.startswith(f"{CAL_PREFIX}:cancel"))
async def cb_datepicker_cancel(call: CallbackQuery):
    from app.keyboards.navigation import main_menu_keyboard
    from app.models import User
    db_user: User = call.bot.get("db_user")  # fallback
    await call.message.edit_text(
        "Скасовано. Повертаємось до меню.",
        reply_markup=main_menu_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "datepicker:ignore")
async def cb_ignore(call: CallbackQuery):
    await call.answer()
