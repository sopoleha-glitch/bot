```python
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

TELEGRAM_TOKEN = "8667653728:AAF3Ekms8refE2-BvS1tgDl03sVuLpvvpx0"
DEEPSEEK_API_KEY = "sk-a45c0fa810f4430e8a154955c153070d"

logging.basicConfig(level=logging.INFO)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

start_button = KeyboardButton("🚀 СТАРТ")
main_keyboard = ReplyKeyboardMarkup([[start_button], ['💰 Баланс', '❓ Помощь']], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "друг"
    
    if user_name.lower() == "матвей":
        await update.message.reply_text(
            f"🚀 Матвей гей, рад тебя видеть! 😄\nЯ бот на DeepSeek, задавай вопросы!",
            reply_markup=main_keyboard
        )
    else:
        await update.message.reply_text(
            f"🚀 Привет, {user_name}!\nЯ бот на DeepSeek! Просто пиши мне о чем угодно.",
            reply_markup=main_keyboard
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Запуск\n/help - Помощь")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Баланс есть, всё ок!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '🚀 СТАРТ':
        await start(update, context)
        return
    
    if text == '💰 Баланс':
        await balance_command(update, context)
        return
    
    if text == '❓ Помощь':
        await help_command(update, context)
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": text}],
            max_tokens=1000
        )
        bot_response = response.choices[0].message.content
        await update.message.reply_text(bot_response)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
```
