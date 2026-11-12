

import os
import json
import random
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==============================
# SOZLAMALAR
# ==============================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SCORES_FILE = BASE_DIR / "scores.json"

MODEL = "gemini-3.5-flash-lite"

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY topilmadi!")

client = genai.Client(
    api_key=GEMINI_KEY,
    http_options={"timeout": 60000}
)

# ==============================
# ZAXIRA IT SAVOLLARI
# ==============================

QUESTIONS = [
    ("HTML nima?", ["Dasturlash tili", "Belgilash tili", "Operatsion tizim", "Brauzer"], 1),
    ("Python qanday til?", ["Dasturlash tili", "Rasm formati", "Brauzer", "O'yin"], 0),
    ("CPU nima?", ["Xotira", "Protsessor", "Monitor", "Klaviatura"], 1),
    ("CSS nima uchun kerak?", ["Dizayn uchun", "Video uchun", "Ovoz uchun", "Internet uchun"], 0),
    ("Internet nima?", ["O'yin", "Global tarmoq", "Dastur", "Qurilma"], 1),
    ("HTML fayl kengaytmasi?", [".jpg", ".mp3", ".html", ".exe"], 2),
    ("1 KB taxminan necha bayt?", ["100", "1024", "500", "10"], 1),
    ("Brauzer nima?", ["Sayt ochuvchi dastur", "Printer", "Klaviatura", "Server"], 0),
    ("Python fayli kengaytmasi?", [".css", ".py", ".png", ".mp4"], 1),
    ("RAM nima?", ["Tezkor xotira", "Protsessor", "Monitor", "Sichqoncha"], 0),
]

RIDDLES = [
    ("Qanoti yo'q, uchadi. Oyog'i yo'q, qochadi. Bu nima?", ["Shamol", "Baliq", "Tosh", "Daraxt"], 0),
    ("O'zi bitta, ko'zi mingta. Bu nima?", ["Yulduz", "Elak", "Kitob", "Soat"], 1),
    ("Qishda ham, yozda ham bir xil kiyimda. Bu nima?", ["Olma", "Archa", "Gul", "Bug'doy"], 1),
    ("Tili yo'q, lekin gapiradi. Bu nima?", ["Kitob", "Tosh", "Stol", "Qalam"], 0),
    ("Oyoqsiz yuradi, og'izsiz gapiradi. Bu nima?", ["Daryo", "Uy", "Qush", "Mashina"], 0),
    ("Kechasi chiqadi, kunduzi yo'qoladi. Bu nima?", ["Quyosh", "Yulduz", "Daraxt", "Bulut"], 1),
    ("Qancha ko'p olsang, shuncha kattalashadi. Bu nima?", ["Chuqur", "Suv", "Kitob", "Uy"], 0),
    ("O'zi qora, yozuvi oq. Bu nima?", ["Doska", "Daftar", "Olma", "Telefon"], 0),
    ("Bir uyda mingta deraza. Bu nima?", ["Anor", "Stol", "Qalam", "Bulut"], 0),
    ("Boshsiz, ko'zsiz, lekin eshik ochadi. Bu nima?", ["Kalit", "Kitob", "Soat", "Qog'oz"], 0),
]

# ==============================
# BALLAR
# ==============================

def load_scores():
    if SCORES_FILE.exists():
        try:
            with open(SCORES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


def add_score(user, points):
    scores = load_scores()
    user_id = str(user.id)

    old_score = scores.get(user_id, {}).get("score", 0)

    scores[user_id] = {
        "name": user.full_name,
        "score": old_score + points
    }

    save_scores(scores)
    return old_score + points


# ==============================
# MENYU
# ==============================

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🧠 Bilimlar jangi", "🧩 Topishmoqlar"],
            ["⚡ Tezkor savol", "🏆 Reyting"]
        ],
        resize_keyboard=True
    )


# ==============================
# GEMINI AI
# ==============================

async def generate_questions(kind, count=10):
    if kind == "quiz":
        topic = "IT, kompyuter, internet, HTML, CSS, Python va texnologiyalar"
        instruction = "Haqiqiy IT bilimlariga oid savollar yarat."
    else:
        topic = "O'zbekcha mantiqiy topishmoqlar"
        instruction = "Qiziqarli, tushunarli va mantiqiy topishmoqlar yarat."

    prompt = f"""
Sen UZBEK GAMES viktorina botining savol yaratuvchisisan.

{instruction}

Mavzu: {topic}
Savollar soni: {count}

Har bir savolda:
- question: savol matni
- options: aynan 4 ta javob varianti
- correct: to'g'ri javobning 0 dan 3 gacha indeksi

Faqat JSON formatida javob ber.
Markdown ishlatma.
Javoblarni o'zbek tilida yoz.
Savollar aniq va bitta to'g'ri javobga ega bo'lsin.

Format:
{{
  "questions": [
    {{
      "question": "Savol matni",
      "options": ["A", "B", "C", "D"],
      "correct": 1
    }}
  ]
}}
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=prompt
    )

    raw = (response.text or "").strip()

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    result = []

    for item in data.get("questions", []):
        question = item.get("question")
        options = item.get("options")
        correct = item.get("correct")

        if (
            isinstance(question, str)
            and isinstance(options, list)
            and len(options) == 4
            and all(isinstance(x, str) for x in options)
            and isinstance(correct, int)
            and not isinstance(correct, bool)
            and 0 <= correct <= 3
        ):
            result.append((question, options, correct))

    if len(result) < count:
        raise ValueError("AI yetarli savol yaratmadi.")

    return result[:count]


async def get_game_questions(kind):
    try:
        print("Gemini yangi savollar yaratyapti...", flush=True)
        questions = await generate_questions(kind, 10)
        print("AI savollari tayyor!", flush=True)
        return questions, True

    except Exception as e:
        print("Gemini xatosi:", type(e).__name__, str(e), flush=True)
        fallback = QUESTIONS if kind == "quiz" else RIDDLES
        return random.sample(fallback, 10), False


# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 UZBEK GAMES ga xush kelibsiz!\n\n"
        "🧠 Bilimlar jangi — AI IT savollari\n"
        "🧩 Topishmoqlar — AI topishmoqlari\n"
        "⚡ Tezkor savol — bitta savol\n"
        "🏆 Reyting — TOP 10 o'yinchi",
        reply_markup=main_keyboard()
    )


# ==============================
# SAVOL CHIQARISH
# ==============================

async def show_question(chat, context):
    number = context.user_data["number"]
    game = context.user_data["game"]

    question, options, correct = game[number]

    keyboard = [
        [
            InlineKeyboardButton(
                option,
                callback_data=f"answer:{number}:{i}"
            )
        ]
        for i, option in enumerate(options)
    ]

    await chat.send_message(
        f"🎮 Savol {number + 1}/10\n\n{question}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_game(update, context, game_type):
    await update.message.reply_text(
        "⏳ AI yangi savollar tayyorlayapti..."
    )

    questions, ai_used = await get_game_questions(game_type)

    context.user_data["game"] = questions
    context.user_data["number"] = 0
    context.user_data["score"] = 0
    context.user_data["game_type"] = game_type

    title = (
        "🧠 Bilimlar jangi"
        if game_type == "quiz"
        else "🧩 Topishmoqlar"
    )

    source = "Gemini AI 🤖" if ai_used else "Zaxira savollar 📚"

    await update.message.reply_text(
        f"{title} boshlandi!\n"
        f"Savollar manbasi: {source}\n"
        "Har bir to'g'ri javob +10 ball."
    )

    await show_question(update.effective_chat, context)


# ==============================
# JAVOBLARNI TEKSHIRISH
# ==============================

async def answer_question(update, context):
    query = update.callback_query
    await query.answer()

    if "game" not in context.user_data:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Avval yangi o'yin boshlang: /start"
        )
        return

    parts = query.data.split(":")
    question_number = int(parts[1])
    selected = int(parts[2])

    number = context.user_data["number"]

    if question_number != number:
        return

    game = context.user_data["game"]
    question, options, correct = game[number]

    await query.edit_message_reply_markup(reply_markup=None)

    if selected == correct:
        context.user_data["score"] += 10
        await query.message.reply_text("✅ To'g'ri! +10 ball")
    else:
        await query.message.reply_text(
            f"❌ Noto'g'ri!\nTo'g'ri javob: {options[correct]}"
        )

    context.user_data["number"] += 1

    if context.user_data["number"] < len(game):
        await show_question(query.message.chat, context)
    else:
        score = context.user_data["score"]
        total = add_score(query.from_user, score)

        context.user_data.clear()

        await query.message.reply_text(
            f"🏁 O'YIN TUGADI!\n\n"
            f"⭐ Natija: {score}/100 ball\n"
            f"🏆 Jami ball: {total}",
            reply_markup=main_keyboard()
        )


# ==============================
# TEZKOR SAVOL
# ==============================

async def quick_question(update, context):
    await update.message.reply_text(
        "⏳ AI tezkor savol tayyorlayapti..."
    )

    questions, ai_used = await get_game_questions("quiz")
    question = questions[0]

    context.user_data["quick_question"] = question
    context.user_data["quick_answered"] = False

    text, options, correct = question

    keyboard = [
        [
            InlineKeyboardButton(
                option,
                callback_data=f"quick:{i}"
            )
        ]
        for i, option in enumerate(options)
    ]

    await update.message.reply_text(
        f"⚡ TEZKOR SAVOL!\n\n{text}\n\n"
        f"Manba: {'Gemini AI 🤖' if ai_used else 'Zaxira 📚'}\n"
        "To'g'ri javob uchun 10 ball!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def quick_answer(update, context):
    query = update.callback_query
    await query.answer()

    question = context.user_data.get("quick_question")

    if not question or context.user_data.get("quick_answered"):
        await query.edit_message_reply_markup(reply_markup=None)
        return

    context.user_data["quick_answered"] = True

    selected = int(query.data.split(":")[1])
    text, options, correct = question

    await query.edit_message_reply_markup(reply_markup=None)

    if selected == correct:
        total = add_score(query.from_user, 10)
        await query.message.reply_text(
            f"✅ To'g'ri! +10 ball!\n🏆 Jami ball: {total}"
        )
    else:
        await query.message.reply_text(
            f"❌ Noto'g'ri!\nTo'g'ri javob: {options[correct]}"
        )

    context.user_data.pop("quick_question", None)
    context.user_data.pop("quick_answered", None)


# ==============================
# REYTING
# ==============================

async def show_top(update, context):
    scores = load_scores()

    if not scores:
        await update.message.reply_text(
            "🏆 Reyting hozircha bo'sh."
        )
        return

    top = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )[:10]

    text = "🏆 TOP 10 O'YINCHI\n\n"

    for i, player in enumerate(top, 1):
        text += f"{i}. {player['name']} — {player['score']} ball\n"

    await update.message.reply_text(text)


# ==============================
# XABARLARNI QABUL QILISH
# ==============================

async def handle_message(update, context):
    text = update.message.text

    if text == "🧠 Bilimlar jangi":
        await start_game(update, context, "quiz")

    elif text == "🧩 Topishmoqlar":
        await start_game(update, context, "riddle")

    elif text == "🏆 Reyting":
        await show_top(update, context)

    elif text == "⚡ Tezkor savol":
        await quick_question(update, context)

    else:
        await update.message.reply_text(
            "Menyudan o'yinni tanlang.",
            reply_markup=main_keyboard()
        )


# ==============================
# BOTNI ISHGA TUSHIRISH
# ==============================

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            answer_question,
            pattern=r"^answer:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            quick_answer,
            pattern=r"^quick:"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_path = os.getenv("WEBHOOK_PATH")
    webhook_secret = os.getenv("WEBHOOK_SECRET")

    if not hostname or not webhook_path or not webhook_secret:
        raise ValueError("Render Webhook sozlamalari topilmadi!")

    port = int(os.getenv("PORT", "10000"))

    print("UZBEK GAMES WEBHOOK ISHGA TUSHMOQDA!", flush=True)

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=f"https://{hostname}/{webhook_path}",
        secret_token=webhook_secret,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
