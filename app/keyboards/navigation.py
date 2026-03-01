from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.formatters import format_date_short, get_week_start


def day_nav_keyboard(target_date: date, calendar_id: int) -> InlineKeyboardMarkup:
    """Navigation keyboard for day view."""
    prev_day = target_date - timedelta(days=1)
    next_day = target_date + timedelta(days=1)
    ctx = f"{calendar_id}"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"◀️ {format_date_short(prev_day)}", callback_data=f"day:{prev_day.isoformat()}:{ctx}"),
        InlineKeyboardButton(text=f"{format_date_short(next_day)} ▶️", callback_data=f"day:{next_day.isoformat()}:{ctx}"),
    )
    builder.row(
        InlineKeyboardButton(text="📆 Переглянути тиждень", callback_data=f"week:{get_week_start(target_date).isoformat()}:{ctx}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Обрати дату", callback_data=f"pick_day_date:{target_date.year}:{target_date.month}:{ctx}"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    )
    return builder.as_markup()


def week_nav_keyboard(week_start: date, calendar_id: int) -> InlineKeyboardMarkup:
    """Navigation keyboard for week view."""
    prev_week = week_start - timedelta(weeks=1)
    next_week = week_start + timedelta(weeks=1)
    ctx = f"{calendar_id}"

    prev_label = f"◀️ {format_date_short(prev_week)}–{format_date_short(prev_week + timedelta(6))}"
    next_label = f"{format_date_short(next_week)}–{format_date_short(next_week + timedelta(6))} ▶️"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=prev_label, callback_data=f"week:{prev_week.isoformat()}:{ctx}"),
        InlineKeyboardButton(text=next_label, callback_data=f"week:{next_week.isoformat()}:{ctx}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Обрати тиждень", callback_data=f"pick_week_date:{week_start.year}:{week_start.month}:{ctx}"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 Перейти до дня", callback_data=f"day:{week_start.isoformat()}:{ctx}"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    )
    return builder.as_markup()


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Мій розклад", callback_data="my_schedule"))
    builder.row(InlineKeyboardButton(text="🔍 Знайти розклад", callback_data="search_schedule"))
    if is_admin:
        builder.row(InlineKeyboardButton(text="⚙️ Адмін-панель", callback_data="admin_panel"))
    return builder.as_markup()


def calendar_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Групи", callback_data="filter_type:group"),
        InlineKeyboardButton(text="👨‍🏫 Викладачі", callback_data="filter_type:teacher"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def calendars_list_keyboard(calendars: list, page: int = 0, page_size: int = 8, suffix: str = "select") -> InlineKeyboardMarkup:
    """Paginated list of calendars."""
    builder = InlineKeyboardBuilder()
    total_pages = max(1, (len(calendars) + page_size - 1) // page_size)
    start = page * page_size
    page_items = calendars[start:start + page_size]

    for cal in page_items:
        builder.row(InlineKeyboardButton(text=cal.name, callback_data=f"cal_{suffix}:{cal.id}"))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"cal_page:{page - 1}:{suffix}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"cal_page:{page + 1}:{suffix}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="search_schedule"))
    return builder.as_markup()


def view_mode_keyboard(calendar_id: int, target_date: date) -> InlineKeyboardMarkup:
    """Choose between day and week view after selecting calendar."""
    week_start = get_week_start(target_date)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 На день", callback_data=f"day:{target_date.isoformat()}:{calendar_id}"),
        InlineKeyboardButton(text="🗓 На тиждень", callback_data=f"week:{week_start.isoformat()}:{calendar_id}"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="search_schedule"))
    return builder.as_markup()


def saved_calendars_keyboard(saved: list) -> InlineKeyboardMarkup:
    """Show user's saved calendars to pick one."""
    builder = InlineKeyboardBuilder()
    from datetime import date
    today = date.today()
    for sc in saved:
        label = sc.custom_label or sc.calendar.name
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"my_cal_view:{sc.calendar_id}:{today.isoformat()}"
        ))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def after_schedule_keyboard(calendar_id: int, target_date: date, is_saved: bool) -> InlineKeyboardMarkup:
    """Keyboard shown after viewing a schedule from search."""
    builder = InlineKeyboardBuilder()
    if not is_saved:
        builder.row(InlineKeyboardButton(text="⭐ Зберегти розклад", callback_data=f"save_cal:{calendar_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🗑 Видалити зі збережених", callback_data=f"unsave_cal:{calendar_id}"))
    builder.row(
        InlineKeyboardButton(text="📅 На день", callback_data=f"day:{target_date.isoformat()}:{calendar_id}"),
        InlineKeyboardButton(text="🗓 На тиждень", callback_data=f"week:{get_week_start(target_date).isoformat()}:{calendar_id}"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()
