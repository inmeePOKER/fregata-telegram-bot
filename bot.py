# bot.py
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
)

# ——— ЛОГИРОВАНИЕ —————————————————————————————————————————
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ——— GOOGLE SHEETS ——————————————————————————————————————
creds_info = json.loads(os.getenv("SERVICE_ACCOUNT_JSON") or "{}")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
gc = gspread.authorize(creds)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # ваш ID таблицы
sh = gc.open_by_key(SPREADSHEET_ID)
ws = sh.sheet1

def get_pending_posts():
    rows = ws.get_all_records()
    return [r for r in rows if r.get("Статус") == "На утверждении"]

def update_status(row_index, new_status):
    ws.update_cell(row_index + 2, 8, new_status)

# ——— TELEGRAM —————————————————————————————————————————
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /confirm для проверки постов.")

async def confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    posts = get_pending_posts()
    if not posts:
        await update.message.reply_text("Нет постов на утверждение.")
        return
    for idx, post in enumerate(posts):
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Утвердить", callback_data=f"approve|{idx}"),
            InlineKeyboardButton("❌ Отклонить",  callback_data=f"reject|{idx}")
        ]])
        await update.message.reply_text(
            f"{post['Дата']} | {post['Платформа']}\n\n{post['Текст поста']}",
            reply_markup=kb
        )

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action, idx = q.data.split("|")
    idx = int(idx)
    if action == "approve":
        update_status(idx, "Утверждено")
        await q.edit_message_text("Пост утверждён ✅")
    else:
        update_status(idx, "Отклонено")
        await q.edit_message_text("Пост отклонён ❌")

async def check_job(ctx: ContextTypes.DEFAULT_TYPE):
    posts = get_pending_posts()
    for post in posts:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Новый пост на утверждение:\n{post['Дата']} | {post['Платформа']}\n\n{post['Текст поста']}"
        )

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(on_button))
    app.job_queue.run_repeating(check_job, interval=300, first=10)
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
