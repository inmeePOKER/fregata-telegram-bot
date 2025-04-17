import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, JobQueue
from telegram.ext import MessageHandler, filters

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Авторизация в Google Sheets
creds_json = os.getenv("SERVICE_ACCOUNT_JSON")
creds = Credentials.from_service_account_info(json.loads(creds_json))
gc = gspread.authorize(creds)
spreadsheet_id = os.getenv("SPREADSHEET_ID")
sheet = gc.open_by_key(spreadsheet_id).sheet1  # Открытие первого листа

# Получение данных из таблицы
def get_pending_requests():
    rows = sheet.get_all_records()
    return [row for row in rows if row.get("Статус") == "На утверждении"]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(f"Привет, {user.first_name}!\nИспользуйте /ping для проверки бота.")

# Команда /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I'm alive 🟢")

# Команда /confirm
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending_requests = get_pending_requests()
    if not pending_requests:
        await update.message.reply_text("Нет заявок на утверждение.")
        return

    for request in pending_requests:
        post_text = request.get("Текст поста")
        post_date = request.get("Дата")
        post_platform = request.get("Платформа")
        
        # Отправляем текст поста в Telegram
        reply_markup = [
            [
                {"text": "✅ Утвердить", "callback_data": "approve"},
                {"text": "❌ Отклонить", "callback_data": "reject"}
            ]
        ]
        await update.message.reply_text(
            f"Пост на платформу {post_platform}:\n{post_text}\nДата: {post_date}",
            reply_markup=reply_markup
        )

# Обработка нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Логика обработки утверждения/отклонения
    if query.data == "approve":
        # Обновление статуса в Google Sheets
        row = sheet.find(query.message.text)
        sheet.update_cell(row.row, 6, "Утверждено")
        await query.edit_message_text(text="Пост утвержден!")
    elif query.data == "reject":
        row = sheet.find(query.message.text)
        sheet.update_cell(row.row, 6, "Отклонено")
        await query.edit_message_text(text="Пост отклонен!")

# Основная функция
async def main() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("confirm", confirm))
    
    # Регистрируем обработчик кнопок
    application.add_handler(MessageHandler(filters.CallbackQuery, button))
    
    # Планировщик задач
    job_queue = application.job_queue
    job_queue.run_repeating(check_sheet_and_send, interval=60, first=10)
    
    # Запуск бота
    await application.run_polling()

# Проверка таблицы и отправка данных в Telegram
async def check_sheet_and_send(context: CallbackContext) -> None:
    pending_requests = get_pending_requests()
    if not pending_requests:
        return

    for request in pending_requests:
        # Отправляем текст в Telegram
        text = request.get("Текст поста")
        platform = request.get("Платформа")
        user_id = os.getenv("ADMIN_ID")

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Пост на платформу {platform}:\n{text}"
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
