import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

UA_MONTHS_NOM = [
    "", "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
]
WEEKDAY_HEADERS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

# Callback prefixes
CAL_PREFIX = "datepicker"
DAY_SELECT = f"{CAL_PREFIX}:day"
WEEK_SELECT = f"{CAL_PREFIX}:week"
MONTH_NAV = f"{CAL_PREFIX}:month"
IGNORE = f"{CAL_PREFIX}:ignore"


def build_calendar(year: int, month: int, mode: str = "day", context: str = "") -> InlineKeyboardMarkup:
    """
    Build inline calendar keyboard.
    mode: 'day' for single day selection, 'week' for week selection
    context: extra data to pass back in callback (e.g. calendar_id)
    """
    builder = InlineKeyboardBuilder()

    # Header: month/year + navigation
    prev_month = date(year, month, 1) - timedelta(days=1)
    next_month = date(year, month, 28) + timedelta(days=5)
    next_month = next_month.replace(day=1)

    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"{MONTH_NAV}:{prev_month.year}:{prev_month.month}:{mode}:{context}"),
        InlineKeyboardButton(text=f"{UA_MONTHS_NOM[month]} {year}", callback_data=IGNORE),
        InlineKeyboardButton(text="▶️", callback_data=f"{MONTH_NAV}:{next_month.year}:{next_month.month}:{mode}:{context}"),
    )

    # Weekday headers
    builder.row(*[InlineKeyboardButton(text=d, callback_data=IGNORE) for d in WEEKDAY_HEADERS])

    # Days grid
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=IGNORE))
            else:
                d = date(year, month, day)
                if mode == "day":
                    row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"{DAY_SELECT}:{d.isoformat()}:{context}"
                    ))
                else:  # week mode - highlight week on hover not possible, just pick day
                    week_start = d - timedelta(days=d.weekday())
                    row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"{WEEK_SELECT}:{week_start.isoformat()}:{context}"
                    ))
        builder.row(*row)

    # Cancel button
    builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data=f"{CAL_PREFIX}:cancel:{context}"))

    return builder.as_markup()
