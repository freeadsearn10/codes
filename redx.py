import logging
import asyncio
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler
)
import requests

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
TOKEN = "7739572809:AAGiBQbxoh33Pgft7y3Ju5t832BdLzCJFmc"

CON_API = "https://refinepremiumsms.xyz/con.php"
NUM_API_BASE = "https://refinepremiumsms.xyz/num.php?range="
INFO_API = "https://refinepremiumsms.xyz/info.php"

DATA_FILE = "redx_bot_data.json"

# States
LANGUAGE, MAIN_MENU = range(2)

# Global data (persistent)
user_numbers = {}     # user_id_str -> list of dicts
user_language = {}    # user_id_str -> lang code

def load_data():
    global user_numbers, user_language
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_numbers = data.get("numbers", {})
                user_language = data.get("langs", {})
            logger.info("Data loaded from JSON")
        except Exception as e:
            logger.error(f"JSON load error: {e}")
    else:
        logger.info("No saved data, starting fresh")

def save_data():
    data = {
        "numbers": user_numbers,
        "langs": user_language
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Data saved to JSON")
    except Exception as e:
        logger.error(f"JSON save error: {e}")

load_data()

# ==================== Multi-Language Texts ====================
TEXTS = {
    'en': {
        'welcome': "🌟 Welcome to RedX OTP Bot 🌟\nChoose your action:",
        'select_lang': "Please select your language:",
        'lang_set': "Language set successfully!",
        'get_number': "📱 Get Number",
        'my_numbers': "📋 My Numbers",
        'console_info': "🖥️ Console Info",
        'select_app': "Select App:",
        'whatsapp': "WhatsApp",
        'facebook': "Facebook",
        'back': "Back",
        'no_numbers': "No numbers taken yet.",
        'your_numbers': "Your Numbers:",
        'loading': "Loading...",
        'success': "🎉 Success!\nNumber: +{}\nRange: {}\nCountry: {}",
        'failed': "Failed to get number",
        'checking': "Checking SMS...",
        'sms_result': "SMS for +{}:\nStatus: {}\nMessage: {}",
        'no_sms': "No SMS yet",
        'chkapi_title': "API Test Results (real response):",
    },
    'bn': {
        'welcome': "🌟 রেডএক্স ওটিপি বটে স্বাগতম 🌟\nঅপশন বেছে নিন:",
        'select_lang': "ভাষা বেছে নিন:",
        'lang_set': "ভাষা সেট হয়েছে!",
        'get_number': "📱 নতুন নম্বর",
        'my_numbers': "📋 আমার নম্বরগুলো",
        'console_info': "🖥️ কনসোল তথ্য",
        'select_app': "অ্যাপ বেছে নিন:",
        'whatsapp': "হোয়াটসঅ্যাপ",
        'facebook': "ফেসবুক",
        'back': "ফিরে যান",
        'no_numbers': "এখনো কোনো নম্বর নেননি।",
        'your_numbers': "আপনার নম্বরসমূহ:",
        'loading': "লোড হচ্ছে...",
        'success': "🎉 সফল!\nনম্বর: +{}\nরেঞ্জ: {}\nদেশ: {}",
        'failed': "নম্বর নিতে ব্যর্থ",
        'checking': "SMS চেক করা হচ্ছে...",
        'sms_result': "+{} এর SMS:\nস্ট্যাটাস: {}\nমেসেজ: {}",
        'no_sms': "এখনো কোনো SMS নেই",
        'chkapi_title': "API টেস্ট রেসপন্স (রিয়েল):",
    },
    'hi': {
        'welcome': "🌟 RedX OTP Bot में आपका स्वागत है 🌟",
        'select_lang': "कृपया भाषा चुनें:",
        'lang_set': "भाषा सफलतापूर्वक सेट की गई!",
    },
    'ar': {
        'welcome': "🌟 مرحبا بك في بوت RedX OTP 🌟",
        'select_lang': "يرجى اختيار اللغة:",
        'lang_set': "تم تعيين اللغة بنجاح!",
    }
}

def get_text(uid: str, key: str) -> str:
    lang = user_language.get(uid, 'en')
    return TEXTS.get(lang, TEXTS['en']).get(key, key)

# ==================== Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = str(update.effective_user.id)
    if uid not in user_language:
        kb = [
            [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
            [InlineKeyboardButton("বাংলা 🇧🇩", callback_data="lang_bn")],
            [InlineKeyboardButton("हिंदी 🇮🇳", callback_data="lang_hi")],
            [InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar")],
        ]
        await update.message.reply_text(get_text(uid, "select_lang"), reply_markup=InlineKeyboardMarkup(kb))
        return LANGUAGE

    await show_main_menu(update, context)
    return ConversationHandler.END


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    lang_map = {"lang_en": "en", "lang_bn": "bn", "lang_hi": "hi", "lang_ar": "ar"}
    lang = lang_map.get(query.data)
    if lang:
        uid = str(query.from_user.id)
        user_language[uid] = lang
        save_data()
        await query.edit_message_text(get_text(uid, "lang_set"))
        await asyncio.sleep(1.2)
        await show_main_menu(update, context)
    return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    kb = [
        [InlineKeyboardButton(get_text(uid, "get_number"), callback_data="get_number")],
        [InlineKeyboardButton(get_text(uid, "my_numbers"), callback_data="my_numbers")],
        [InlineKeyboardButton(get_text(uid, "console_info"), callback_data="console_info")],
    ]
    text = get_text(uid, "welcome")
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')


async def chkapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = get_text(uid, "chkapi_title") + "\n\n"

    # con.php
    try:
        r = requests.get(CON_API, timeout=10)
        d = r.json()
        text += "con.php Response:\n```json\n" + json.dumps(d, indent=2)[:1500] + "\n```\n\n"
    except Exception as e:
        text += f"con.php: Error - {str(e)[:100]}\n\n"

    # info.php
    try:
        r = requests.get(INFO_API, timeout=10)
        d = r.json()
        text += "info.php Response:\n```json\n" + json.dumps(d, indent=2)[:1500] + "\n```\n\n"
    except Exception as e:
        text += f"info.php: Error - {str(e)[:100]}\n\n"

    # num.php test
    try:
        test_range = "23762"  # Change if needed
        r = requests.get(f"{NUM_API_BASE}{test_range}", timeout=10)
        d = r.json()
        text += f"num.php Test ({test_range}):\n```json\n" + json.dumps(d, indent=2)[:1500] + "\n```"
    except Exception as e:
        text += f"num.php Test: Error - {str(e)[:100]}"

    await update.message.reply_text(text, parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = str(query.from_user.id)

    if data == "get_number":
        kb = [
            [InlineKeyboardButton(get_text(uid, "whatsapp"), callback_data="app_whatsapp")],
            [InlineKeyboardButton(get_text(uid, "facebook"), callback_data="app_facebook")],
            [InlineKeyboardButton(get_text(uid, "back"), callback_data="back_menu")],
        ]
        await query.edit_message_text(get_text(uid, "select_app"), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == "back_menu":
        await show_main_menu(update, context)

    elif data == "my_numbers":
        nums = user_numbers.get(uid, [])
        if not nums:
            await query.edit_message_text(get_text(uid, "no_numbers"))
            return

        text = get_text(uid, "your_numbers") + "\n\n"
        kb = []
        for i, n in enumerate(nums, 1):
            text += f"{i}. +{n['number']} ({n['app']})\n"
            kb.append([InlineKeyboardButton(f"Check SMS #{i}", callback_data=f"checksms_{n['number']}")])

        kb.append([InlineKeyboardButton(get_text(uid, "back"), callback_data="back_menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == "console_info":
        msg = await query.edit_message_text(get_text(uid, "loading"))
        try:
            r = requests.get(CON_API, timeout=10)
            logs = r.json().get("data", {}).get("logs", [])
            text = f"Recent logs ({len(logs)}):\n\n"
            for log in logs[:10]:
                text += f"{log.get('time', 'N/A')} | {log.get('app_name', 'N/A')} | {log.get('range', 'N/A')} | {log.get('country', 'N/A')}\n"
            await msg.edit_text(text, parse_mode='Markdown')
        except:
            await msg.edit_text("Console load failed")

    elif data.startswith("app_"):
        app = data.split("_")[1]
        msg = await query.edit_message_text(f"Loading {app} ranges...")
        try:
            r = requests.get(CON_API, timeout=10)
            logs = r.json().get("data", {}).get("logs", [])
            ranges = {}
            for log in logs:
                if log.get("app_name", "").lower() == app.lower():
                    rg = log.get("range")
                    if rg:
                        ranges[rg] = ranges.get(rg, 0) + 1

            if not ranges:
                await msg.edit_text("No ranges found")
                return

            kb = []
            for rg, count in sorted(ranges.items(), key=lambda x: x[1], reverse=True)[:10]:
                kb.append([InlineKeyboardButton(f"{rg} ({count}x)", callback_data=f"range_{app}_{rg}")])

            kb.append([InlineKeyboardButton(get_text(uid, "back"), callback_data="get_number")])
            await msg.edit_text(f"{app.capitalize()} Ranges:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        except:
            await msg.edit_text("Error loading ranges")

    elif data.startswith("range_"):
        _, app, rg = data.split("_", 2)
        msg = await query.edit_message_text("Allocating number...")
        try:
            r = requests.get(f"{NUM_API_BASE}{rg}", timeout=12)
            res = r.json()
            if res.get("success"):
                info = res.get("full_response", {}).get("data", {})
                number = info.get("full_number", "N/A")
                country = info.get("country", "Unknown")

                user_numbers.setdefault(uid, []).append({
                    "number": number,
                    "range": rg,
                    "app": app,
                    "country": country,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_data()

                kb = [
                    [InlineKeyboardButton("New Number", callback_data="get_number")],
                    [InlineKeyboardButton("Check SMS", callback_data=f"checksms_{number}")],
                    [InlineKeyboardButton(get_text(uid, "back"), callback_data="back_menu")],
                ]
                await msg.edit_text(
                    get_text(uid, "success").format(number, rg, country),
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode='Markdown'
                )
            else:
                await msg.edit_text(get_text(uid, "failed"))
        except Exception as e:
            await msg.edit_text(f"Error: {str(e)[:100]}")

    elif data.startswith("checksms_"):
        num = data.split("_")[1]
        msg = await query.edit_message_text(get_text(uid, "checking").format(num))

        try:
            r = requests.get(INFO_API, timeout=15)
            r.raise_for_status()

            if not r.text.strip():
                await msg.edit_text("Server returned empty response")
                return

            d = r.json()

            sms_text = get_text(uid, "no_sms")
            status = "Unknown"

            numbers_list = d.get("data", {}).get("numbers", []) if isinstance(d.get("data"), dict) else d.get("data", []) if isinstance(d.get("data"), list) else []

            for item in numbers_list:
                if item.get("number") == num:
                    sms = item.get("message", "").strip() or item.get("otp", "").strip()
                    sms_text = sms if sms else "No message received"
                    status = item.get("status", "Unknown")
                    break

            kb = [
                [InlineKeyboardButton("Check Again", callback_data=f"checksms_{num}")],
                [InlineKeyboardButton(get_text(uid, "back"), callback_data="my_numbers")]
            ]

            await msg.edit_text(
                get_text(uid, "sms_result").format(num, status, sms_text),
                reply_markup=InlineKeyboardMarkup(kb)
            )

        except requests.exceptions.Timeout:
            await msg.edit_text("Server timeout. Try later.")
        except requests.exceptions.HTTPError as e:
            await msg.edit_text(f"Server error: {r.status_code}")
        except json.JSONDecodeError:
            await msg.edit_text("API returned invalid format (not JSON). Server issue. Try again in 10-15 min.")
        except Exception as e:
            await msg.edit_text(f"Error: {str(e)[:100]}")
            logger.error(f"SMS check error: {e}")

    save_data()


def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [CallbackQueryHandler(set_language, pattern="^lang_")],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    print("RedX OTP Bot started - Full features with 4 languages + JSON persistence")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
