from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📁 Керування календарями", callback_data="admin_calendars"))
    builder.row(InlineKeyboardButton(text="🕐 Графіки дзвінків", callback_data="admin_schedules"))
    builder.row(InlineKeyboardButton(text="👥 Адміністратори", callback_data="admin_admins"))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def admin_calendars_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Завантажити з файлу", callback_data="admin_cal_upload"))
    builder.row(InlineKeyboardButton(text="📋 Переглянути всі", callback_data="admin_cal_list:0"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return builder.as_markup()


def admin_calendar_actions_keyboard(calendar_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    status_text = "⏸ Деактивувати" if is_active else "▶️ Активувати"
    builder.row(
        InlineKeyboardButton(text=status_text, callback_data=f"admin_cal_toggle:{calendar_id}"),
        InlineKeyboardButton(text="🗑 Видалити", callback_data=f"admin_cal_delete:{calendar_id}"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cal_list:0"))
    return builder.as_markup()


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Підтвердити", callback_data=yes_data),
        InlineKeyboardButton(text="❌ Скасувати", callback_data=no_data),
    )
    return builder.as_markup()


def admin_schedules_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Завантажити графік", callback_data="admin_sched_upload"))
    builder.row(InlineKeyboardButton(text="📋 Переглянути графіки", callback_data="admin_sched_list"))
    builder.row(InlineKeyboardButton(text="📅 Прив'язати до дати", callback_data="admin_sched_override"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return builder.as_markup()


def schedules_list_keyboard(schedules: list, action: str = "set_default") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sched in schedules:
        label = f"{'✅ ' if sched.is_default else ''}{sched.name}"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin_sched_{action}:{sched.id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_schedules"))
    return builder.as_markup()


def admin_admins_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Додати адміна", callback_data="admin_add_admin"))
    builder.row(InlineKeyboardButton(text="📋 Список адмінів", callback_data="admin_list_admins"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return builder.as_markup()


def admins_list_keyboard(admins: list, current_user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        if admin.id == current_user_id:
            continue
        name = admin.full_name or admin.username or str(admin.id)
        builder.row(InlineKeyboardButton(
            text=f"🗑 {name}",
            callback_data=f"admin_remove_admin:{admin.id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_admins"))
    return builder.as_markup()
