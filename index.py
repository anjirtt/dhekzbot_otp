#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
from urllib.parse import urljoin
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# --- CONFIG AREA ---
YOUR_BOT_TOKEN = "8537047218:AAGDJQz8cKmVJDa7_MXjmTrZtZUGCQCXo9w"  # GANTI INI ANJIR!
ADMIN_CHAT_IDS = ["8195907276"]  # User ID Telegram lo
INITIAL_CHAT_IDS = ["-1003905860336"]  # ID grup/channel awal

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = "caminating.com"
PASSWORD = "sojit@##"

POLLING_INTERVAL = 15  # Detik. Jangan 1 detik, nanti kena banned goblok!
STATE_FILE = "processed_sms_ids.json"
CHAT_IDS_FILE = "chat_ids.json"

# --- COUNTRY FLAGS ---
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Argentina": "🇦🇷",
    "Australia": "🇦🇺", "Austria": "🇦🇹", "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩",
    "Belgium": "🇧🇪", "Brazil": "🇧🇷", "Canada": "🇨🇦", "China": "🇨🇳",
    "Colombia": "🇨🇴", "Egypt": "🇪🇬", "France": "🇫🇷", "Germany": "🇩🇪",
    "India": "🇮🇳", "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶",
    "Israel": "🇮🇱", "Italy": "🇮🇹", "Japan": "🇯🇵", "Jordan": "🇯🇴",
    "Kuwait": "🇰🇼", "Malaysia": "🇲🇾", "Mexico": "🇲🇽", "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱", "Nigeria": "🇳🇬", "Pakistan": "🇵🇰", "Philippines": "🇵🇭",
    "Poland": "🇵🇱", "Qatar": "🇶🇦", "Russia": "🇷🇺", "Saudi Arabia": "🇸🇦",
    "Singapore": "🇸🇬", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Spain": "🇪🇸",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Thailand": "🇹🇭", "Turkey": "🇹🇷",
    "UAE": "🇦🇪", "UK": "🇬🇧", "USA": "🇺🇸", "Vietnam": "🇻🇳",
    "Unknown": "🏴‍☠️"
}

SERVICE_KEYWORDS = {
    "WhatsApp": ["whatsapp"], "Telegram": ["telegram"], "Facebook": ["facebook"],
    "Instagram": ["instagram"], "Google": ["google"], "Gmail": ["gmail"],
    "TikTok": ["tiktok"], "Snapchat": ["snapchat"], "Twitter": ["twitter"],
    "Amazon": ["amazon"], "Netflix": ["netflix"], "Spotify": ["spotify"],
    "Discord": ["discord"], "PayPal": ["paypal"], "Binance": ["binance"],
    "Coinbase": ["coinbase"], "Uber": ["uber"], "Airbnb": ["airbnb"],
    "Microsoft": ["microsoft"], "Apple": ["apple"], "Yahoo": ["yahoo"],
    "Steam": ["steam"], "LinkedIn": ["linkedin"], "Reddit": ["reddit"],
    "Tinder": ["tinder"], "OnlyFans": ["onlyfans"], "Signal": ["signal"]
}

SERVICE_EMOJIS = {
    "WhatsApp": "🟢", "Telegram": "📩", "Facebook": "📘", "Instagram": "📸",
    "Google": "🔍", "Gmail": "✉️", "TikTok": "🎵", "Snapchat": "👻",
    "Twitter": "🐦", "Amazon": "🛒", "Netflix": "🎬", "Spotify": "🎶",
    "Discord": "🗨️", "PayPal": "💰", "Binance": "🪙", "Coinbase": "🪙",
    "Uber": "🚗", "Airbnb": "🏠", "Microsoft": "🪟", "Apple": "🍏",
    "Yahoo": "🟣", "Steam": "🎮", "LinkedIn": "💼", "Reddit": "👽",
    "Tinder": "🔥", "OnlyFans": "🔞", "Signal": "🔐", "Unknown": "❓"
}

# --- JSON HELPERS ---
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_chat_ids():
    return load_json(CHAT_IDS_FILE, INITIAL_CHAT_IDS)

def save_chat_ids(ids):
    save_json(CHAT_IDS_FILE, ids)

def load_processed_ids():
    return set(load_json(STATE_FILE, []))

def save_processed_id(sid):
    ids = load_processed_ids()
    ids.add(sid)
    save_json(STATE_FILE, list(ids))

# --- COMMAND HANDLERS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS:
        await update.message.reply_text("❌ Lu bukan admin, minggir!")
        return
    await update.message.reply_text(
        "✅ *dhekzEdan SMS Bot Ready!*\n"
        "/addchat <id> — Tambah chat ID\n"
        "/remchat <id> — Hapus chat ID\n"
        "/listchat — List semua chat ID",
        parse_mode="Markdown"
    )

async def addchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS:
        return
    try:
        cid = ctx.args[0]
        ids = load_chat_ids()
        if cid not in ids:
            ids.append(cid)
            save_chat_ids(ids)
            await update.message.reply_text(f"✅ Chat ID `{cid}` ditambahin!", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Udah ada goblok!")
    except:
        await update.message.reply_text("❌ Format: /addchat <id>")

async def remchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS:
        return
    try:
        cid = ctx.args[0]
        ids = load_chat_ids()
        if cid in ids:
            ids.remove(cid)
            save_chat_ids(ids)
            await update.message.reply_text(f"✅ Chat ID `{cid}` dikick!", parse_mode="Markdown")
        else:
            await update.message.reply_text("🤔 Gak ketemu tuh ID!")
    except:
        await update.message.reply_text("❌ Format: /remchat <id>")

async def listchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS:
        return
    ids = load_chat_ids()
    msg = "📜 *Chat ID Terdaftar:*\n" + "\n".join(f"`{i}`" for i in ids) if ids else "Kosong!"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- SMS FETCHER ---
async def fetch_sms(client, headers, csrf_token):
    all_msgs = []
    try:
        today = datetime.utcnow()
        start = today - timedelta(days=1)
        fdate = start.strftime('%m/%d/%Y')
        tdate = today.strftime('%m/%d/%Y')

        # Get groups
        r1 = await client.post(SMS_API_ENDPOINT, headers=headers,
                               data={'from': fdate, 'to': tdate, '_token': csrf_token})
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        groups = soup1.find_all('div', class_='pointer')
        if not groups:
            return []

        group_ids = []
        for g in groups:
            onclick = g.get('onclick', '')
            m = re.search(r"getDetials\('(.+?)'\)", onclick)
            if m:
                group_ids.append(m.group(1))

        for gid in group_ids:
            r2 = await client.post(f"{BASE_URL}portal/sms/received/getsms/number",
                                   headers=headers,
                                   data={'start': fdate, 'end': tdate, 'range': gid, '_token': csrf_token})
            soup2 = BeautifulSoup(r2.text, 'html.parser')
            numbers_div = soup2.select("div[onclick*='getDetialsNumber']")
            phones = [d.text.strip() for d in numbers_div]

            for phone in phones:
                r3 = await client.post(f"{BASE_URL}portal/sms/received/getsms/number/sms",
                                       headers=headers,
                                       data={'start': fdate, 'end': tdate, 'Number': phone, 'Range': gid, '_token': csrf_token})
                soup3 = BeautifulSoup(r3.text, 'html.parser')
                cards = soup3.find_all('div', class_='card-body')

                for card in cards:
                    p = card.find('p', class_='mb-0')
                    if not p:
                        continue
                    sms_text = p.get_text(separator='\n').strip()
                    country = gid.split('(')[0].strip() if '(' in gid else gid.strip()
                    service = "Unknown"
                    lower = sms_text.lower()
                    for svc, kws in SERVICE_KEYWORDS.items():
                        if any(k in lower for k in kws):
                            service = svc
                            break
                    code_match = re.search(r'\b(\d{4,8})\b', sms_text)
                    code = code_match.group(1) if code_match else "N/A"
                    flag = COUNTRY_FLAGS.get(country, "🏴‍☠️")
                    uid = f"{phone}-{hash(sms_text)}"

                    all_msgs.append({
                        "id": uid, "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "number": phone, "country": country, "flag": flag,
                        "service": service, "code": code, "full_sms": sms_text
                    })
        return all_msgs
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        traceback.print_exc()
        return []

# --- SEND TO TELEGRAM ---
async def send_msg(ctx, chat_id, msg):
    try:
        emoji = SERVICE_EMOJIS.get(msg['service'], "❓")
        text = (
            f"🔔 *OTP MASUK BOSS!*\n\n"
            f"📞 *Nomor:* `{msg['number']}`\n"
            f"🔑 *Kode:* `{msg['code']}`\n"
            f"🏆 *Layanan:* {emoji} {msg['service']}\n"
            f"🌍 *Negara:* {msg['flag']} {msg['country']}\n"
            f"⏰ *Waktu:* `{msg['time']}`\n\n"
            f"💬 *Pesan:*\n```\n{msg['full_sms']}\n```"
        )
        await ctx.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Send error ke {chat_id}: {e}")

# --- MAIN JOB ---
async def check_sms_job(ctx: ContextTypes.DEFAULT_TYPE):
    print(f"\n--- [{datetime.utcnow()}] Cek SMS ---")
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            # Login
            login_page = await client.get(LOGIN_URL, headers=headers)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            token_input = soup.find('input', {'name': '_token'})
            login_data = {'email': USERNAME, 'password': PASSWORD}
            if token_input:
                login_data['_token'] = token_input['value']

            login_res = await client.post(LOGIN_URL, data=login_data, headers=headers)
            if "login" in str(login_res.url):
                print("❌ Login gagal!")
                return
            print("✅ Login sukses!")

            # CSRF
            dash_soup = BeautifulSoup(login_res.text, 'html.parser')
            meta = dash_soup.find('meta', {'name': 'csrf-token'})
            if not meta:
                print("❌ CSRF token gak ketemu!")
                return
            csrf = meta.get('content')
            headers['Referer'] = str(login_res.url)

            # Ambil SMS
            messages = await fetch_sms(client, headers, csrf)
            if not messages:
                print("✔️ Gak ada SMS baru.")
                return

            processed = load_processed_ids()
            recipients = load_chat_ids()
            new_count = 0

            for msg in reversed(messages):
                if msg['id'] not in processed:
                    new_count += 1
                    print(f"✔️ SMS baru: {msg['number']} | {msg['service']}")
                    for cid in recipients:
                        await send_msg(ctx, cid, msg)
                    save_processed_id(msg['id'])

            if new_count > 0:
                print(f"✅ {new_count} SMS terkirim ke Telegram.")

        except Exception as e:
            print(f"❌ Error utama: {e}")
            traceback.print_exc()

# --- MAIN ---
def main():
    print("🚀 dhekzEdan SMS Bot Starting...")
    if not YOUR_BOT_TOKEN or "ISI_TOKEN" in YOUR_BOT_TOKEN:
        print("🔴 GANTI BOT TOKEN DULU ANJIR!")
        return

    app = Application.builder().token(YOUR_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addchat", addchat))
    app.add_handler(CommandHandler("remchat", remchat))
    app.add_handler(CommandHandler("listchat", listchat))

    app.job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL, first=5)
    print(f"🔄 Cek setiap {POLLING_INTERVAL} detik. Bot online!")
    app.run_polling()

if __name__ == "__main__":
    main()