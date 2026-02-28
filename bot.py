import logging
import requests
import io
import os
import tempfile
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import PyPDF2
from docx import Document

TELEGRAM_TOKEN = "8667653728:AAF3Ekms8refE2-BvS1tgDl03sVuLpvvpx0"
DEEPSEEK_API_KEY = "sk-a45c0fa810f4430e8a154955c153070d"

logging.basicConfig(level=logging.INFO)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

start_button = KeyboardButton("🚀 СТАРТ")
files_button = KeyboardButton("📁 Анализ договора")
lawyer_button = KeyboardButton("⚖️ Юр. консультация")
help_button = KeyboardButton("❓ Помощь")

main_keyboard = ReplyKeyboardMarkup([
    [start_button],
    [files_button, lawyer_button],
    [help_button]
], resize_keyboard=True)

LEGAL_SYSTEM_PROMPT = """
Ты — профессиональный юридический консультант с многолетним опытом. Твои ответы должны быть:
- Понятными простому человеку (без сложных терминов, а если используешь — сразу объясняешь)
- Со ссылками на статьи законов (ГК РФ, УК РФ, КоАП и т.д.)
- Практичными — что делать, куда идти, какие документы нужны
- Осторожными — всегда добавляй, что для точного решения нужна личная консультация с юристом
- Дружелюбными — ты здесь, чтобы помочь, а не запугать

Важно: Если вопрос не юридический — мягко направляй, но не отказывай в помощи.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "друг"
    context.user_data['history'] = []
    await update.message.reply_text(
        f"⚖️ Привет, {user_name}! Я твой юридический помощник.\n\n"
        f"📁 Анализ договора — загрузи файл, я проверю риски\n"
        f"⚖️ Юр. консультация — задай вопрос о законах\n"
        f"Например: 'Как составить иск?', 'Что делать при ДТП?'",
        reply_markup=main_keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚖️ **Юридический помощник**\n\n"
        "📁 **Анализ договора** — загрузи файл (PDF, Word), я:\n"
        "- Выделю риски\n"
        "- Укажу на подозрительные пункты\n"
        "- Дам рекомендации\n\n"
        "⚖️ **Юр. консультация** — напиши вопрос, например:\n"
        "- 'Как вернуть товар?'\n"
        "- 'Что делать, если уволили?'\n"
        "- 'Как составить завещание?'\n\n"
        "⚠️ Помни: я даю общую информацию, для точного решения нужен юрист."
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['history'] = []
    await update.message.reply_text("🧹 История очищена!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📁 Анализирую договор...")
    file = await update.message.effective_attachment.get_file()
    
    try:
        if update.message.document:
            file_name = update.message.document.file_name
            file_ext = file_name.split('.')[-1].lower()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
                await file.download_to_drive(tmp_file.name)
                tmp_path = tmp_file.name
            
            text = ""
            if file_ext == 'pdf':
                with open(tmp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text()
            elif file_ext == 'docx':
                doc = Document(tmp_path)
                text = '\n'.join([para.text for para in doc.paragraphs])
            else:
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            if len(text) > 15000:
                text = text[:15000] + "..."
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты юридический эксперт. Проанализируй договор и выдели: 1) Риски 2) Сомнительные пункты 3) Что стоит изменить. Пиши простым языком."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1500
            )
            
            await update.message.reply_text(f"📊 **Анализ договора:**\n\n{response.choices[0].message.content}")
            os.unlink(tmp_path)
            
    except Exception as e:
        await update.message.reply_text(f"Ошибка при анализе: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🚀 СТАРТ":
        await start(update, context)
        return
    
    if text == "📁 Анализ договора":
        await update.message.reply_text("Отправь мне файл (PDF или Word) с договором, и я проверю его на риски.")
        return
    
    if text == "⚖️ Юр. консультация":
        await update.message.reply_text(
            "⚖️ Задай свой юридический вопрос. Например:\n"
            "• 'Как вернуть деньги за товар?'\n"
            "• 'Что делать при ДТП?'\n"
            "• 'Как составить иск в суд?'"
        )
        return
    
    if text == "❓ Помощь":
        await help_command(update, context)
        return
    
    await update.message.chat.send_action(action="typing")
    
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    
    context.user_data['history'].append({"role": "user", "content": text})
    
    if len(context.user_data['history']) > 50:
        context.user_data['history'] = context.user_data['history'][-50:]
    
    try:
        messages = [{"role": "system", "content": LEGAL_SYSTEM_PROMPT}] + context.user_data['history'][-20:]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=1500
        )
        
        bot_response = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": bot_response})
        
        await update.message.reply_text(f"⚖️ {bot_response}")
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
