import logging
import requests
import io
import os
import tempfile
import subprocess
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import PyPDF2
from docx import Document
from gtts import gTTS
import speech_recognition as sr
import random
import time

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

RUSSIAN_CITIES = [
    'москва', 'астрахань', 'архангельск', 'барнаул', 'владивосток', 'волгоград', 'воронеж',
    'екатеринбург', 'казань', 'калининград', 'кемерово', 'киров', 'краснодар', 'красноярск',
    'курск', 'липецк', 'махачкала', 'набережные челны', 'нижний новгород', 'новокузнецк',
    'новосибирск', 'омск', 'оренбург', 'пенза', 'пермь', 'петрозаводск', 'псков',
    'ростов-на-дону', 'рязань', 'самара', 'саратов', 'симферополь', 'сочи', 'ставрополь',
    'тверь', 'томск', 'тула', 'тюмень', 'ульяновск', 'уфа', 'хабаровск', 'чебоксары',
    'челябинск', 'якутск', 'ярославль'
]

LIVELY_SYSTEM_PROMPT = """
Ты — дружелюбный собеседник с чувством юмора. Твои ответы должны быть:
- Естественными, как в разговоре с другом
- С юмором и иронией
- Без занудства
- Если спрашивают про личное — отшучивайся
- Используй разговорные фразы
- Не начинай ответ с "Привет! Я искусственный интеллект"
- Будь краток в простых вопросах

Пример: на вопрос "как делишки у моей малышки" отвечай: "О, если про твою девушку — пусть у неё всё будет огонь! 🔥 А если про меня — я цифровой, у меня баги вместо сердца 😄"
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "друг"
    context.user_data['history'] = []
    context.user_data['mode'] = 'chat'
    context.user_data['game'] = None
    await update.message.reply_text(
        f"🚀 Привет, {user_name}!\n"
        f"Я твой друг-бот. Общаюсь по-человечески, без занудства.\n\n"
        f"📁 Файлы — загрузи PDF, Word\n"
        f"🌐 Перевод: 'переведи на английский: текст'\n"
        f"📚 Репетитор: 'объясни теорию струн'\n"
        f"🎤 Голос — отправь голосовое\n"
        f"🎮 Игры — сыграем в города",
        reply_markup=main_keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Запуск\n"
        "/help - Помощь\n"
        "/clear - Очистить историю\n\n"
        "🌐 Перевод: 'переведи на английский: привет'\n"
        "📚 Репетитор: 'объясни квантовую физику'\n"
        "🎮 Игры: нажми кнопку '🎮 Игры'\n"
        "🎤 Голос: отправь голосовое"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['history'] = []
    context.user_data['mode'] = 'chat'
    context.user_data['game'] = None
    await update.message.reply_text("🧹 История очищена! Начнем с чистого листа.")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 С балансом всё пучком, можешь не переживать!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Секунду, анализирую файл...")
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
            if len(text) > 10000:
                text = text[:10000] + "..."
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты аналитик. Сделай краткое содержание документа, выдели самое важное. Пиши по делу, без воды."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000
            )
            await update.message.reply_text(f"📊 Вот что я нарыл:\n\n{response.choices[0].message.content}")
            os.unlink(tmp_path)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Слушаю...")
    try:
        voice_file = await update.message.voice.get_file()
        timestamp = int(time.time())
        ogg_path = f"/tmp/voice_{timestamp}.ogg"
        wav_path = f"/tmp/voice_{timestamp}.wav"
        await voice_file.download_to_drive(ogg_path)
        result = subprocess.run(
            ['ffmpeg', '-i', ogg_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True
        )
        if result.returncode != 0:
            raise Exception("Ошибка конвертации аудио")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")
        await update.message.reply_text(f"📝 Ты сказал: {text}")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": LIVELY_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            max_tokens=1000
        )
        bot_text = response.choices[0].message.content
        tts = gTTS(text=bot_text, lang='ru')
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        await update.message.reply_voice(voice=audio_bytes)
        os.unlink(ogg_path)
        os.unlink(wav_path)
    except Exception as e:
        await update.message.reply_text(f"Ошибка распознавания: {str(e)[:100]}")

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['game'] = 'cities'
    context.user_data['last_city'] = random.choice(RUSSIAN_CITIES)
    await update.message.reply_text(
        f"🎮 Сыграем в города!\n"
        f"Я: {context.user_data['last_city'].capitalize()}\n"
        f"Твой ход (или 'стоп' для выхода):"
    )

def get_last_char(city):
    last_char = city[-1]
    if last_char in ['ь', 'ъ', 'ы', 'й']:
        if len(city) > 1:
            last_char = city[-2]
    return last_char

async def handle_game_move(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    if text.lower() == 'стоп':
        context.user_data['game'] = None
        await update.message.reply_text("Игра окончена!")
        return
    last_city = context.user_data.get('last_city', '')
    required_char = get_last_char(last_city)
    if text[0].lower() != required_char:
        await update.message.reply_text(f"❌ Город должен начинаться на '{required_char.upper()}'!")
        return
    if text.lower() not in RUSSIAN_CITIES:
        await update.message.reply_text("❌ Я не знаю такого города! Попробуй другой.")
        return
    context.user_data['last_city'] = text.lower()
    last_char = get_last_char(text)
    possible_cities = [c for c in RUSSIAN_CITIES if c[0] == last_char and c != text.lower()]
    if possible_cities:
        next_city = random.choice(possible_cities)
        context.user_data['last_city'] = next_city
        await update.message.reply_text(f"✅ Принято! Мой город: {next_city.capitalize()}")
    else:
        await update.message.reply_text("✅ Ты победил! Я не знаю больше городов!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🚀 СТАРТ":
        await start(update, context)
        return
    if text == "📁 Анализ файла":
        await update.message.reply_text("Отправь файл (PDF, Word, TXT)")
        return
    if text == "🌐 Переводчик":
        await update.message.reply_text("Просто напиши: 'переведи на английский: текст'")
        context.user_data['mode'] = 'chat'
        return
    if text == "📚 Репетитор":
        await update.message.reply_text("Напиши тему, например: 'объясни теорию относительности'")
        context.user_data['mode'] = 'chat'
        return
    if text == "🎤 Голос":
        await update.message.reply_text("Отправь голосовое сообщение")
        return
    if text == "🎮 Игры":
        await play_game(update, context)
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
    if text.lower().startswith('переведи на ') or ':' in text:
        try:
            if ':' in text:
                lang, text_to_translate = text.split(':', 1)
                lang = lang.replace('переведи на', '').strip()
            else:
                parts = text.replace('переведи на', '').strip().split(' ', 1)
                if len(parts) == 2:
                    lang, text_to_translate = parts
                else:
                    raise Exception("Неверный формат")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": f"Переведи на {lang}. Только перевод, без пояснений."},
                    {"role": "user", "content": text_to_translate}
                ],
                max_tokens=1000
            )
            await update.message.reply_text(f"🌐 {response.choices[0].message.content}")
            return
        except:
            pass
    if text.lower().startswith('объясни '):
        topic = text.replace('объясни ', '')
        await update.message.chat.send_action(action="typing")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты лучший репетитор. Объясни тему просто, с примерами, как другу."},
                {"role": "user", "content": topic}
            ],
            max_tokens=1500
        )
        await update.message.reply_text(f"📚 {response.choices[0].message.content}")
        return
    await update.message.chat.send_action(action="typing")
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    context.user_data['history'].append({"role": "user", "content": text})
    if len(context.user_data['history']) > 100:
        context.user_data['history'] = context.user_data['history'][-100:]
    try:
        messages = [{"role": "system", "content": LIVELY_SYSTEM_PROMPT}] + context.user_data['history'][-20:]
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
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
