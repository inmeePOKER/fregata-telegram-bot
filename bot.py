import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)

# ——— ЛОГИРОВАНИЕ —————————————————————————————————————————
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ——— GOOGLE SHEETS ——————————————————————————————————————
# 1) Загружаем JSON сервисного аккаунта из переменной окружения
creds_info = json.loads(os.getenv("SERVICE_ACCOUNT_JSON"))
# 2) Указываем нужные scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
gc = gspread.authorize(creds)

# 3) Открываем нужную таблицу по ключу
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # добавь эту переменную в Railway!
sh = gc.open_by_key(SPREADSHEET_ID)
ws = sh.sheet1

def get_pending_posts():
    """Читаем все строки и фильтруем те, у которых Статус == На утверждении."""
    rows = ws.get_all_records()
    return [row for row in rows if row.get("Статус") == "На утверждении"]

def update_status(row_index, new_status):
    """Обновляем столбец 'Статус' (номер 8, т.к. A=1,…) на новую метку."""
    ws.update_cell(row_index + 2, 8, new_status)  # +2: пропускаем заголовок и идём по индексу

# ——— TELEGRAM —————————————————————————————————————————
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /ping для проверки.")

async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот жив 🟢")

async def confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    posts = get_pending_posts()
    if not posts:
        await update.message.reply_text("Нет постов на утверждение.")
        return
    for idx, post in enumerate(posts):
        text = post["Текст поста"]
        platform = post["Платформа"]
        date = post["Дата"]
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Утвердить", callback_data=f"approve|{idx}"),
            InlineKeyboardButton("❌ Отклонить",  callback_data=f"reject|{idx}")
        ]])
        await update.message.reply_text(
            f"Пост для {platform}\n{date}\n\n{text}",
            reply_markup=kb
        )

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, idx_str = query.data.split("|")
    idx = int(idx_str)
    pending = get_pending_posts()
    # вычисляем реальный номер строки в таблице
    # находим уникальную ячейку по Номеру строки
    # но проще: индекс в списке +2
    row_num = idx + 2
    if action == "approve":
        update_status(idx, "Утверждено")
        await query.edit_message_text("Пост утверждён ✅")
    else:
        update_status(idx, "Отклонено")
        await query.edit_message_text("Пост отклонён ❌")

async def check_job(ctx: ContextTypes.DEFAULT_TYPE):
    # шлём админу, если что-то добавилось
    posts = get_pending_posts()
    for idx, post in enumerate(posts):
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Новый пост на утверждение:\n{post['Платформа']} | {post['Дата']}\n\n{post['Текст поста']}"
        )

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(on_button))
    # каждый 5 минут проверяем
    app.job_queue.run_repeating(check_job, interval=300, first=10)
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
