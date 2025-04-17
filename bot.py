from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

def start(update, context):
    update.message.reply_text("Привет! Я бот для утверждения постов.")

def approve(update, context):
    if update.message.from_user.id == int(ADMIN_ID):
        update.message.reply_text("Пост утверждён!")
    else:
        update.message.reply_text("У вас нет прав на утверждение.")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
