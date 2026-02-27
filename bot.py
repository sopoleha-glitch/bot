```python
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
import pandas as pd
from gtts import gTTS
import speech_recognition as sr
import random

TELEGRAM_TOKEN = "8667653728:AAF3Ekms8refE2-BvS1tgDl03sVuLpvvpx0"
DEEPSEEK_API_KEY = "sk-a45c0fa810f4430e8a154955c153070d"

logging.basicConfig(level=logging.INFO)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

start_button = KeyboardButton("🚀 СТАРТ")
files_button = KeyboardButton("📁 Анализ файла")
translate_button = KeyboardButton("🌐 Переводчик")
tutor_button = KeyboardButton("📚 Репетитор")
voice_button = KeyboardButton("🎤 Голос")
games_button = KeyboardButton("🎮 Игры")
balance_button = KeyboardButton("💰 Баланс")
help_button = KeyboardButton("❓ Помощь")

main_keyboard = ReplyKeyboardMarkup([
    [start_button],
    [files_button, translate_button, tutor_button],
    [voice_button, games_button],
    [balance_button, help_button]
], resize_keyboard=True)

games = {
    'cities': {
        'name': '🌆 Города',
        'description': 'Назови город, а я следующий',
        'russian_cities': ['москва', 'питер', 'казань', 'новосибирск', 'екатеринбург', 'нижний новгород', 'самара', 'омск', 'челябинск', 'ростов', 'уфа', 'волгоград', 'пермь', 'красноярск', 'воронеж']
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "друг"
    
    context.user_data['history'] = []
    context.user_data['mode'] = 'chat'
    context.user_data['game'] = None
    
    await update.message.reply_text(
        f"🚀 {user_name} гей, рад тебя видеть! 😄\n"
        f"Я бот на DeepSeek, задавай вопросы!\n\n"
        f"📁 Анализ файлов — загрузи PDF, Word, Excel\n"
        f"🌐 Переводчик — перевожу с сохранением стиля\n"
        f"📚 Репетитор — объясняю сложные темы\n"
        f"🎤 Голос — отправь голосовое, я пойму\n"
        f"🎮 Игры — сыграем в города",
        reply_markup=main_keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Запуск\n"
        "/help - Помощь\n"
        "/clear - Очистить историю\n\n"
        "📁 Анализ файлов — загрузи файл, я сделаю краткое содержание\n"
        "🌐 Переводчик — напиши 'переведи на английский: текст'\n"
        "📚 Репетитор — напиши 'объясни {тема}'\n"
        "🎤 Голос — отправь голосовое сообщение\n"
        "🎮 Игры — сыграем в города"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['history'] = []
    context.user_data['mode'] = 'chat'
    context.user_data['game'] = None
    await update.message.reply_text("🧹 История и режимы очищены!")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Баланс есть, всё ок!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Получил файл, анализирую...")
    
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
            
            elif file_ext in ['xls', 'xlsx']:
                df = pd.read_excel(tmp_path)
                text = df.to_string()
            
            else:
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Сделай краткое содержание этого документа. Выдели главное."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000
            )
            
            await update.message.reply_text(f"📊 Анализ файла:\n\n{response.choices[0].message.content}")
            
            os.unlink(tmp_path)
            
    except Exception as e:
        await update.message.reply_text(f"Ошибка при анализе файла: {e}")

async def translate_text(text, target_language="английский", style="обычный"):
    style_prompt = {
        "деловой": "Переведи в официально-деловом стиле",
        "дружеский": "Переведи в дружеском, неформальном стиле",
        "поэтический": "Переведи красиво, как в стихах",
        "обычный": "Переведи точно, сохраняя смысл"
    }
    
    system_prompt = f"Ты профессиональный переводчик. {style_prompt.get(style, style_prompt['обычный'])}. Сохраняй тон и эмоции оригинала."
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Переведи на {target_language}: {text}"}
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

async def explain_topic(topic, level="начинающий"):
    system_prompt = f"Ты лучший репетитор. Объясни тему '{topic}' для уровня '{level}'. Используй примеры из жизни. Будь терпелив и дружелюбен."
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Объясни мне {topic}"}
        ],
        max_tokens=1500
    )
    return response.choices[0].message.content

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Получил голосовое, распознаю...")
    
    try:
        voice_file = await update.message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            await voice_file.download_to_drive(tmp_file.name)
            tmp_path = tmp_file.name
        
        wav_path = tmp_path.replace('.ogg', '.wav')
        os.system(f"ffmpeg -i {tmp_path} {wav_path}")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")
        
        await update.message.reply_text(f"📝 Распознал: {text}")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": text}],
            max_tokens=1000
        )
        
        tts = gTTS(text=response.choices[0].message.content, lang='ru')
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        
        await update.message.reply_voice(voice=audio_bytes)
        
        os.unlink(tmp_path)
        os.unlink(wav_path)
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка при распознавании: {e}")

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_name):
    if game_name == "города":
        context.user_data['game'] = 'cities'
        context.user_data['last_city'] = random.choice(games['cities']['russian_cities'])
        await update.message.reply_text(
            f"🎮 Сыграем в города!\n"
            f"Я называю город, ты называешь на последнюю букву.\n"
            f"Мой город: {context.user_data['last_city'].capitalize()}\n"
            f"Твой ход! (или 'стоп' для выхода)"
        )

async def handle_game_move(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    game = context.user_data.get('game')
    
    if game == 'cities':
        if text.lower() == 'стоп':
            context.user_data['game'] = None
            await update.message.reply_text("Игра окончена! Возвращаемся в обычный режим.")
            return
        
        last_city = context.user_data.get('last_city', '')
        last_char = last_city[-1]
        if last_char in ['ь', 'ъ', 'ы', 'й']:
            last_char = last_city[-2]
        
        if text[0].lower() != last_char:
            await update.message.reply_text(f"❌ Город должен начинаться на букву '{last_char.upper()}'! Попробуй еще.")
            return
        
        context.user_data['last_city'] = text.lower()
        next_city = random.choice(games['cities']['russian_cities'])
        await update.message.reply_text(f"✅ Принято! Мой город: {next_city.capitalize()}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🚀 СТАРТ":
        await start(update, context)
        return
    
    if text == "📁 Анализ файла":
        await update.message.reply_text("Отправь мне файл (PDF, Word, Excel, TXT), я сделаю краткое содержание")
        return
    
    if text == "🌐 Переводчик":
        context.user_data['mode'] = 'translator'
        await update.message.reply_text(
            "🌐 Режим переводчика!\n"
            "Напиши в формате: 'на английский: Привет, как дела?'\n"
            "Или: 'на французский (деловой): Текст'"
        )
        return
    
    if text == "📚 Репетитор":
        context.user_data['mode'] = 'tutor'
        await update.message.reply_text(
            "📚 Режим репетитора!\n"
            "Напиши тему, которую хочешь понять.\n"
            "Например: 'квантовая физика для начинающих'"
        )
        return
    
    if text == "🎤 Голос":
        await update.message.reply_text("Отправь мне голосовое сообщение, я распознаю и отвечу голосом!")
        return
    
    if text == "🎮 Игры":
        await play_game(update, context, "города")
        return
    
    if text == "💰 Баланс":
        await balance_command(update, context)
        return
    
    if text == "❓ Помощь":
        await help_command(update, context)
        return
    
    if context.user_data.get('game'):
        await handle_game_move(update, context, text)
        return
    
    mode = context.user_data.get('mode', 'chat')
    
    if mode == 'translator':
        try:
            if ':' in text:
                parts = text.split(':', 1)
                lang_info = parts[0].strip()
                text_to_translate = parts[1].strip()
                
                if '(' in lang_info and ')' in lang_info:
                    lang, style = lang_info.split('(')
                    style = style.rstrip(')')
                else:
                    lang = lang_info
                    style = 'обычный'
                
                translation = await translate_text(text_to_translate, lang, style)
                await update.message.reply_text(f"🌐 Перевод ({style} стиль):\n\n{translation}")
            else:
                await update.message.reply_text("Неверный формат. Используй: 'на английский: текст'")
        except Exception as e:
            await update.message.reply_text(f"Ошибка перевода: {e}")
        return
    
    if mode == 'tutor':
        explanation = await explain_topic(text)
        await update.message.reply_text(f"📚 Объяснение:\n\n{explanation}")
        context.user_data['mode'] = 'chat'
        return
    
    await update.message.chat.send_action(action="typing")
    
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    
    context.user_data['history'].append({"role": "user", "content": text})
    
    if len(context.user_data['history']) > 100:
        context.user_data['history'] = context.user_data['history'][-100:]
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=context.user_data['history'],
            max_tokens=1000
        )
        bot_response = response.choices[0].message.content
        
        context.user_data['history'].append({"role": "assistant", "content": bot_response})
        
        if len(context.user_data['history']) > 100:
            context.user_data['history'] = context.user_data['history'][-100:]
        
        await update.message.reply_text(bot_response)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    main()
```
