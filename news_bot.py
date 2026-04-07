import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

from google import genai
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG ==================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("NEWS_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DATA_DIR = Path("/data")
DATA_DIR.mkdir(exist_ok=True)
CHANNELS_FILE = DATA_DIR / "channels.json"

# ================== GEMINI ==================

client_ai = genai.Client(
    api_key=GEMINI_API_KEY
)

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

if CHANNELS_FILE.exists():
    try:
        channels_data = json.loads(
            CHANNELS_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        channels_data = {}
else:
    channels_data = {}

user_sessions = {}

def save_channels():
    CHANNELS_FILE.write_text(
        json.dumps(
            channels_data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

# ================== MESSAGE SEPARATOR ==================

def split_message(text, max_length=4000):

    parts = []

    while len(text) > max_length:

        part = text[:max_length]

        # стараемся резать по строке
        last_newline = part.rfind("\n")

        if last_newline != -1:
            part = part[:last_newline]

        parts.append(part)

        text = text[len(part):]

    parts.append(text)

    return parts

# ================== TOPIC BUTTONS ==================

def build_topic_buttons(user_id):

    selected = user_sessions.get(
        user_id,
        {}
    ).get("topics", [])

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

# ================== GEMINI NEWS ==================

async def generate_news(topics):

    prompt = f"""
Собери актуальные новости за последние 24 часа.

Темы:
{", ".join(topics)}

Требования:

— новости должны быть свежими  
— если новости на английском — переведи  
— напиши всё на русском  
— формат удобный для Telegram  
— разделяй новости и темы от друг друга, то есть после новостей будет пустая строка, так же как и после темы
— добавляй смайлик в начало новости, который будет соответствовать этой новости
— если всё что говорится в новости может сказаться на мире, то после новости анализируй и пиши блок текста о том как это может сказаться на мире и жизни
— добавь в самом конце дайджеста такой текст "Данные новости были проанализированы и записаны ИИ Gemini, создатель не ручается за актуальность и правдивость данной информации, настоятельно рекомендую проверять информацию из надежных источников."

Формат:

📰 Утренний дайджест

📌 Тема:

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
        
    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
____________________________________________________________________________________        
📌 Тема:

    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
        
    — новость  
    
        — как это может сказаться на мире и жизни (если последствия будут ощутимыми)
____________________________________________________________________________________
и так далее
"""

    response = await asyncio.to_thread(
        client_ai.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

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
    
# ================== POST NOW COMMAND ==================

@client.on(events.NewMessage(pattern="/post_now"))
async def post_now(event):

    if not event.is_private:
        return

    user_id = event.sender_id

    # режим ожидания канала
    user_sessions[user_id] = {
        "mode": "post_now"
    }

    await event.reply(
        "📢 Отправьте username канала для публикации.\n\n"
        "Например:\n"
        "@my_channel"
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

    if not text.startswith("@"):
        return

    try:

        entity = await client.get_entity(text)

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

                parts = split_message(news)

                for part in parts:

                    await client.send_message(
                        cid,
                        part
                    )

                await event.reply(
                    "✅ Новости опубликованы!"
                )

            except Exception as e:

                await event.reply(
                    f"❌ Ошибка генерации:\n{e}"
                )

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

    except Exception:

        await event.reply(
            "❌ Не удалось получить доступ к каналу.\n"
            "Проверьте:\n"
            "— бот администратор\n"
            "— username правильный"
        )
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

        channels_data[cid] = {
            "owner": user_id,
            "topics": topics,
            "time": "09:00"
        }

        save_channels()

        await event.edit(
            "✅ Настройки сохранены.\n"
            "Новости будут публиковаться в 09:00."
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

                    news = await generate_news(
                        topics
                    )

                    parts = split_message(news)

                    for part in parts:

                        await client.send_message(
                            int(cid),
                            part
                        )

                    # сохраняем дату поста
                    channels_data[cid]["last_post"] = today_str

                    save_channels()

                    print(
                        "NEWS POSTED:",
                        cid
                    )

            except Exception as e:

                print(
                    "DAILY LOOP ERROR:",
                    e
                )

        # проверяем каждые 60 секунд
        await asyncio.sleep(60)

# ================== MAIN ==================

async def main():

    await client.start(
        bot_token=BOT_TOKEN
    )

    print("news bot started")
    print("Server time:", datetime.now())

    asyncio.create_task(
        daily_loop()
    )

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
