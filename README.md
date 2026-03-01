# 📅 Schedule Telegram Bot

Телеграм бот для перегляду розкладу занять через публічні Google Calendar (iCal).

---

## Стек

- **Python 3.12** + **aiogram 3**
- **PostgreSQL** — зберігання користувачів, календарів, графіків дзвінків
- **Redis** — FSM стани + кеш iCal відповідей
- **recurring-ical-events** — розгортання повторюваних подій з iCal
- **Docker Compose** — деплой

---

## Структура проекту

```
schedule_bot/
├── app/
│   ├── handlers/
│   │   ├── start.py          # /start та головне меню
│   │   ├── search.py         # Пошук і збереження календарів
│   │   ├── schedule_view.py  # Перегляд розкладу (день/тиждень)
│   │   └── admin.py          # Адмін-панель
│   ├── keyboards/
│   │   ├── navigation.py     # Навігаційні клавіатури
│   │   ├── calendar_widget.py # Inline date-picker
│   │   └── admin.py          # Адмін клавіатури
│   ├── middlewares/
│   │   └── user.py           # Авто-реєстрація + інʼєкція user в handlers
│   ├── models/
│   │   ├── models.py         # SQLAlchemy моделі
│   │   └── database.py       # Engine + session
│   ├── services/
│   │   ├── ical.py           # Завантаження та парсинг iCal
│   │   ├── cache.py          # Redis кеш
│   │   ├── calendars.py      # CRUD для Calendar
│   │   ├── users.py          # CRUD для User
│   │   ├── schedule.py       # Зіставлення уроків з дзвінками
│   │   └── bell_schedule.py  # CRUD для Schedule/ScheduleSlot
│   ├── utils/
│   │   └── formatters.py     # Форматування повідомлень
│   └── config.py             # Налаштування з .env
├── main.py                   # Точка входу
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Швидкий старт (локально)

```bash
# 1. Клонувати репо
git clone <your-repo-url>
cd schedule_bot

# 2. Створити .env
cp .env.example .env
# Заповнити BOT_TOKEN, SUPER_ADMIN_ID, POSTGRES_PASSWORD

# 3. Запустити
docker compose up -d

# 4. Переглянути логи
docker compose logs -f bot
```

---

## Деплой на VPS

### Вимоги
- VPS з Ubuntu 22.04+
- Docker + Docker Compose

### Встановлення Docker
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогінитись
```

### Деплой
```bash
# На сервері
git clone <your-repo-url> /opt/schedule_bot
cd /opt/schedule_bot

# Створити .env з реальними даними
cp .env.example .env
nano .env

# Запустити
docker compose up -d
```

### Оновлення бота
```bash
cd /opt/schedule_bot
git pull
docker compose up -d --build bot
```

### Деплой через Dokploy
1. Встановити Dokploy: `curl -sSL https://dokploy.com/install.sh | sh`
2. Відкрити `http://your-vps-ip:3000`
3. Створити проект → Application → підключити GitHub репо
4. В розділі Environment Variables додати всі змінні з `.env.example`
5. Dokploy сам знайде `docker-compose.yml` і запустить всі сервіси
6. Увімкнути автодеплой по push у main гілку

---

## Формат файлів для адміна

### Завантаження календарів (groups.txt / teachers.txt)
```
тип=група
ІП-31=https://calendar.google.com/calendar/ical/xxxxx%40group.calendar.google.com/public/basic.ics
ІП-32=yyyyy@group.calendar.google.com
```

```
тип=викладач
Іваненко Іван Іванович=xxxxx@group.calendar.google.com
Петренко Василь Степанович=https://calendar.google.com/...
```

### Завантаження графіку дзвінків (schedule.txt)
```
назва=Основний розклад
1=08:00-09:20
2=09:40-11:00
3=11:20-12:40
4=13:00-14:20
5=14:40-16:00
6=16:20-17:40
```

---

## Ролі

- **user** — звичайний користувач (за замовчуванням)
- **admin** — адміністратор, має доступ до адмін-панелі

Перший адміністратор визначається через `SUPER_ADMIN_ID` в `.env`.
Надалі адміни призначаються через адмін-панель бота.

---

## Як підготувати Google Calendar

1. Відкрити calendar.google.com
2. Поруч із потрібним календарем → ⋮ → Налаштування та доступ
3. Розділ "Доступ до подій" → увімкнути "Зробити загальнодоступним"
4. Розділ "Інтегрувати календар" → скопіювати **Публічна адреса у форматі iCal**
5. Вставити URL або лише ID частину у файл для завантаження
