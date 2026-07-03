import re
import logging
import os
from dotenv import load_dotenv
import psycopg2
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import paramiko

load_dotenv()
TOKEN = os.getenv("TOKEN")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")

DB_REPL_HOST = os.getenv("DB_REPL_HOST")
DB_REPL_PORT = os.getenv("DB_REPL_PORT", "22")
DB_REPL_USER = os.getenv("DB_REPL_USER")
DB_REPL_PASSWORD = os.getenv("DB_REPL_PASSWORD")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

WAIT_FOR_TEXT = 1
WAIT_FOR_CONFIRM = 2


def get_db_connection():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE
    )


def find_emails(text):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    emails = re.findall(pattern, text)
    unique = []
    for e in emails:
        if e not in unique:
            unique.append(e)
    return unique


def find_phones(text):
    pattern = r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    phones = re.findall(pattern, text)
    unique = []
    for p in phones:
        if p not in unique:
            unique.append(p)
    return unique


async def start(update, context):
    text = (
        "Привет! Это бот для работы с текстом и базой данных.\n\n"
        "/find_email - найти email и записать в БД\n"
        "/find_phone_number - найти телефоны и записать в БД\n"
        "/get_emails - email из БД\n"
        "/get_phone_numbers - телефоны из БД\n"
        "/get_repl_logs - логи репликации"
    )
    await update.message.reply_text(text)
    logger.info(f"Пользователь {update.effective_user.id} вызвал /start")


async def find_email(update, context):
    await update.message.reply_text("Отправьте текст, в котором нужно найти email-адреса:")
    return WAIT_FOR_TEXT


async def process_email(update, context):
    text = update.message.text
    emails = find_emails(text)
    if not emails:
        await update.message.reply_text("Email-адреса не найдены.")
        return ConversationHandler.END
    context.user_data['found_emails'] = emails
    await update.message.reply_text("Найденные email:\n" + "\n".join(emails))
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Записать найденные email в базу данных?", reply_markup=keyboard)
    return WAIT_FOR_CONFIRM


async def confirm_email(update, context):
    answer = update.message.text.strip().lower()
    if answer != "да":
        await update.message.reply_text("Запись отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    emails = context.user_data.get('found_emails', [])
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for email in emails:
            cur.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
        conn.commit()
        cur.close()
        conn.close()
        await update.message.reply_text(f"Успешно записано: {len(emails)} шт.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await update.message.reply_text(f"Ошибка при записи в БД: {e}", reply_markup=ReplyKeyboardRemove())
        logger.error(f"Ошибка записи email: {e}")
    return ConversationHandler.END


async def find_phone(update, context):
    await update.message.reply_text("Отправьте текст, в котором нужно найти номера телефонов:")
    return WAIT_FOR_TEXT


async def process_phone(update, context):
    text = update.message.text
    phones = find_phones(text)
    if not phones:
        await update.message.reply_text("Номера телефонов не найдены.")
        return ConversationHandler.END
    context.user_data['found_phones'] = phones
    await update.message.reply_text("Найденные номера:\n" + "\n".join(phones))
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Записать найденные номера в базу данных?", reply_markup=keyboard)
    return WAIT_FOR_CONFIRM


async def confirm_phone(update, context):
    answer = update.message.text.strip().lower()
    if answer != "да":
        await update.message.reply_text("Запись отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    phones = context.user_data.get('found_phones', [])
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for phone in phones:
            cur.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s)", (phone,))
        conn.commit()
        cur.close()
        conn.close()
        await update.message.reply_text(f"Успешно записано: {len(phones)} шт.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await update.message.reply_text(f"Ошибка при записи в БД: {e}", reply_markup=ReplyKeyboardRemove())
        logger.error(f"Ошибка записи телефонов: {e}")
    return ConversationHandler.END


async def get_emails(update, context):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email FROM emails ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            result = "Email-адреса из базы данных:\n"
            for row in rows:
                result += f"{row[0]}. {row[1]}\n"
        else:
            result = "В таблице нет записей."
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при чтении из БД: {e}")


async def get_phone_numbers(update, context):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, phone_number FROM phone_numbers ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            result = "Номера телефонов из базы данных:\n"
            for row in rows:
                result += f"{row[0]}. {row[1]}\n"
        else:
            result = "В таблице нет записей."
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при чтении из БД: {e}")


async def get_repl_logs(update, context):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=DB_REPL_HOST,
            port=int(DB_REPL_PORT),
            username=DB_REPL_USER,
            password=DB_REPL_PASSWORD
        )
        command = ("grep -E 'START_REPLICATION|IDENTIFY_SYSTEM|replication connection authorized|received replication command' "
    "/var/log/postgresql/*.log | tail -20")
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8')
        client.close()

        result = output if output.strip() else "Логи репликации не найдены."
        for i in range(0, len(result), 4000):
            await update.message.reply_text(result[i:i + 4000])
        logger.info(f"Пользователь {update.effective_user.id} вызвал /get_repl_logs")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении логов репликации: {e}")
        logger.error(f"Ошибка получения логов репликации: {e}")

async def cancel(update, context):
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()

    email_conv = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email)],
        states={
            WAIT_FOR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
            WAIT_FOR_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_email)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    phone_conv = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone)],
        states={
            WAIT_FOR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone)],
            WAIT_FOR_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_phone)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(email_conv)
    app.add_handler(phone_conv)
    app.add_handler(CommandHandler('get_emails', get_emails))
    app.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))
    app.add_handler(CommandHandler('get_repl_logs', get_repl_logs))

    logger.info("Бот запущен и готов к работе")
    app.run_polling()


if __name__ == "__main__":
    main()
