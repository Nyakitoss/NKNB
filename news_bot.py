import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG ==================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("NEWS_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = Path(__file__).parent

CHANNELS_FILE = BASE_DIR / "channels.json"

# ================== GEMINI ==================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
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
    channels_data = json.loads(
        CHANNELS_FILE.read_text(encoding="utf-8")
    )
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

# ================== CHANNEL FETCH ==================

async def get_admin_channels():

    dialogs = await client.get_dialogs()

    result = []

    for d in dialogs:

        if d.is_channel:

            entity = d.entity

            if entity.creator or entity.admin_rights:

                result.append(
                    (entity.title, entity.id)
                )

    return result

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

Формат:

📰 Утренний дайджест

📌 Тема:
— новость  
— новость  

Не пиши лишнего текста.
"""

    response = await asyncio.to_thread(
        model.generate_content,
        prompt
    )

    return response.text

# ================== START COMMAND ==================

@client.on(events.NewMessage(pattern="/start"))
async def start(event):

    if not event.is_private:
        return

    channels = await get_admin_channels()

    if not channels:

        await event.reply(
            "❌ У вас нет каналов.\n"
            "Добавьте бота администратором."
        )

        return

    user_id = event.sender_id

    buttons = []

    for title, cid in channels:

        buttons.append([
            Button.inline(
                title,
                data=f"channel:{cid}"
            )
        ])

    await event.reply(
        "📢 Выберите канал:",
        buttons=buttons
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

    while True:

        now = datetime.now()

        for cid, cfg in channels_data.items():

            time_str = cfg.get("time", "09:00")

            h, m = map(int, time_str.split(":"))

            target = now.replace(
                hour=h,
                minute=m,
                second=0,
                microsecond=0
            )

            if abs((now - target).total_seconds()) < 60:

                try:

                    topics = cfg["topics"]

                    news = await generate_news(
                        topics
                    )

                    await client.send_message(
                        int(cid),
                        news
                    )

                    print(
                        "NEWS POSTED:",
                        cid
                    )

                except Exception as e:

                    print(
                        "NEWS ERROR:",
                        e
                    )

        await asyncio.sleep(60)

# ================== MAIN ==================

async def main():

    await client.start(
        bot_token=BOT_TOKEN
    )

    print("news bot started")

    asyncio.create_task(
        daily_loop()
    )

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())