import os
import csv
import re
import calendar
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Этапы диалога
NAME, PHONE, SERVICE, MASTER, DATE, COMMENT = range(6)

def detect_country(phone: str) -> str:
    if phone.startswith("+380") or phone.startswith("0"):
        return "🇺🇦 Украина"
    elif phone.startswith("+375"):
        return "🇧🇾 Беларусь"
    elif phone.startswith("+7") or phone.startswith("8"):
        return "🇷🇺 Россия"
    else:
        return "🌍 Неизвестно"

def create_calendar(year, month):
    RU_MONTHS = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    RU_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    keyboard = []

    # Заголовок месяца
    keyboard.append([InlineKeyboardButton(f"{RU_MONTHS[month]} {year}", callback_data="ignore")])

    # Дни недели
    keyboard.append([InlineKeyboardButton(day, callback_data="ignore") for day in RU_DAYS])

    # Календарь
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date:{year}-{month:02d}-{day:02d}"))
        keyboard.append(row)

    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    nav_row = [
        InlineKeyboardButton("⬅️", callback_data=f"nav:{prev_year}-{prev_month}"),
        InlineKeyboardButton("➡️", callback_data=f"nav:{next_year}-{next_month}")
    ]
    keyboard.append(nav_row)

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🚀 Начать оформление заявки"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Привет! Нажми кнопку ниже, чтобы начать оформление заявки:", reply_markup=markup)
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🚀 Начать оформление заявки":
        await update.message.reply_text("Как вас зовут?")
        return NAME
    context.user_data["name"] = text
    await update.message.reply_text("📞 Укажите ваш номер телефона:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not re.match(r"^(\+380\d{9}|0\d{9}|\+375\d{9}|\+7\d{10}|8\d{10})$", phone):
        await update.message.reply_text(
            "❗ Введите корректный номер телефона:\n"
            "- 🇺🇦 +380XXXXXXXXX или 0XXXXXXXXX\n"
            "- 🇧🇾 +375XXXXXXXXX\n"
            "- 🇷🇺 +7XXXXXXXXXX или 8XXXXXXXXXX"
        )
        return PHONE
    context.user_data["phone"] = phone
    context.user_data["country"] = detect_country(phone)

    keyboard = [["Стрижка", "Маникюр"], ["Массаж", "Окрашивание"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("💅 Выберите услугу:", reply_markup=markup)
    return SERVICE

async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["service"] = update.message.text
    keyboard = [["Алина", "Мария"], ["Светлана"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("✂️ Выберите мастера:", reply_markup=markup)
    return MASTER

async def get_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["master"] = update.message.text
    now = datetime.now()
    calendar_markup = create_calendar(now.year, now.month)
    await update.message.reply_text("📅 Выберите дату:", reply_markup=calendar_markup)
    return DATE

async def handle_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("date:"):
        date_str = data.split("date:")[1]
        context.user_data["date"] = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")

        # Предложим выбрать время
        times = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
        keyboard = [[InlineKeyboardButton(t, callback_data=f"time:{t}") for t in times[i:i+3]] for i in range(0, len(times), 3)]
        await query.message.edit_text(
            f"📅 Вы выбрали дату: {context.user_data['date']}\n⏰ Теперь выберите время:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DATE

    elif data.startswith("nav:"):
        year, month = map(int, data.split("nav:")[1].split("-"))
        new_markup = create_calendar(year, month)
        await query.edit_message_reply_markup(reply_markup=new_markup)

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    time_str = query.data.split("time:")[1]
    context.user_data["time"] = time_str

    date = context.user_data["date"]
    time = context.user_data["time"]

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_datetime")],
        [InlineKeyboardButton("🔁 Изменить дату", callback_data="change_date")]
    ]
    await query.message.edit_text(
        f"📋 Вы выбрали: {date} в {time}\nПодтвердите или измените:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DATE
async def handle_datetime_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "confirm_datetime":
        context.user_data["date"] = f"{context.user_data['date']} {context.user_data['time']}"
        await query.message.delete()
        await query.message.reply_text("📝 Есть ли у вас пожелания или комментарии? (Если нет — напишите «-»)")
        return COMMENT

    elif action == "change_date":
        now = datetime.now()
        calendar_markup = create_calendar(now.year, now.month)
        await query.message.edit_text("📅 Выберите новую дату:", reply_markup=calendar_markup)
        return DATE

async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comment"] = update.message.text

    with open("requests.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            context.user_data["name"],
            context.user_data["phone"],
            context.user_data["country"],
            context.user_data["service"],
            context.user_data["master"],
            context.user_data["date"],
            context.user_data["comment"]
        ])

    await update.message.reply_text("✅ Спасибо! Вы записаны. Мы свяжемся с вами для подтверждения.", reply_markup=ReplyKeyboardRemove())

    message = (
        f"📥 Новая запись в салон:\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📞 Телефон: {context.user_data['phone']} ({context.user_data['country']})\n"
        f"💅 Услуга: {context.user_data['service']}\n"
        f"✂️ Мастер: {context.user_data['master']}\n"
        f"📅 Дата: {context.user_data['date']}\n"
        f"📝 Комментарий: {context.user_data['comment']}"
    )
    await context.bot.send_message(chat_id=OWNER_ID, text=message)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Заявка отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def show_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 У вас нет доступа к этой команде.")
        return

    try:
        with open("requests.csv", newline="", encoding="utf-8") as file:
            reader = list(csv.reader(file))
            if not reader:
                await update.message.reply_text("📭 Заявок пока нет.")
                return

            rows = reader[-5:]
            for row in rows:
                if len(row) >= 7:
                    name, phone, country, service, master, date, comment = row
                    msg = (
                        f"📝 Заявка:\n"
                        f"👤 {name}\n📞 {phone} ({country})\n"
                        f"💅 {service} | ✂️ {master}\n"
                        f"📅 {date}\n📝 {comment}"
                    )
                    await update.message.reply_text(msg)
    except FileNotFoundError:
        await update.message.reply_text("📂 Файл заявок не найден.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_master)],
            DATE: [ CallbackQueryHandler(handle_calendar, pattern="^date:"),
                    CallbackQueryHandler(handle_calendar, pattern="^nav:"),
                    CallbackQueryHandler(handle_time_selection, pattern="^time:"),
                    CallbackQueryHandler(handle_datetime_confirmation, pattern="^(confirm_datetime|change_date)$")
],

            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("requests", show_requests))

    print("🤖 Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()
