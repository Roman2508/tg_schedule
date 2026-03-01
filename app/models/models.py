from datetime import datetime, date, time
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Boolean, DateTime, Date, Time,
    Integer, ForeignKey, Enum, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"


class CalendarType(str, PyEnum):
    GROUP = "group"
    TEACHER = "teacher"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram_id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    saved_calendars: Mapped[List["UserSavedCalendar"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class Calendar(Base):
    __tablename__ = "calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256))
    ical_url: Mapped[str] = mapped_column(String(1024))
    type: Mapped[CalendarType] = mapped_column(Enum(CalendarType))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    saved_by: Mapped[List["UserSavedCalendar"]] = relationship(
        back_populates="calendar", cascade="all, delete-orphan"
    )

    def build_ical_url(self) -> str:
        """Return stored URL or build from calendar ID."""
        if self.ical_url.startswith("http"):
            return self.ical_url
        calendar_id = self.ical_url.replace("@", "%40")
        return f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics"


class UserSavedCalendar(Base):
    __tablename__ = "user_saved_calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    calendar_id: Mapped[int] = mapped_column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"))
    custom_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "calendar_id"),)

    user: Mapped["User"] = relationship(back_populates="saved_calendars")
    calendar: Mapped["Calendar"] = relationship(back_populates="saved_by")


class Schedule(Base):
    """Bell schedule (розклад дзвінків)."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    slots: Mapped[List["ScheduleSlot"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan", order_by="ScheduleSlot.lesson_number"
    )
    overrides: Mapped[List["ScheduleOverride"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleSlot(Base):
    """One lesson time slot."""
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"))
    lesson_number: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    schedule: Mapped["Schedule"] = relationship(back_populates="slots")


class ScheduleOverride(Base):
    """Override bell schedule for a specific date."""
    __tablename__ = "schedule_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    override_date: Mapped[date] = mapped_column(Date, unique=True)
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"))

    schedule: Mapped["Schedule"] = relationship(back_populates="overrides")
