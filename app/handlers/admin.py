from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.admin import (
    admin_panel_keyboard, admin_calendars_keyboard, admin_calendar_actions_keyboard,
    confirm_keyboard, admin_schedules_keyboard, schedules_list_keyboard,
    admin_admins_keyboard, admins_list_keyboard
)
from app.keyboards.navigation import main_menu_keyboard
from app.models import User, CalendarType
from app.models.database import async_session_maker
from app.services.calendars import (
    get_all_calendars, get_calendar, toggle_calendar, delete_calendar,
    parse_calendars_file, create_calendar
)
from app.services.bell_schedule import (
    get_all_schedules, create_schedule, set_default_schedule,
    add_override, parse_schedule_file, get_default_schedule
)
from app.services.users import get_all_admins, set_user_admin, get_user
from app.keyboards.calendar_widget import build_calendar
from datetime import date

router = Router()


class IsAdmin(Filter):
    async def __call__(self, event, db_user: User) -> bool:
        return db_user.is_admin


# Apply admin filter to all handlers in this router
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())


class AdminStates(StatesGroup):
    waiting_calendars_file = State()
    waiting_schedule_file = State()
    waiting_schedule_name = State()
    waiting_admin_id = State()
    waiting_override_schedule_id = State()
    waiting_override_date = State()


# ── Admin Panel ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>Адмін-панель</b>\n\nОберіть розділ:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Calendars management ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_calendars")
async def cb_admin_calendars(call: CallbackQuery):
    await call.message.edit_text(
        "📁 <b>Керування календарями</b>",
        reply_markup=admin_calendars_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cal_list:"))
async def cb_admin_cal_list(call: CallbackQuery):
    async with async_session_maker() as session:
        calendars = await get_all_calendars(session, active_only=False)

    if not calendars:
        await call.answer("Немає жодного календаря", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for cal in calendars:
        status = "✅" if cal.is_active else "⏸"
        type_label = "Гр." if cal.type == CalendarType.GROUP else "Вик."
        builder.row(InlineKeyboardButton(
            text=f"{status} [{type_label}] {cal.name}",
            callback_data=f"admin_cal_info:{cal.id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_calendars"))

    await call.message.edit_text(
        f"📋 <b>Всі календарі</b> ({len(calendars)} шт.)",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cal_info:"))
async def cb_admin_cal_info(call: CallbackQuery):
    calendar_id = int(call.data.split(":")[1])
    async with async_session_maker() as session:
        cal = await get_calendar(session, calendar_id)

    if not cal:
        await call.answer("Не знайдено", show_alert=True)
        return

    type_label = "Група" if cal.type == CalendarType.GROUP else "Викладач"
    status = "Активний ✅" if cal.is_active else "Деактивований ⏸"
    text = (
        f"📅 <b>{cal.name}</b>\n"
        f"Тип: {type_label}\n"
        f"Статус: {status}\n"
        f"URL: <code>{cal.ical_url[:60]}...</code>"
    )
    await call.message.edit_text(
        text,
        reply_markup=admin_calendar_actions_keyboard(calendar_id, cal.is_active),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cal_toggle:"))
async def cb_admin_cal_toggle(call: CallbackQuery):
    calendar_id = int(call.data.split(":")[1])
    async with async_session_maker() as session:
        new_state = await toggle_calendar(session, calendar_id)
    status = "активовано ✅" if new_state else "деактивовано ⏸"
    await call.answer(f"Календар {status}")
    # Refresh info
    async with async_session_maker() as session:
        cal = await get_calendar(session, calendar_id)
    type_label = "Група" if cal.type == CalendarType.GROUP else "Викладач"
    status_text = "Активний ✅" if cal.is_active else "Деактивований ⏸"
    await call.message.edit_text(
        f"📅 <b>{cal.name}</b>\nТип: {type_label}\nСтатус: {status_text}",
        reply_markup=admin_calendar_actions_keyboard(calendar_id, cal.is_active),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_cal_delete:"))
async def cb_admin_cal_delete_confirm(call: CallbackQuery):
    calendar_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        "⚠️ Ви впевнені що хочете видалити цей календар?\nВсі збережені посилання користувачів теж видаляться.",
        reply_markup=confirm_keyboard(f"admin_cal_delete_ok:{calendar_id}", "admin_cal_list:0"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cal_delete_ok:"))
async def cb_admin_cal_delete_ok(call: CallbackQuery):
    calendar_id = int(call.data.split(":")[1])
    async with async_session_maker() as session:
        await delete_calendar(session, calendar_id)
    await call.answer("Видалено ✅")
    await call.message.edit_text(
        "📁 <b>Керування календарями</b>",
        reply_markup=admin_calendars_keyboard(),
        parse_mode="HTML",
    )


# ── Upload calendars from file ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_cal_upload")
async def cb_admin_cal_upload(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📤 <b>Завантаження календарів</b>\n\n"
        "Надішліть .txt файл у форматі:\n"
        "<code>тип=група\n"
        "ІП-31=https://calendar.google.com/...\n"
        "ІП-32=xxxxx@group.calendar.google.com</code>\n\n"
        "або <code>тип=викладач</code> для викладачів.",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_calendars_file)
    await call.answer()


@router.message(AdminStates.waiting_calendars_file, F.document)
async def handle_calendars_file(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.endswith(".txt"):
        await message.answer("Потрібен .txt файл")
        return

    file = await message.bot.get_file(doc.file_id)
    content_bytes = await message.bot.download_file(file.file_path)
    content = content_bytes.read().decode("utf-8")

    cal_type, entries = parse_calendars_file(content)

    if not cal_type:
        await message.answer("❌ Не вдалось визначити тип. Перевірте рядок 'тип=група' або 'тип=викладач'")
        return

    if not entries:
        await message.answer("❌ Не знайдено жодного запису")
        return

    type_label = "Групи" if cal_type == CalendarType.GROUP else "Викладачі"
    preview = "\n".join(f"• {name}" for name, _ in entries[:10])
    if len(entries) > 10:
        preview += f"\n... та ще {len(entries) - 10}"

    await state.update_data(entries=entries, cal_type=cal_type.value)
    await message.answer(
        f"📋 <b>Превью ({type_label})</b> — {len(entries)} записів:\n\n{preview}\n\nПідтвердити завантаження?",
        reply_markup=confirm_keyboard("admin_cal_upload_confirm", "admin_calendars"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_cal_upload_confirm")
async def cb_admin_cal_upload_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    entries = data.get("entries", [])
    cal_type = CalendarType(data.get("cal_type"))

    async with async_session_maker() as session:
        count = 0
        for name, url in entries:
            await create_calendar(session, name, url, cal_type)
            count += 1

    await state.clear()
    await call.answer(f"✅ Завантажено {count} календарів")
    await call.message.edit_text(
        f"✅ Успішно додано <b>{count}</b> календарів.",
        reply_markup=admin_calendars_keyboard(),
        parse_mode="HTML",
    )


# ── Bell Schedules ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_schedules")
async def cb_admin_schedules(call: CallbackQuery):
    await call.message.edit_text(
        "🕐 <b>Графіки дзвінків</b>",
        reply_markup=admin_schedules_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "admin_sched_list")
async def cb_admin_sched_list(call: CallbackQuery):
    async with async_session_maker() as session:
        schedules = await get_all_schedules(session)

    if not schedules:
        await call.answer("Немає жодного графіку", show_alert=True)
        return

    await call.message.edit_text(
        "📋 <b>Графіки дзвінків</b>\nОберіть для встановлення основним:",
        reply_markup=schedules_list_keyboard(schedules, action="set_default"),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_sched_set_default:"))
async def cb_sched_set_default(call: CallbackQuery):
    sched_id = int(call.data.split(":")[1])
    async with async_session_maker() as session:
        await set_default_schedule(session, sched_id)
        schedules = await get_all_schedules(session)

    await call.answer("✅ Основний графік змінено")
    await call.message.edit_reply_markup(
        reply_markup=schedules_list_keyboard(schedules, action="set_default")
    )


@router.callback_query(F.data == "admin_sched_upload")
async def cb_admin_sched_upload(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📤 <b>Завантаження графіку дзвінків</b>\n\n"
        "Надішліть .txt файл у форматі:\n"
        "<code>назва=Основний розклад\n"
        "1=08:00-09:20\n"
        "2=09:40-11:00\n"
        "3=11:20-12:40</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_schedule_file)
    await call.answer()


@router.message(AdminStates.waiting_schedule_file, F.document)
async def handle_schedule_file(message: Message, state: FSMContext):
    doc = message.document
    file = await message.bot.get_file(doc.file_id)
    content_bytes = await message.bot.download_file(file.file_path)
    content = content_bytes.read().decode("utf-8")

    name, slots = parse_schedule_file(content)

    if not slots:
        await message.answer("❌ Не вдалось розпарсити графік. Перевірте формат файлу.")
        return

    if not name:
        name = "Без назви"

    preview = "\n".join(f"{num}. {s.strftime('%H:%M')}–{e.strftime('%H:%M')}" for num, s, e in slots)
    await state.update_data(sched_name=name, sched_slots=[(n, s.isoformat(), e.isoformat()) for n, s, e in slots])

    async with async_session_maker() as session:
        has_default = await get_default_schedule(session)

    set_default_text = "" if has_default else "\n\n<i>Це перший графік — буде встановлений основним автоматично.</i>"

    await message.answer(
        f"📋 <b>{name}</b> — {len(slots)} уроків:\n\n{preview}{set_default_text}\n\nПідтвердити завантаження?",
        reply_markup=confirm_keyboard("admin_sched_upload_confirm", "admin_schedules"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_sched_upload_confirm")
async def cb_sched_upload_confirm(call: CallbackQuery, state: FSMContext):
    from datetime import time as dtime
    data = await state.get_data()
    name = data["sched_name"]
    raw_slots = data["sched_slots"]
    slots = [(n, dtime.fromisoformat(s), dtime.fromisoformat(e)) for n, s, e in raw_slots]

    async with async_session_maker() as session:
        has_default = await get_default_schedule(session)
        sched = await create_schedule(session, name, slots, set_default=not has_default)

    await state.clear()
    await call.answer("✅ Графік збережено")
    await call.message.edit_text(
        f"✅ Графік <b>{name}</b> збережено.",
        reply_markup=admin_schedules_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_sched_override")
async def cb_sched_override(call: CallbackQuery, state: FSMContext):
    async with async_session_maker() as session:
        schedules = await get_all_schedules(session)

    if not schedules:
        await call.answer("Немає жодного графіку", show_alert=True)
        return

    await call.message.edit_text(
        "📅 Оберіть графік для прив'язки до конкретної дати:",
        reply_markup=schedules_list_keyboard(schedules, action="override_pick"),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_sched_override_pick:"))
async def cb_sched_override_pick(call: CallbackQuery, state: FSMContext):
    sched_id = int(call.data.split(":")[1])
    await state.update_data(override_sched_id=sched_id)
    today = date.today()
    kb = build_calendar(today.year, today.month, mode="day", context=f"override:{sched_id}")
    await call.message.edit_text("🗓 Оберіть дату для прив'язки:", reply_markup=kb)
    await call.answer()


# Override date selected from calendar widget
@router.callback_query(F.data.startswith("datepicker:day:") & F.data.contains(":override:"))
async def cb_override_date_selected(call: CallbackQuery):
    parts = call.data.split(":")
    # datepicker:day:YYYY-MM-DD:override:sched_id
    date_str = parts[2]
    sched_id = int(parts[4])
    target_date = date.fromisoformat(date_str)

    async with async_session_maker() as session:
        await add_override(session, target_date, sched_id)

    await call.answer(f"✅ Графік прив'язано до {date_str}")
    await call.message.edit_text(
        f"✅ Графік прив'язано до <b>{date_str}</b>.",
        reply_markup=admin_schedules_keyboard(),
        parse_mode="HTML",
    )


# ── Admins management ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_admins")
async def cb_admin_admins(call: CallbackQuery):
    await call.message.edit_text(
        "👥 <b>Адміністратори</b>",
        reply_markup=admin_admins_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "admin_list_admins")
async def cb_admin_list_admins(call: CallbackQuery, db_user: User):
    async with async_session_maker() as session:
        admins = await get_all_admins(session)

    lines = []
    for admin in admins:
        name = admin.full_name or admin.username or str(admin.id)
        you = " (ви)" if admin.id == db_user.id else ""
        lines.append(f"• {name}{you} — <code>{admin.id}</code>")

    await call.message.edit_text(
        f"👥 <b>Адміністратори</b> ({len(admins)}):\n\n" + "\n".join(lines),
        reply_markup=admins_list_keyboard(admins, db_user.id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "admin_add_admin")
async def cb_admin_add_admin(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "➕ Надішліть <b>Telegram ID</b> користувача якого хочете зробити адміном.\n\n"
        "<i>Користувач має попередньо написати боту хоча б раз.</i>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_admin_id)
    await call.answer()


@router.message(AdminStates.waiting_admin_id)
async def handle_new_admin_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введіть числовий Telegram ID")
        return

    async with async_session_maker() as session:
        success = await set_user_admin(session, target_id, True)

    if success:
        await message.answer(f"✅ Користувач <code>{target_id}</code> тепер адмін.", parse_mode="HTML")
    else:
        await message.answer("❌ Користувача не знайдено. Переконайтесь що він писав боту.")

    await state.clear()


@router.callback_query(F.data.startswith("admin_remove_admin:"))
async def cb_remove_admin(call: CallbackQuery, db_user: User):
    target_id = int(call.data.split(":")[1])
    if target_id == db_user.id:
        await call.answer("Не можна видалити самого себе", show_alert=True)
        return

    async with async_session_maker() as session:
        await set_user_admin(session, target_id, False)
        admins = await get_all_admins(session)

    await call.answer("✅ Адміна знято")
    await call.message.edit_reply_markup(
        reply_markup=admins_list_keyboard(admins, db_user.id)
    )
