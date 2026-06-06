
code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 بوت تيليجرام المتكامل - KIMO BOT
"""

import os
import logging
import sqlite3
import random
import string
import asyncio
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, Any

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    InputMediaPhoto, Bot
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

# ========== ⚙️ CONFIGURATION ==========
BOT_TOKEN = "8690926155:AAEjx73W1qAJHYcBs2q5VRr09v5gTdgDjHw"
GROQ_API_KEY = "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"
ADMIN_ID = 6471539208
AI_MODEL = "openai/gpt-oss-120b"
AI_NAME = "كيمو"

# ========== 📜 RULES ==========
RULES = """
📜 قوانين المجموعة:

1️⃣ احترام جميع الأعضاء وعدم التعرض لأي شخص بالإساءة.
2️⃣ عدم نشر أي محتوى غير أخلاقي أو إباحي.
3️⃣ عدم إرسال رسائل مزعجة (سبام) بكثرة.
4️⃣ عدم نشر روابط مشبوهة أو خبيثة.
5️⃣ الالتزام بموضوع المجموعة.
6️⃣ عدم استخدام أسماء مستعارة مسيئة.
7️⃣ احترام قرارات الإدارة.
8️⃣ عدم التدخل في الخلافات الشخصية.
9️⃣ عدم نشر معلومات شخصية لأي عضو.
🔟 الاستمتاع بالألعاب والفعاليات بروح رياضية.

⚠️ المخالفة تؤدي إلى الميوت أو الطرد!
"""

# ========== 🗄️ DATABASE ==========
class Database:
    def __init__(self, db_name="bot_database.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TEXT,
                balance INTEGER DEFAULT 0,
                bank_card TEXT,
                warnings INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name, last_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def update_balance(self, user_id, amount):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
    
    def create_bank_card(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        while True:
            card_number = "".join(random.choices(string.digits, k=16))
            cursor.execute("SELECT user_id FROM users WHERE bank_card = ?", (card_number,))
            if not cursor.fetchone():
                break
        cursor.execute("UPDATE users SET bank_card = ? WHERE user_id = ?", (card_number, user_id))
        conn.commit()
        conn.close()
        return card_number

db = Database()

# ========== 🤖 AI HANDLER ==========
class AIHandler:
    def __init__(self):
        self.client = None
        try:
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            logging.warning("مكتبة Groq غير مثبتة")
        except Exception as e:
            logging.warning(f"خطأ في Groq: {e}")
    
    async def chat(self, message: str) -> str:
        if not self.client:
            return "⚠️ لم يتم إعداد API الذكاء الاصطناعي بعد."
        try:
            response = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": f"أنت مساعد ذكي باللغة العربية اسمك {AI_NAME}. كن مفيداً وودوداً واختصر إجاباتك."},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ حدث خطأ في الاتصال بـ {AI_NAME}: {str(e)}"

ai_handler = AIHandler()

# ========== 💎 BANK SYSTEM ==========
class BankSystem:
    def generate_card_image(self, user_id, username, card_number, balance):
        try:
            from PIL import Image, ImageDraw, ImageFont
            width, height = 900, 550
            img = Image.new("RGB", (width, height), "#0f0f23")
            draw = ImageDraw.Draw(img)
            for y in range(height):
                r = int(15 + (0.03 * y))
                g = int(15 + (0.01 * y))
                b = int(35 + (0.04 * y))
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            draw.ellipse([(-150, -150), (250, 250)], fill=(233, 69, 96, 30))
            draw.ellipse([(650, 350), (1050, 750)], fill=(78, 205, 196, 20))
            draw.rounded_rectangle([60, 100, 840, 480], radius=25, fill="#1a1a3e", outline="#e94560", width=3)
            draw.rounded_rectangle([680, 120, 820, 190], radius=8, fill="#FFD700")
            draw.text((695, 140), "GOLD", fill="#1a1a3e")
            draw.text((695, 160), "MEMBER", fill="#1a1a3e")
            draw.text((100, 130), "💎 KIMO BANK", fill="#e94560")
            draw.text((100, 170), "البطاقة البنكية الذكية", fill="#a0a0a0")
            draw.line([(100, 210), (800, 210)], fill="#e94560", width=2)
            formatted_card = " ".join([card_number[i:i+4] for i in range(0, 16, 4)])
            draw.text((100, 240), formatted_card, fill="#ffffff")
            draw.text((100, 300), f"المالك: {username}", fill="#a0a0a0")
            draw.text((100, 340), f"الرصيد: {balance:,} ريال 💰", fill="#4ecca3")
            draw.text((100, 380), f"معرف الحساب: {user_id}", fill="#a0a0a0")
            draw.text((100, 420), f"تاريخ الإصدار: {datetime.now().strftime('%Y/%m')}", fill="#a0a0a0")
            draw.text((750, 420), "📶", fill="#ffffff")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf
        except ImportError:
            return None

bank_system = BankSystem()

# ========== 🎵 MUSIC HANDLER ==========
class MusicHandler:
    def __init__(self):
        self.active_sessions = {}
    
    async def download_audio(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            import yt_dlp
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(title)s.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Unknown")
                filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
                return {"file": filename, "title": title}
        except Exception:
            return None
    
    def create_control_panel(self):
        keyboard = [
            [
                InlineKeyboardButton("⏯️ إيقاف مؤقت", callback_data="music_pause"),
                InlineKeyboardButton("⏹️ إيقاف نهائي", callback_data="music_stop")
            ],
            [
                InlineKeyboardButton("🔊 رفع صوت", callback_data="music_vol_up"),
                InlineKeyboardButton("🔉 خفض صوت", callback_data="music_vol_down")
            ],
            [
                InlineKeyboardButton("🎵 مؤثرات صوتية", callback_data="music_effects"),
                InlineKeyboardButton("🗑️ إزالة من القائمة", callback_data="music_remove")
            ],
            [
                InlineKeyboardButton("⏭️ التالي", callback_data="music_next"),
                InlineKeyboardButton("⏮️ السابق", callback_data="music_prev")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

music_handler = MusicHandler()

# ========== 🎮 GAMES ==========
class Games:
    def __init__(self):
        self.words = ["محمد", "الرياض", "برمجة", "تيليجرام", "ذكاء", "اصطناعي", "بنك", "موسيقى", "حاسوب", "شمس"]
        self.countries = {
            "السعودية": "الرياض", "مصر": "القاهرة", "الإمارات": "أبوظبي",
            "الكويت": "الكويت", "قطر": "الدوحة", "البحرين": "المنامة",
            "عمان": "مسقط", "الأردن": "عمان"
        }
        self.general = [
            {"q": "ما هي عاصمة السعودية؟", "a": "الرياض"},
            {"q": "كم عدد أيام الأسبوع؟", "a": "7"},
            {"q": "ما هي أطول سورة في القرآن؟", "a": "البقرة"},
            {"q": "كم عدد أركان الإسلام؟", "a": "5"},
            {"q": "ما هي أولى سور القرآن؟", "a": "الفاتحة"}
        ]
        self.math = [
            {"q": "5 + 7 × 2 = ?", "a": "19"},
            {"q": "√144 = ?", "a": "12"},
            {"q": "12 × 12 = ?", "a": "144"}
        ]
        self.riddles = [
            {"q": "ما هو الشيء الذي كلما أخذت منه كبر؟", "a": "الحفرة"},
            {"q": "ما هو الشيء الذي يمشي بلا رجلين؟", "a": "الساعة"}
        ]
        self.truths = [
            "ما هو الشيء الذي ندمت على فعله في حياتك؟",
            "ما هو سرك الذي لم تخبر به أحداً؟",
            "من هو الشخص الذي تحبه سراً؟"
        ]
        self.would_you_rather = [
            "لو خيروك بين أن تكون غنياً وبين أن تكون مشهوراً؟",
            "لو خيروك بين السفر حول العالم أو العيش في منزل حلمك؟"
        ]
        self.challenges = [
            "تحدي: اكتب جملة بكل حرف من أحرف اسمك!",
            "تحدي: ارسل صورة لوجهك بدون فلاتر!"
        ]
        self.punishments = [
            "عقاب: غنِّ أغنية لمدة 30 ثانية!",
            "عقاب: ارسل رسالة صوتية تقول فيها 'أنا أحب البوت'!"
        ]
        self.ktweet = [
            "كت تويت: وش أكثر شيء يضايقك في الناس؟",
            "كت تويت: وش أغرب موقف صار لك؟"
        ]
        self.wisdom = [
            "الصبر مفتاح الفرج.",
            "من شابه أباه فما ظلم.",
            "الوقت كالسيف إن لم تقطعه قطعك."
        ]
        self.letters = ["أ", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي"]
    
    def get_random_word(self): return random.choice(self.words)
    def get_random_country(self): return random.choice(list(self.countries.keys()))
    def get_random_general(self): return random.choice(self.general)
    def get_random_math(self): return random.choice(self.math)
    def get_random_riddle(self): return random.choice(self.riddles)
    def get_random_truth(self): return random.choice(self.truths)
    def get_random_would_you(self): return random.choice(self.would_you_rather)
    def get_random_challenge(self): return random.choice(self.challenges)
    def get_random_punishment(self): return random.choice(self.punishments)
    def get_random_ktweet(self): return random.choice(self.ktweet)
    def get_random_wisdom(self): return random.choice(self.wisdom)
    def get_random_letter(self): return random.choice(self.letters)

games = Games()

# ========== 👋 WELCOME HANDLER ==========
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status
    if old_status in ["left", "kicked"] and new_status == "member":
        user = update.chat_member.new_chat_member.user
        user_id = user.id
        username = user.username or "لا يوجد"
        first_name = user.first_name or "مستخدم"
        last_name = user.last_name or ""
        db.add_user(user_id, username, first_name, last_name)
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        except:
            photos = None
        join_date = datetime.now().strftime("%Y-%m-%d")
        join_time = datetime.now().strftime("%H:%M:%S")
        welcome_text = f"""
🎉 أهلاً وسهلاً بك يا {first_name}!

📋 معلومات حسابك:
├─ 👤 الاسم: {first_name} {last_name}
├─ 🔖 اليوزر: @{username}
├─ 🆔 الآيدي: `{user_id}`
├─ 📅 التاريخ: {join_date}
└─ ⏰ الوقت: {join_time}

✨ نورت المجموعة! 
🤖 استخدم /start لرؤية قائمة الأوامر
        """
        keyboard = [[InlineKeyboardButton("📜 القوانين", callback_data="show_rules")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if photos and photos.photos:
                photo_file = await photos.photos[0][0].get_file()
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file.file_id,
                    caption=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logging.error(f"Welcome error: {e}")

# ========== 📱 COMMAND HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name or "")
    keyboard = [
        [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu"),
         InlineKeyboardButton("🏦 البنك", callback_data="bank_menu")],
        [InlineKeyboardButton("🎵 الموسيقى", callback_data="music_menu"),
         InlineKeyboardButton("🤖 كيمو", callback_data="ai_menu")],
        [InlineKeyboardButton("📜 القوانين", callback_data="show_rules"),
         InlineKeyboardButton("⚙️ الإدارة", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 أهلاً {user.first_name}!\n\n"
        f"🤖 أنا بوت متكامل بمميزات متعددة:\n"
        f"• حماية قوية 🛡️\n"
        f"• ذكاء اصطناعي ({AI_NAME}) 🤖\n"
        f"• نظام بنك مع بطاقات 💎\n"
        f"• تشغيل موسيقى 🎵\n"
        f"• 30+ لعبة تفاعلية 🎮\n\n"
        f"📌 الأوامر الأساسية:\n"
        f"/كيمو - التحدث مع الذكاء الاصطناعي\n"
        f"/بنك - نظام البنك\n"
        f"/تشغيل_موسيقى - تشغيل من يوتيوب\n"
        f"/اداره - لوحة الإدارة\n\n"
        f"✨ اختر من القائمة:",
        reply_markup=reply_markup
    )

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # استخراج السؤال من /كيمو أو /kimo
    if text.startswith("/كيمو"):
        user_message = text[6:].strip()
    elif text.startswith("/kimo"):
        user_message = text[6:].strip()
    else:
        user_message = " ".join(context.args) if context.args else ""
    
    if not user_message:
        await update.message.reply_text(
            f"🤖 استخدم: /كيمو <سؤالك>\n\n"
            f"💡 مثال: /كيمو ما هي عاصمة السعودية؟\n\n"
            f"📝 أو يمكنك التسولف معي في أي موضوع!"
        )
        return
    
    processing_msg = await update.message.reply_text(f"🤖 {AI_NAME} يفكر... 💭")
    response = await ai_handler.chat(user_message)
    await processing_msg.edit_text(
        f"🤖 {AI_NAME}:\n\n"
        f"{response}\n\n"
        f"— — — — — — — — — —\n"
        f"💡 اكتب /كيمو <سؤالك> للمزيد"
    )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    if not user_data or not user_data[6]:
        card_number = db.create_bank_card(user.id)
        balance = 0
    else:
        card_number = user_data[6]
        balance = user_data[5] or 0
    card_image = bank_system.generate_card_image(
        user.id, user.username or user.first_name, card_number, balance
    )
    keyboard = [
        [InlineKeyboardButton("💰 إيداع", callback_data="bank_deposit"),
         InlineKeyboardButton("💸 سحب", callback_data="bank_withdraw")],
        [InlineKeyboardButton("📊 الرصيد", callback_data="bank_balance"),
         InlineKeyboardButton("🏧 تحويل", callback_data="bank_transfer")],
        [InlineKeyboardButton("🎁 هدية يومية", callback_data="bank_daily")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if card_image:
        await update.message.reply_photo(
            photo=card_image,
            caption=f"🏦 بنك {AI_NAME}\n\n"
                    f"💳 رقم البطاقة: `{card_number}`\n"
                    f"💰 الرصيد: {balance:,} ريال\n"
                    f"👤 المالك: {user.first_name}\n\n"
                    f"✨ البطاقة الذهبية الخاصة بك!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🏦 بنك {AI_NAME}\n\n"
            f"💳 رقم البطاقة: `{card_number}`\n"
            f"💰 الرصيد: {balance:,} ريال\n\n"
            f"(يرجى تثبيت مكتبة Pillow لعرض تصميم البطاقة)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def music_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # استخراج الرابط من /تشغيل_موسيقى أو /music
    if text.startswith("/تشغيل_موسيقى"):
        url = text[len("/تشغيل_موسيقى"):].strip()
    elif text.startswith("/music"):
        url = text[6:].strip()
    else:
        url = context.args[0] if context.args else ""
    
    if not url:
        await update.message.reply_text(
            "🎵 استخدم: /تشغيل_موسيقى <رابط يوتيوب>\n\n"
            "💡 مثال:\n"
            "/تشغيل_موسيقى https://youtube.com/watch?v=...\n\n"
            "📌 سيتم تشغيل الموسيقى لك وحدك مع لوحة تحكم خاصة!"
        )
        return
    
    user_id = update.effective_user.id
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ الرابط غير صالح!")
        return
    
    processing_msg = await update.message.reply_text("🎵 جاري تحميل المقطع... ⏳")
    result = await music_handler.download_audio(url)
    if not result:
        await processing_msg.edit_text(
            "❌ فشل تحميل المقطع.\n\n"
            "⚠️ تأكد من:\n"
            "• صحة الرابط\n"
            "• تثبيت FFmpeg على السيرفر\n"
            "• صلاحيات تحميل الملفات"
        )
        return
    
    try:
        with open(result["file"], "rb") as audio:
            await update.message.reply_audio(
                audio=audio,
                title=result["title"],
                caption=f"🎵 {result['title']}\n\n"
                        f"🎛️ لوحة التحكم الخاصة بك:",
                reply_markup=music_handler.create_control_panel()
            )
        await processing_msg.delete()
        music_handler.active_sessions[user_id] = {
            "file": result["file"],
            "title": result["title"],
            "is_playing": True,
            "volume": 100
        }
    except Exception as e:
        await processing_msg.edit_text(f"❌ حدث خطأ: {str(e)}")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ هذا الأمر للمشرفين فقط!\n\n"
            "🔒 ليس لديك صلاحيات الوصول."
        )
        return
    
    text = update.message.text
    # استخراج الأمر من /اداره أو /admin
    if text.startswith("/اداره"):
        parts = text[len("/اداره"):].strip().split()
    elif text.startswith("/admin"):
        parts = text[7:].strip().split()
    else:
        parts = context.args
    
    if not parts:
        await update.message.reply_text(
            "🔧 أوامر الإدارة المتاحة:\n\n"
            "👤 إدارة الأعضاء:\n"
            "/اداره طرد <آيدي>\n"
            "/اداره ميوت <آيدي> <دقائق>\n"
            "/اداره تحذير <آيدي>\n"
            "/اداره الغاء_ميوت <آيدي>\n\n"
            "📢 الإعلانات:\n"
            "/اداره رسالة <النص>\n\n"
            "📊 المعلومات:\n"
            "/اداره معلومات <آيدي>\n\n"
            "🎮 إدارة الألعاب:\n"
            "/اداره اضف_نقاط <آيدي> <العدد>\n"
            "/اداره خصم_نقاط <آيدي> <العدد>\n\n"
            "💡 مثال: /اداره طرد 123456789"
        )
        return
    
    command = parts[0]
    chat_id = update.effective_chat.id
    
    try:
        if command == "طرد":
            if len(parts) < 2:
                await update.message.reply_text("❌ استخدم: /اداره طرد <آيدي>")
                return
            target_id = int(parts[1])
            await context.bot.ban_chat_member(chat_id, target_id)
            await update.message.reply_text(f"✅ تم طرد المستخدم `{target_id}` بنجاح!", parse_mode="Markdown")
        
        elif command == "ميوت":
            if len(parts) < 3:
                await update.message.reply_text("❌ استخدم: /اداره ميوت <آيدي> <دقائق>")
                return
            target_id = int(parts[1])
            minutes = int(parts[2])
            until_date = datetime.now() + timedelta(minutes=minutes)
            await context.bot.restrict_chat_member(chat_id, target_id, until_date=until_date)
            await update.message.reply_text(
                f"🔇 تم كتم المستخدم `{target_id}`\n"
                f"⏱️ المدة: {minutes} دقيقة",
                parse_mode="Markdown"
            )
        
        elif command == "الغاء_ميوت":
            if len(parts) < 2:
                await update.message.reply_text("❌ استخدم: /اداره الغاء_ميوت <آيدي>")
                return
            target_id = int(parts[1])
            await context.bot.restrict_chat_member(
                chat_id, target_id,
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await update.message.reply_text(f"🔊 تم إلغاء كتم المستخدم `{target_id}`", parse_mode="Markdown")
        
        elif command == "رسالة":
            if len(parts) < 2:
                await update.message.reply_text("❌ استخدم: /اداره رسالة <النص>")
                return
            message = " ".join(parts[1:])
            await context.bot.send_message(chat_id=chat_id, text=f"📢 إعلان من الإدارة:\n\n{message}")
        
        elif command == "تحذير":
            if len(parts) < 2:
                await update.message.reply_text("❌ استخدم: /اداره تحذير <آيدي>")
                return
            target_id = int(parts[1])
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (target_id,))
            cursor.execute("SELECT warnings FROM users WHERE user_id = ?", (target_id,))
            warnings = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            await update.message.reply_text(
                f"⚠️ تحذير للمستخدم `{target_id}`\n"
                f"📊 عدد التحذيرات: {warnings}/3",
                parse_mode="Markdown"
            )
            if warnings >= 3:
                await context.bot.ban_chat_member(chat_id, target_id)
                await update.message.reply_text(f"🚫 تم طرد المستخدم `{target_id}` بسبب 3 تحذيرات!", parse_mode="Markdown")
        
        elif command == "معلومات":
            if len(parts) < 2:
                await update.message.reply_text("❌ استخدم: /اداره معلومات <آيدي>")
                return
            target_id = int(parts[1])
            user_data = db.get_user(target_id)
            if user_data:
                await update.message.reply_text(
                    f"📊 معلومات المستخدم:\n\n"
                    f"🆔 الآيدي: `{user_data[0]}`\n"
                    f"👤 الاسم: {user_data[2]}\n"
                    f"🔖 اليوزر: @{user_data[1]}\n"
                    f"📅 تاريخ الانضمام: {user_data[4]}\n"
                    f"💰 الرصيد: {user_data[5]}\n"
                    f"💳 البطاقة: {user_data[6]}\n"
                    f"⚠️ التحذيرات: {user_data[7]}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ المستخدم غير موجود في القاعدة.")
        
        elif command == "اضف_نقاط":
            if len(parts) < 3:
                await update.message.reply_text("❌ استخدم: /اداره اضف_نقاط <آيدي> <العدد>")
                return
            target_id = int(parts[1])
            points = int(parts[2])
            db.update_balance(target_id, points)
            await update.message.reply_text(f"✅ تم إضافة {points} نقطة للمستخدم `{target_id}`", parse_mode="Markdown")
        
        elif command == "خصم_نقاط":
            if len(parts) < 3:
                await update.message.reply_text("❌ استخدم: /اداره خصم_نقاط <آيدي> <العدد>")
                return
            target_id = int(parts[1])
            points = int(parts[2])
            db.update_balance(target_id, -points)
            await update.message.reply_text(f"✅ تم خصم {points} نقطة من المستخدم `{target_id}`", parse_mode="Markdown")
        
        else:
            await update.message.reply_text("❌ أمر غير معروف. استخدم /اداره لرؤية القائمة.")
    
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")

# ========== 🎮 GAME MENUS ==========
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔤 كلمات", callback_data="game_words"),
         InlineKeyboardButton("🌍 عربي", callback_data="game_arabic")],
        [InlineKeyboardButton("✏️ أكمل", callback_data="game_complete"),
         InlineKeyboardButton("🇬🇧 انجليزي", callback_data="game_english")],
        [InlineKeyboardButton("🔨 تفكيك", callback_data="game_decompose"),
         InlineKeyboardButton("⚡ الاسرع", callback_data="game_fastest")],
        [InlineKeyboardButton("🔄 العكس", callback_data="game_reverse"),
         InlineKeyboardButton("🧩 حزورة", callback_data="game_riddle")],
        [InlineKeyboardButton("📊 ترتيب", callback_data="game_sort"),
         InlineKeyboardButton("🌍 علم دول", callback_data="game_countries")],
        [InlineKeyboardButton("📖 دين", callback_data="game_religion"),
         InlineKeyboardButton("📚 عام", callback_data="game_general")],
        [InlineKeyboardButton("➕ رياضيات", callback_data="game_math"),
         InlineKeyboardButton("📋 مصطلح", callback_data="game_terms")],
        [InlineKeyboardButton("🔧 تركيب", callback_data="game_assemble"),
         InlineKeyboardButton("💭 حكم", callback_data="game_wisdom")],
        [InlineKeyboardButton("🐦 كت تويت", callback_data="game_ktweet"),
         InlineKeyboardButton("🤔 لو خيروك", callback_data="game_would_you")],
        [InlineKeyboardButton("💬 صراحة", callback_data="game_truth"),
         InlineKeyboardButton("⚖️ احكام", callback_data="game_judgments")],
        [InlineKeyboardButton("🎰 الروليت", callback_data="game_roulette"),
         InlineKeyboardButton("🎵 موسيقى", callback_data="game_music")],
        [InlineKeyboardButton("🖼️ صور", callback_data="game_pictures"),
         InlineKeyboardButton("📅 جدول", callback_data="game_schedule")],
        [InlineKeyboardButton("🔍 المختلف", callback_data="game_different"),
         InlineKeyboardButton("🎤 صور فنانين", callback_data="game_artists")],
        [InlineKeyboardButton("⭐ شخصيات بوب", callback_data="game_pop"),
         InlineKeyboardButton("🇰🇷 شخصيات كيبوب", callback_data="game_kpop")],
        [InlineKeyboardButton("🇯🇵 شخصيات انمي", callback_data="game_anime"),
         InlineKeyboardButton("🔤 اختر حرف", callback_data="game_letter")],
        [InlineKeyboardButton("📝 حروف", callback_data="game_letters"),
         InlineKeyboardButton("🎤 بغني", callback_data="game_singing")],
        [InlineKeyboardButton("🎯 حزر", callback_data="game_guess"),
         InlineKeyboardButton("😈 عقاب", callback_data="game_punishment")],
        [InlineKeyboardButton("💺 كرسي اعتراف", callback_data="game_confession"),
         InlineKeyboardButton("🏆 تحديات", callback_data="game_challenges")],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")]
    ]
    await query.edit_message_text(
        "🎮 قائمة الألعاب التفاعلية:\n\n"
        "اختر لعبة من القائمة:\n"
        "• العاب فردية 🧍\n"
        "• العاب جماعية 👥\n"
        "• مسابقات وتحديات 🏆\n\n"
        "🎯 اضغط على اللعبة التي تريدها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game_type = query.data
    user = query.from_user
    
    if game_type == "game_words":
        word = games.get_random_word()
        shuffled = "".join(random.sample(word, len(word)))
        await query.edit_message_text(
            f"🔤 لعبة الكلمات:\n\n"
            f"رتب هذه الحروف لتكوين كلمة صحيحة:\n\n"
            f"📝 {shuffled}\n\n"
            f"💡 اكتب إجابتك في المحادثة!\n"
            f"⏱️ لديك 60 ثانية",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "words", "answer": word, "user_id": user.id}
    
    elif game_type == "game_countries":
        country = games.get_random_country()
        await query.edit_message_text(
            f"🌍 لعبة علم الدول:\n\n"
            f"ما هي عاصمة {country}؟\n\n"
            f"💡 اكتب إجابتك!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "countries", "answer": games.countries[country], "user_id": user.id}
    
    elif game_type == "game_general":
        question = games.get_random_general()
        await query.edit_message_text(
            f"📚 سؤال عام:\n\n"
            f"{question['q']}\n\n"
            f"💡 اكتب إجابتك!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "general", "answer": question["a"], "user_id": user.id}
    
    elif game_type == "game_math":
        question = games.get_random_math()
        await query.edit_message_text(
            f"➕ لعبة الرياضيات:\n\n"
            f"{question['q']}\n\n"
            f"💡 اكتب إجابتك!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "math", "answer": question["a"], "user_id": user.id}
    
    elif game_type == "game_riddle":
        riddle = games.get_random_riddle()
        await query.edit_message_text(
            f"🧩 حزورة:\n\n"
            f"{riddle['q']}\n\n"
            f"💡 ما هو الجواب؟",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "riddle", "answer": riddle["a"], "user_id": user.id}
    
    elif game_type == "game_truth":
        truth = games.get_random_truth()
        await query.edit_message_text(
            f"💬 لعبة صراحة:\n\n"
            f"{truth}\n\n"
            f"📝 اكتب جوابك الصريح!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "truth", "answer": None, "user_id": user.id}
    
    elif game_type == "game_would_you":
        question = games.get_random_would_you()
        await query.edit_message_text(
            f"🤔 لو خيروك:\n\n"
            f"{question}\n\n"
            f"📝 اكتب اختيارك مع السبب!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "would_you", "answer": None, "user_id": user.id}
    
    elif game_type == "game_wisdom":
        wisdom = games.get_random_wisdom()
        await query.edit_message_text(
            f"💭 حكمة اليوم:\n\n"
            f"❝ {wisdom} ❞\n\n"
            f"✨ اكتب تعليقك أو حكمة أخرى!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "wisdom", "answer": None, "user_id": user.id}
    
    elif game_type == "game_ktweet":
        ktweet = games.get_random_ktweet()
        await query.edit_message_text(
            f"🐦 كت تويت:\n\n"
            f"{ktweet}\n\n"
            f"📝 اكتب تغريدتك!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "ktweet", "answer": None, "user_id": user.id}
    
    elif game_type == "game_punishment":
        punishment = games.get_random_punishment()
        await query.edit_message_text(
            f"😈 عقاب:\n\n"
            f"{punishment}\n\n"
            f"⚠️ يجب تنفيذ العقاب! 📸",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "punishment", "answer": None, "user_id": user.id}
    
    elif game_type == "game_challenges":
        challenge = games.get_random_challenge()
        await query.edit_message_text(
            f"🏆 تحدي:\n\n"
            f"{challenge}\n\n"
            f"💪 هل تستطيع تنفيذ التحدي؟",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "challenge", "answer": None, "user_id": user.id}
    
    elif game_type == "game_letter":
        letter = games.get_random_letter()
        await query.edit_message_text(
            f"🔤 اختر حرف:\n\n"
            f"الحرف المختار: {letter}\n\n"
            f"📝 اكتب كلمة تبدأ بهذا الحرف!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "letter", "answer": letter, "user_id": user.id}
    
    elif game_type == "game_roulette":
        result = random.choice(["🟥 أحمر", "⬛ أسود", "🟢 أخضر"])
        color = "🟥" if "أحمر" in result else "⬛" if "أسود" in result else "🟢"
        await query.edit_message_text(
            f"🎰 لعبة الروليت:\n\n"
            f"العجلة تدور... 🎡\n\n"
            f"النتيجة: {result}\n\n"
            f"{'🎉 فزت!' if '🟢' in color else '😅 حاول مرة أخرى!'}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 لعب مرة أخرى", callback_data="game_roulette")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]
            ])
        )
    
    elif game_type == "game_confession":
        await query.edit_message_text(
            f"💺 كرسي الاعتراف:\n\n"
            f"سؤال اليوم: ما هو أكبر سر تخفيه عن أهلك؟\n\n"
            f"📝 اكتب اعترافك (بصراحة)!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]])
        )
        context.user_data["game"] = {"type": "confession", "answer": None, "user_id": user.id}
    
    else:
        await query.edit_message_text(
            f"🎮 {game_type}\n\n"
            f"🚧 هذه اللعبة قيد التطوير!\n"
            f"سيتم إضافتها قريباً...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 لعبة أخرى", callback_data="games_menu")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )

# ========== 🔘 CALLBACK HANDLER ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "show_rules":
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(RULES, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "games_menu":
        await games_menu(update, context)
    
    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu"),
             InlineKeyboardButton("🏦 البنك", callback_data="bank_menu")],
            [InlineKeyboardButton("🎵 الموسيقى", callback_data="music_menu"),
             InlineKeyboardButton("🤖 كيمو", callback_data="ai_menu")],
            [InlineKeyboardButton("📜 القوانين", callback_data="show_rules"),
             InlineKeyboardButton("⚙️ الإدارة", callback_data="admin_menu")]
        ]
        await query.edit_message_text(
            "القائمة الرئيسية:\n\n🤖 اختر من القائمة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "bank_menu":
        user = query.from_user
        user_data = db.get_user(user.id)
        balance = user_data[5] if user_data else 0
        card = user_data[6] if user_data else "غير موجود"
        keyboard = [
            [InlineKeyboardButton("💰 إيداع", callback_data="bank_deposit"),
             InlineKeyboardButton("💸 سحب", callback_data="bank_withdraw")],
            [InlineKeyboardButton("🏧 تحويل", callback_data="bank_transfer"),
             InlineKeyboardButton("🎁 هدية يومية", callback_data="bank_daily")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        await query.edit_message_text(
            f"🏦 بنك {AI_NAME}\n\n"
            f"💳 البطاقة: `{card}`\n"
            f"💰 الرصيد: {balance:,} ريال\n\n"
            f"اختر عملية:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data == "music_menu":
        await query.edit_message_text(
            "🎵 تشغيل الموسيقى:\n\n"
            "استخدم الأمر:\n"
            "`/تشغيل_موسيقى <رابط يوتيوب>`\n\n"
            "💡 المميزات:\n"
            "• تشغيل خاص لكل شخص 🎧\n"
            "• لوحة تحكم بالصوت 🔊\n"
            "• مؤثرات صوتية 🎛️\n"
            "• قائمة تشغيل خاصة 📋",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]),
            parse_mode="Markdown"
        )
    
    elif data == "ai_menu":
        await query.edit_message_text(
            f"🤖 {AI_NAME} - الذكاء الاصطناعي\n\n"
            f"نموذج: `{AI_MODEL}`\n\n"
            f"💬 استخدم الأمر:\n"
            f"`/كيمو <سؤالك>`\n\n"
            f"مثال:\n"
            f"`/كيمو اشرح لي النسبية`\n\n"
            f"✨ يمكنك التسولف في أي موضوع!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]),
            parse_mode="Markdown"
        )
    
    elif data == "admin_menu":
        user = query.from_user
        if user.id != ADMIN_ID:
            await query.edit_message_text(
                "⛔ ليس لديك صلاحيات الوصول!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]])
            )
            return
        await query.edit_message_text(
            "⚙️ لوحة الإدارة:\n\n"
            "استخدم الأمر:\n"
            "`/اداره`\n\n"
            "لرؤية جميع أوامر الإدارة.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]),
            parse_mode="Markdown"
        )
    
    elif data.startswith("game_"):
        await game_handler(update, context)
    
    elif data.startswith("music_"):
        user_id = query.from_user.id
        if user_id not in music_handler.active_sessions:
            await query.edit_message_text("❌ لا يوجد مقطع موسيقي نشط لك!")
            return
        session = music_handler.active_sessions[user_id]
        if data == "music_pause":
            session["is_playing"] = not session["is_playing"]
            status = "▶️ تشغيل" if session["is_playing"] else "⏸️ إيقاف مؤقت"
            await query.edit_message_text(
                f"🎵 {session['title']}\n\n"
                f"الحالة: {status}\n"
                f"🔊 الصوت: {session['volume']}%\n\n"
                f"استخدم لوحة التحكم:",
                reply_markup=music_handler.create_control_panel()
            )
        elif data == "music_stop":
            if os.path.exists(session["file"]):
                os.remove(session["file"])
            del music_handler.active_sessions[user_id]
            await query.edit_message_text("⏹️ تم إيقاف الموسيقى وإزالتها من القائمة.")
        elif data == "music_vol_up":
            session["volume"] = min(100, session["volume"] + 10)
            await query.edit_message_text(
                f"🔊 الصوت: {session['volume']}%\n\n🎵 {session['title']}",
                reply_markup=music_handler.create_control_panel()
            )
        elif data == "music_vol_down":
            session["volume"] = max(0, session["volume"] - 10)
            await query.edit_message_text(
                f"🔉 الصوت: {session['volume']}%\n\n🎵 {session['title']}",
                reply_markup=music_handler.create_control_panel()
            )
        elif data == "music_effects":
            await query.edit_message_text(
                f"🎵 مؤثرات صوتية:\n\n"
                f"• 🎸 صوت غيتار\n"
                f"• 🎹 صوت بيانو\n"
                f"• 🥁 إيقاع\n\n"
                f"(قيد التطوير - يتطلب مكتبات إضافية)",
                reply_markup=music_handler.create_control_panel()
            )
        elif data == "music_remove":
            if os.path.exists(session["file"]):
                os.remove(session["file"])
            del music_handler.active_sessions[user_id]
            await query.edit_message_text("🗑️ تم إزالة الموسيقى من قائمتك الخاصة.")
    
    elif data == "bank_daily":
        user = query.from_user
        db.update_balance(user.id, 100)
        await query.edit_message_text(
            "🎁 هدية يومية!\n\n"
            "✅ تم إضافة 100 ريال لحسابك.\n"
            "🕐 تعال غداً للحصول على المزيد!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏦 العودة للبنك", callback_data="bank_menu")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
    
    elif data in ["bank_deposit", "bank_withdraw", "bank_transfer"]:
        await query.edit_message_text(
            f"🏦 هذه الميزة قيد التطوير!\n\n"
            f"سيتم إضافتها قريباً...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏦 العودة للبنك", callback_data="bank_menu")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )

# ========== 💬 MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    if "game" in context.user_data:
        game = context.user_data["game"]
        if game.get("user_id") != user.id:
            return
        if game["answer"] and text.strip() == game["answer"]:
            await update.message.reply_text(
                "✅ إجابة صحيحة! 🎉\n\n"
                f"🎁 ربحت 10 نقاط!\n"
                f"💰 تم إضافتها لحسابك في البنك."
            )
            db.update_balance(user.id, 10)
            del context.user_data["game"]
        elif game["answer"] and text.strip() != game["answer"]:
            await update.message.reply_text(
                "❌ إجابة خاطئة!\n"
                "💡 حاول مرة أخرى أو اضغط /الغاء للخروج"
            )
        elif not game["answer"]:
            await update.message.reply_text(
                "✅ تم تسجيل إجابتك! 📝\n\n"
                "شكراً لمشاركتك! 🎉"
            )
            del context.user_data["game"]

# ========== 🛡️ PROTECTION ==========
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    if user.id == ADMIN_ID:
        return
    text = update.message.text or ""
    caption = update.message.caption or ""
    content = text + caption
    suspicious = ["t.me/joinchat", "t.me/+", "bit.ly", "short.link", "0px", "javascript:"]
    for link in suspicious:
        if link in content.lower():
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"⚠️ {user.first_name}\n"
                    f"تم حذف رسالتك لاحتوائها على رابط مشبوه! 🚫"
                )
                return
            except:
                pass
    bad_words = ["سب", "شتم", "قذف"]
    for word in bad_words:
        if word in content:
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"🚫 {user.first_name}\n"
                    f"تم حذف رسالتك لاحتوائها على كلمات مسيئة!"
                )
                db.update_balance(user.id, -5)
                return
            except:
                pass

# ========== 🚀 MAIN ==========
def main():
    # التحقق من وجود التوكن (ما يتحقق من القيمة الفعلية، يتحقق من عدم كونه فارغ)
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
        print("❌ خطأ: لم تقم بوضع توكن البوت!")
        return
    
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        print("⚠️ تحذير: لم تقم بوضع مفتاح Groq API!")
        print("🤖 لن يعمل الذكاء الاصطناعي حتى تضع المفتاح.")
    
    os.makedirs("downloads", exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # الأوامر الإنجليزية
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("kimo", ai_command))
    application.add_handler(CommandHandler("bank", bank_command))
    application.add_handler(CommandHandler("music", music_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # الأوامر العربية باستخدام Regex (بديل عن CommandHandler)
    application.add_handler(MessageHandler(
        filters.Regex(r"^/كيمو(\s+.*)?$") & filters.TEXT, ai_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r"^/بنك(\s+.*)?$") & filters.TEXT, bank_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r"^/تشغيل_موسيقى(\s+.*)?$") & filters.TEXT, music_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r"^/اداره(\s+.*)?$") & filters.TEXT, admin_command
    ))
    
    application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, protect_group))
    
    print("🤖 بوت KIMO يعمل الآن!")
    print("✅ اضغط Ctrl+C للإيقاف")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
'''

with open('/mnt/agents/output/bot_fixed.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ تم إنشاء الملف المصحح!")
print(f"📁 المسار: /mnt/agents/output/bot_fixed.py")
print(f"📊 عدد الأسطر: {len(code.splitlines())}")
