import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

from google import genai
from dotenv import load_dotenv

from storage import storage
from validators import InputValidator, ErrorHandler, ValidationError
from gemini_client import create_gemini_client
from cache_manager import cache_manager
from openrouter_client import create_ai_client
from news_parser import news_parser
from news_analyzer import news_analyzer

load_dotenv()

# ================== CONFIG ==================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("NEWS_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# AI Provider selection: "gemini", "groq", "grok", "openrouter"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")  # Default to OpenRouter

# Daily request limits for different providers
DAILY_LIMITS = {
    "gemini": 15,
    "groq": 43200,
    "grok": 100,
    "openrouter": 1000  # Estimated limit for free tier
}

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(exist_ok=True)
CHANNELS_FILE = DATA_DIR / "channels.json"

# ================== AI CLIENT SETUP ==================

# Initialize AI client based on provider
try:
    if AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY is required for Gemini provider")
        client_ai = create_gemini_client(GEMINI_API_KEY)
        ai_api_key = GEMINI_API_KEY
        models_count = 3  # Gemini models
    elif AI_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise Exception("GROQ_API_KEY is required for Groq provider")
        client_ai = create_ai_client("groq", GROQ_API_KEY)
        ai_api_key = GROQ_API_KEY
        models_count = 3  # Groq models
    elif AI_PROVIDER == "grok":
        if not GROK_API_KEY:
            raise Exception("GROK_API_KEY is required for Grok provider")
        client_ai = create_ai_client("grok", GROK_API_KEY)
        ai_api_key = GROK_API_KEY
        models_count = 6  # Grok models
    elif AI_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise Exception("OPENROUTER_API_KEY is required for OpenRouter provider")
        client_ai = create_ai_client("openrouter", OPENROUTER_API_KEY)
        ai_api_key = OPENROUTER_API_KEY
        models_count = 23  # OpenRouter free models
    else:
        raise Exception(f"Unsupported AI provider: {AI_PROVIDER}")

    print(f"**LOG: Using AI provider: {AI_PROVIDER}**")
    print(f"**LOG: Daily limit: {DAILY_LIMITS[AI_PROVIDER]} requests**")
    print(f"**LOG: API key configured: {'YES' if ai_api_key else 'NO'}**")
    print(f"**LOG: Models available: {models_count}**")
    print(f"**LOG: News sources: {len(news_parser.news_sources)} RSS feeds**")
    print("**LOG: Bot started successfully**")
    
except Exception as e:
    print(f"**LOG: Failed to initialize AI client: {e}**")
    raise

# ================== CLIENT ==================

client = TelegramClient(
    StringSession(),
    API_ID,
    API_HASH
)

# ================== TOPICS ==================

TOPICS = [
    "Искусственный интеллект",
    "Технологии",
    "Игры",
    "Наука",
    "Экономика",
    "Криптовалюты",
    "Космос",
    "Медицина",
    "Автомобили",
    "Кибербезопасность",
    "Политика",
    "Общество"
]

# ================== STORAGE ==================

# Используем новое хранилище с поддержкой Redis
channels_data = storage.get_channels_data()
user_sessions = {}

def save_channels():
    return storage.save_channels_data(channels_data)

# ================== MESSAGE SEPARATOR ==================

def split_message(text, max_length=4000):

    parts = []

    while len(text) > max_length:

        part = text[:max_length]

        # стараемся резать по строке
        last_newline = part.rfind("\n")

        if last_newline != -1 and last_newline > max_length * 0.8:  # не резать слишком рано
            part = part[:last_newline]

        # Удаляем пустые строки в начале и конце
        part = part.strip()
        
        if part:  # добавляем только непустые части
            parts.append(part)

        text = text[len(part):]

    # Добавляем последнюю часть, если она не пустая
    remaining_text = text.strip()
    if remaining_text:
        parts.append(remaining_text)

    return parts

# ================== TEXT SANITIZE ==================

def sanitize_text(text):

    if not text:
        return ""

    # удаляем нулевые символы и другие невидимые символы
    text = text.replace("\x00", "")
    text = text.replace("\u200B", "")  # zero-width space
    text = text.replace("\u200C", "")  # zero-width non-joiner
    text = text.replace("\u200D", "")  # zero-width joiner

    # заменяем странные unicode-разделители
    text = text.replace("\u2028", "\n")
    text = text.replace("\u2029", "\n")

    # убираем множественные пустые строки
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    # убираем лишние пробелы в начале и конце
    text = text.strip()

    return text

# ================== TOPIC BUTTONS ==================

def build_topic_buttons(user_id):

    session = user_sessions.get(user_id, {})
    selected = session.get("topics", [])
    
    # If this is a channel configuration, load saved topics
    if "channel" in session and not selected:
        channel_id = str(session["channel"])
        if channel_id in channels_data:
            selected = channels_data[channel_id].get("topics", [])
            session["topics"] = selected  # Update session with loaded topics

    buttons = []

    for topic in TOPICS:

        mark = "✅" if topic in selected else "⬜"

        buttons.append([
            Button.inline(
                f"{mark} {topic}",
                data=f"toggle:{topic}"
            )
        ])

    buttons.append([
        Button.inline(
            "💾 Сохранить",
            data="save_topics"
        )
    ])

    return buttons

# ================== NEWS GENERATION ==================

async def generate_news(topics):
    """Генерация новостей через парсинг и анализ"""
    try:
        print(f"**LOG: Starting news generation for topics: {', '.join(topics)}**")
        
        # Проверяем кэш новостей
        cached_news = news_parser.get_cached_news()
        if cached_news:
            print("**LOG: Using cached news**")
            # Фильтруем по темам
            filtered_news = news_parser.filter_news_by_topics(cached_news, topics)
            if filtered_news:
                print(f"**LOG: Found {len(filtered_news)} relevant cached news items**")
                return await news_analyzer.analyze_news(filtered_news, topics)
        
        # Парсим свежие новости
        print("**LOG: Parsing fresh news from sources**")
        all_news = await news_parser.parse_all_sources()
        
        # Кэшируем результаты
        news_parser.cache_news(all_news)
        
        # Фильтруем по темам
        filtered_news = news_parser.filter_news_by_topics(all_news, topics)
        
        if not filtered_news:
            print("**LOG: No relevant news found**")
            return "📰 **Ежедневный дайджест**\n\nК сожалению, не найдено новостей по указанным темам за последние 24 часа.\n\nПопробуйте изменить темы или повторите попытку позже."
        
        print(f"**LOG: Analyzing {len(filtered_news)} relevant news items**")
        return await news_analyzer.analyze_news(filtered_news, topics)
        
    except Exception as e:
        print(f"**LOG: News generation error: {str(e)}**")
        return f"📰 **Ошибка генерации новостей**\n\nПроизошла ошибка при обработке новостей: {str(e)}\n\nПопробуйте повторить попытку позже."

# ================== START COMMAND ==================

@client.on(events.NewMessage(pattern="/start"))
async def start(event):

    if not event.is_private:
        return

    await event.reply(
        "📢 Отправьте username канала.\n\n"
        "Например:\n"
        "@my_channel\n\n"
        "⚠️ Канал должен быть публичным.\n\n"
        "⚠️ Бот должен быть администратором канала."
    )
    
# ================== EDIT TIME COMMAND ==================

@client.on(events.NewMessage(pattern="/edit_time"))
async def edit_time(event):
    if not event.is_private:
        return
    
    user_id = event.sender_id
    await event.reply(
        "**Edit Posting Time**\n\n"
        "Send channel username to edit posting time:\n"
        "Example: @my_channel\n\n"
        "Current channels will be listed with their current times."
    )
    
    user_sessions[user_id] = {
        "mode": "edit_time"
    }

# ================== POST NOW COMMAND ==================

@client.on(events.NewMessage(pattern="/post_now"))
async def post_now(event):

    if not event.is_private:
        return

    user_id = event.sender_id

    # Check API limits first
    limits = cache_manager.check_api_limits(AI_PROVIDER)
    if not limits["can_request"]:
        time_until_reset = cache_manager.get_time_until_reset()
        await event.reply(
            f"**API Limit Reached**\n\n"
            f"Provider: {AI_PROVIDER}\n"
            f"Used: {limits['requests_today']}/{limits['daily_limit']} requests\n"
            f"Reset in: {time_until_reset}\n\n"
            f"Try:\n"
            f"1. Wait for reset\n"
            f"2. Use /limits to check status\n"
            f"3. Request will use cached news if available"
        )
        return

    # Wait for channel input mode
    user_sessions[user_id] = {
        "mode": "post_now"
    }

    await event.reply(
        f"**API Status**: Available\n\n"
        f"Provider: {AI_PROVIDER}\n"
        f"Requests today: {limits['requests_today']}/{limits['daily_limit']}\n\n"
        "Send channel username for publication:\n\n"
        "`@my_channel`"
    )
    
# ================== LIMITS COMMAND ==================

@client.on(events.NewMessage(pattern="/limits"))
async def limits(event):

    if not event.is_private:
        return

    limits = cache_manager.check_api_limits(AI_PROVIDER)
    time_until_reset = cache_manager.get_time_until_reset()

    await event.reply(
        f"**API Limits - {AI_PROVIDER.title()}**\n\n"
        f"Provider: {AI_PROVIDER}\n"
        f"Used: {limits['requests_today']}/{limits['daily_limit']} requests\n"
        f"Remaining: {limits['remaining']}\n"
        f"Reset in: {time_until_reset}\n\n"
        f"Daily limit: {DAILY_LIMITS[AI_PROVIDER]} requests"
    )

# ================== CHANNEL INPUT ==================

@client.on(events.NewMessage)
async def handle_channel_input(event):

    if not event.is_private:
        return

    user_id = event.sender_id
    text = event.raw_text.strip()

    if text.startswith("/"):
        return

    # Handle time setting for edit_time_set mode
    session = user_sessions.get(user_id)
    if session and session.get("mode") == "edit_time_set":
        # Validate time format HH:MM
        import re
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
        
        if not time_pattern.match(text):
            await event.reply(
                "Invalid time format!\n\n"
                "Please use HH:MM format (24-hour)\n"
                "Examples: 08:00, 14:30, 18:00\n\n"
                "Available times: 00:00 - 23:59"
            )
            return
        
        cid = session["channel"]
        channels_data[str(cid)]["time"] = text
        save_channels()
        
        await event.reply(
            f"**Posting time updated successfully!**\n\n"
            f"New time: {text}\n"
            f"Channel: {await client.get_entity(int(cid))}\n\n"
            f"News will now be posted at {text} daily."
        )
        
        del user_sessions[user_id]
        return

    if not text.startswith("@"):
        return

    try:
        # Валидация username канала
        validated_username = InputValidator.validate_channel_username(text)
        
        entity = await client.get_entity(validated_username)

        # 🔐 Проверяем права администратора
        perms = await client.get_permissions(
            entity,
            user_id
        )

        if not perms.is_admin:
            await event.reply(
                "❌ У вас нет прав администратора в этом канале."
            )
            return

        cid = entity.id

        session = user_sessions.get(user_id)

        # ===== EDIT_TIME MODE =====
        
        if session and session.get("mode") == "edit_time":
            # Show current time and ask for new time
            current_config = channels_data.get(str(cid))
            current_time = current_config.get("time", "09:00") if current_config else "09:00"
            
            user_sessions[user_id] = {
                "mode": "edit_time_set",
                "channel": cid
            }
            
            await event.reply(
                f"**Current posting time for {text}:** {current_time}\n\n"
                "Send new time in format HH:MM (24-hour)\n"
                "Examples: 08:00, 14:30, 18:00\n\n"
                "Available times: 00:00 - 23:59"
            )
            return

        # ===== POST_NOW MODE =====

        if session and session.get("mode") == "post_now":

            await event.reply(
                "⏳ Генерирую новости..."
            )

            try:

                # если канал настроен — берём его темы
                if str(cid) in channels_data:

                    topics = channels_data[str(cid)]["topics"]

                else:

                    topics = [
                        "Искусственный интеллект",
                        "Технологии",
                        "Игры",
                        "Наука",
                        "Экономика",
                        "Криптовалюты",
                        "Космос",
                        "Медицина",
                        "Автомобили",
                        "Кибербезопасность",
                        "Политика",
                        "Общество"
                    ]

                news = await generate_news(topics)

                # очистка текста
                news = sanitize_text(news)

                parts = split_message(news)

                for i, part in enumerate(parts):
                    
                    part = sanitize_text(part)

                    # Дополнительная проверка на пустые и невалидные сообщения
                    if not part or len(part.strip()) == 0:
                        print(f"Skipping empty part #{i}")
                        continue
                    
                    if len(part) > 4096:  # Telegram limit
                        print(f"Part #{i} too long ({len(part)} chars), splitting further")
                        sub_parts = split_message(part, 3500)  # Recursive split
                        for sub_part in sub_parts:
                            if sub_part.strip():
                                await client.send_message(
                                    int(cid),
                                    sub_part
                                )
                                print(f"Sending sub-part length: {len(sub_part)}")
                    else:
                        await client.send_message(
                            int(cid),
                            part
                        )
                        print(f"Sending part #{i} length: {len(part)}")

                await event.reply(
                    "✅ Новости опубликованы!"
                )

            except Exception as e:
                error_msg = ErrorHandler.handle_gemini_error(e)
                await event.reply(error_msg)

            return

        # ===== CONFIG MODE =====

        user_sessions[user_id] = {
            "channel": cid,
            "topics": []
        }

        await event.reply(
            "🧠 Выберите категории:",
            buttons=build_topic_buttons(user_id)
        )

    except ValidationError as ve:
        await event.reply(str(ve))
    
    except Exception as e:
        error_msg = ErrorHandler.handle_telegram_error(e)
        await event.reply(error_msg)
# ================== CALLBACK ==================

@client.on(events.CallbackQuery)
async def callbacks(event):

    user_id = event.sender_id
    data = event.data.decode()

    # ===== выбрать канал =====

    if data.startswith("channel:"):

        cid = data.split(":")[1]

        user_sessions[user_id] = {
            "channel": cid,
            "topics": []
        }

        await event.edit(
            "🧠 Выберите категории:",
            buttons=build_topic_buttons(user_id)
        )

        return

    # ===== переключить тему =====

    if data.startswith("toggle:"):

        topic = data.split(":")[1]

        session = user_sessions.get(user_id)

        if not session:
            return

        topics = session["topics"]

        if topic in topics:
            topics.remove(topic)
        else:
            topics.append(topic)

        await event.edit(
            "🧠 Выберите категории:",
            buttons=build_topic_buttons(user_id)
        )

        return

    # ===== сохранить =====

    if data == "save_topics":

        session = user_sessions.get(user_id)

        if not session:
            return

        cid = session["channel"]
        topics = session["topics"]
        
        # Get current time or use default
        current_config = channels_data.get(str(cid))
        current_time = current_config.get("time", "09:00") if current_config else "09:00"

        channels_data[cid] = {
            "owner": user_id,
            "topics": topics,
            "time": current_time
        }

        save_channels()

        await event.edit(
            "**Settings saved successfully!**\n\n"
            f"Topics: {len(topics)} selected\n"
            f"Posting time: {current_time}\n\n"
            "Use `/edit_time` to change posting time."
        )

# ================== DAILY LOOP ==================

async def daily_loop():

    print("Daily loop started")

    while True:

        now = datetime.now()

        for cid, cfg in channels_data.items():

            try:

                time_str = cfg.get("time", "09:00")

                h, m = map(int, time_str.split(":"))

                target = now.replace(
                    hour=h,
                    minute=m,
                    second=0,
                    microsecond=0
                )

                # дата последнего поста
                last_post_date = cfg.get("last_post")

                today_str = now.strftime("%Y-%m-%d")

                # если уже постили сегодня — пропускаем
                if last_post_date == today_str:
                    continue

                # разница во времени
                diff = (now - target).total_seconds()

                # если время прошло,
                # но не больше 1 часа (3600 сек)
                if 0 <= diff <= 3600:

                    print(
                        f"Posting news for {cid}"
                    )

                    topics = cfg["topics"]

                    news = await generate_news(topics)

                    news = sanitize_text(news)

                    parts = split_message(news)

                    for i, part in enumerate(parts):

                        part = sanitize_text(part)

                        # Дополнительная проверка на пустые и невалидные сообщения
                        if not part or len(part.strip()) == 0:
                            print(f"Skipping empty part #{i} in daily loop")
                            continue
                        
                        if len(part) > 4096:  # Telegram limit
                            print(f"Part #{i} too long ({len(part)} chars), splitting further")
                            sub_parts = split_message(part, 3500)  # Recursive split
                            for sub_part in sub_parts:
                                if sub_part.strip():
                                    await client.send_message(
                                        cid,
                                        sub_part
                                    )
                                    print(f"Sending sub-part length: {len(sub_part)}")
                        else:
                            await client.send_message(
                                cid,
                                part
                            )
                            print(f"Sending part #{i} length: {len(part)}")
                    # сохраняем дату поста
                    channels_data[cid]["last_post"] = today_str

                    save_channels()

                    print(
                        "NEWS POSTED:",
                        cid
                    )

            except Exception as e:
                error_type = type(e).__name__
                print(f"DAILY LOOP ERROR ({error_type}): {e}")
                
                # Дополнительная информация для отладки
                if "gemini" in str(e).lower():
                    print("Gemini API error - check API key and quotas")
                elif "telegram" in str(e).lower():
                    print("Telegram API error - check bot permissions")
                elif "redis" in str(e).lower():
                    print("Redis error - check connection")

        # проверяем каждые 60 секунд
        await asyncio.sleep(60)

# ================== MAIN ==================

async def main():

    await client.start(
        bot_token=BOT_TOKEN
    )

    print("=" * 50)
    print("=== NEWS BOT STARTED ===")
    print(f"Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Timezone: {datetime.now().astimezone().tzinfo}")
    print(f"AI Provider: {AI_PROVIDER}")
    print(f"Redis Storage: {'Enabled' if storage.use_redis else 'Disabled (Local)'}")
    print("=" * 50)

    asyncio.create_task(
        daily_loop()
    )

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
