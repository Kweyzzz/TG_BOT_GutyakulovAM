import re
import logging
import os
from dotenv import load_dotenv
import psycopg2
import paramiko
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

load_dotenv()
TOKEN = os.getenv("TOKEN")

RM_HOST = os.getenv("RM_HOST")
RM_PORT = os.getenv("RM_PORT")
RM_USER = os.getenv("RM_USER")
RM_PASSWORD = os.getenv("RM_PASSWORD")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")

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
WAIT_FOR_PACKAGE = 3


def get_db_connection():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE
    )


def run_ssh_command(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=RM_HOST,
            port=int(RM_PORT),
            username=RM_USER,
            password=RM_PASSWORD
        )
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        client.close()
        if output:
            return output
        elif error:
            return error
        else:
            return "Команда выполнена, вывод пустой."
    except Exception as e:
        logger.error(f"Ошибка SSH: {e}")
        return f"Не удалось выполнить команду: {e}"


def split_long_message(text, limit=4000):
    parts = []
    while len(text) > limit:
        parts.append(text[:limit])
        text = text[limit:]
    parts.append(text)
    return parts


async def send_result(update, text):
    if not text.strip():
        text = "Нет данных."
    for part in split_long_message(text):
        await update.message.reply_text(part)


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
        "Привет! Это бот для мониторинга, работы с текстом и базой данных.\n\n"
        "Текст и БД:\n"
        "/find_email - найти email и записать в БД\n"
        "/find_phone_number - найти телефоны и записать в БД\n"
        "/get_emails - email из БД\n"
        "/get_phone_numbers - телефоны из БД\n"
        "/get_repl_logs - логи репликации\n\n"
        "Мониторинг системы:\n"
        "/get_release /get_uname /get_uptime /get_df /get_free\n"
        "/get_mpstat /get_w /get_auths /get_critical /get_ps\n"
        "/get_ss /get_apt_list /get_services"
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
    log_dir = "/logs"
    try:
        if not os.path.isdir(log_dir):
            await update.message.reply_text("Папка с логами не найдена.")
            return
        lines = []
        for filename in os.listdir(log_dir):
            if filename.endswith(".log"):
                with open(os.path.join(log_dir, filename), "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "replication" in line.lower():
                            lines.append(line.strip())
        result = "\n".join(lines[-20:]) if lines else "Логи репликации не найдены."
        await send_result(update, result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении логов репликации: {e}")


async def get_release(update, context):
    await send_result(update, run_ssh_command("cat /etc/*release"))


async def get_uname(update, context):
    await send_result(update, run_ssh_command("uname -a"))


async def get_uptime(update, context):
    await send_result(update, run_ssh_command("uptime"))


async def get_df(update, context):
    await send_result(update, run_ssh_command("df -h"))


async def get_free(update, context):
    await send_result(update, run_ssh_command("free -h"))


async def get_mpstat(update, context):
    await send_result(update, run_ssh_command("mpstat"))


async def get_w(update, context):
    await send_result(update, run_ssh_command("w"))


async def get_auths(update, context):
    await send_result(update, run_ssh_command("last -n 10"))


async def get_critical(update, context):
    await send_result(update, run_ssh_command("journalctl -p crit -n 5 --no-pager"))


async def get_ps(update, context):
    await send_result(update, run_ssh_command("ps aux"))


async def get_ss(update, context):
    await send_result(update, run_ssh_command("ss -tuln"))


async def get_apt_list(update, context):
    await update.message.reply_text("Введите название пакета или отправьте 'все' для полного списка:")
    return WAIT_FOR_PACKAGE


async def process_apt_list(update, context):
    answer = update.message.text.strip()
    if answer.lower() == "все":
        result = run_ssh_command("apt list --installed")
    else:
        result = run_ssh_command(f"apt list --installed | grep {answer}")
        if not result.strip():
            result = "Пакет не найден."
    await send_result(update, result)
    return ConversationHandler.END


async def get_services(update, context):
    await send_result(update, run_ssh_command("systemctl list-units --type=service --state=running --no-pager"))


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

    apt_conv = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list)],
        states={WAIT_FOR_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_apt_list)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(email_conv)
    app.add_handler(phone_conv)
    app.add_handler(apt_conv)
    app.add_handler(CommandHandler('get_emails', get_emails))
    app.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))
    app.add_handler(CommandHandler('get_repl_logs', get_repl_logs))
    app.add_handler(CommandHandler('get_release', get_release))
    app.add_handler(CommandHandler('get_uname', get_uname))
    app.add_handler(CommandHandler('get_uptime', get_uptime))
    app.add_handler(CommandHandler('get_df', get_df))
    app.add_handler(CommandHandler('get_free', get_free))
    app.add_handler(CommandHandler('get_mpstat', get_mpstat))
    app.add_handler(CommandHandler('get_w', get_w))
    app.add_handler(CommandHandler('get_auths', get_auths))
    app.add_handler(CommandHandler('get_critical', get_critical))
    app.add_handler(CommandHandler('get_ps', get_ps))
    app.add_handler(CommandHandler('get_ss', get_ss))
    app.add_handler(CommandHandler('get_services', get_services))

    logger.info("Бот запущен и готов к работе")
    app.run_polling()


if __name__ == "__main__":
    main()
