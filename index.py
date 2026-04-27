#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, re, json, os, traceback, random
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup

# -------------------- CONFIG --------------------
YOUR_BOT_TOKEN = "8537047218:AAGDJQz8cKmVJDa7_MXjmTrZtZUGCQCXo9w"
ADMIN_CHAT_IDS = ["8195907276"]
INITIAL_CHAT_IDS = ["-1003905860336"]

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"
USERNAME = "caminating.com"
PASSWORD = "sojit@##"

POLLING_INTERVAL = 15
STATE_FILE = "processed_sms_ids.json"
CHAT_IDS_FILE = "chat_ids.json"
MONITORED_FILE = "monitored_numbers.json"

# -------------------- COUNTRY FLAGS (lengkap) --------------------
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
    "UAE": "🇦🇪", "UK": "🇬🇧", "USA": "🇺🇸", "Vietnam": "🇻🇳", "Unknown": "🏴‍☠️"
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

TARGET_COUNTRIES = {
    "us": {"name": "USA", "flag": "🇺🇸", "codes": ["+1"]},
    "uk": {"name": "UK", "flag": "🇬🇧", "codes": ["+44"]},
    "in": {"name": "INDIA", "flag": "🇮🇳", "codes": ["+91"]},
    "id": {"name": "INDONESIA", "flag": "🇮🇩", "codes": ["+62"]},
    "ca": {"name": "CANADA", "flag": "🇨🇦", "codes": ["+1"]},
    "br": {"name": "BRAZIL", "flag": "🇧🇷", "codes": ["+55"]},
}

# -------------------- JSON HELPERS --------------------
def load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path) as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, 'w') as f: json.dump(data, f, indent=2)

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

def load_monitored_numbers():
    return load_json(MONITORED_FILE, [])

def save_monitored_numbers(numbers):
    save_json(MONITORED_FILE, numbers)

# -------------------- SCRAPE NOMOR PUBLIK --------------------
async def scrape_numbers_by_country(country_key):
    all_numbers = []
    headers = {"User-Agent": "Mozilla/5.0"}
    country_info = TARGET_COUNTRIES[country_key]
    codes = country_info["codes"]

    # Quackr
    try:
        url = f"https://quackr.io/numbers/{country_key}"
        r = await httpx.AsyncClient(timeout=15, headers=headers).get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        for cell in soup.select("td.number, li.number, span.number"):
            num = cell.get_text(strip=True)
            if any(num.startswith(c) for c in codes):
                all_numbers.append({"number": num, "source": "Quackr"})
    except: pass

    # SMS24
    try:
        url = f"https://sms24.me/en/numbers/{country_key}"
        r = await httpx.AsyncClient(timeout=15, headers=headers).get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        for cell in soup.select("a.number-link, div.number, span.number"):
            num = cell.get_text(strip=True)
            if any(num.startswith(c) for c in codes):
                all_numbers.append({"number": num, "source": "SMS24"})
    except: pass

    # ReceiveSMS (US/UK/CA only)
    if country_key in ["us", "uk", "ca"]:
        try:
            url = "https://receive-sms.cc/"
            r = await httpx.AsyncClient(timeout=15, headers=headers).get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            for cell in soup.select("div.number-box, span.number, a.number"):
                num = cell.get_text(strip=True)
                if any(num.startswith(c) for c in codes):
                    all_numbers.append({"number": num, "source": "ReceiveSMS"})
        except: pass

    # Hapus duplikat
    seen = set()
    unique = [n for n in all_numbers if n['number'] not in seen and not seen.add(n['number'])]
    return unique[:10]

# -------------------- MONITORING SMS PUBLIK --------------------
async def check_public_sms(number, source):
    headers = {"User-Agent": "Mozilla/5.0"}
    messages = []
    if source == "Quackr":
        try:
            url = f"https://quackr.io/numbers/{number.replace('+', '')}"
            r = await httpx.AsyncClient(timeout=15, headers=headers).get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            for msg_div in soup.select("div.message, div.sms, li.sms"):
                sender = msg_div.select_one(".sender, .from").get_text(strip=True) if msg_div.select_one(".sender, .from") else "Unknown"
                txt = msg_div.select_one(".text, .body").get_text(strip=True) if msg_div.select_one(".text, .body") else ""
                time_str = msg_div.select_one(".time, .date").get_text(strip=True) if msg_div.select_one(".time, .date") else datetime.utcnow().strftime("%H:%M")
                if txt:
                    messages.append({"sender": sender, "text": txt, "time": time_str})
        except: pass
    elif source == "SMS24":
        try:
            url = f"https://sms24.me/en/numbers/{number.replace('+', '')}"
            r = await httpx.AsyncClient(timeout=15, headers=headers).get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            for msg_div in soup.select("div.message, li.message"):
                txt = msg_div.get_text(strip=True)
                if txt:
                    messages.append({"sender": "Unknown", "text": txt, "time": datetime.utcnow().strftime("%H:%M")})
        except: pass
    return messages

# -------------------- HANDLER COMMANDS --------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS:
        return await update.message.reply_text("❌ Lu bukan admin, minggir!")
    keyboard = [
        [InlineKeyboardButton("🇺🇸 USA", callback_data='get_us')],
        [InlineKeyboardButton("🇬🇧 UK", callback_data='get_uk')],
        [InlineKeyboardButton("🇮🇳 INDIA", callback_data='get_in')],
        [InlineKeyboardButton("🇮🇩 INDONESIA", callback_data='get_id')],
        [InlineKeyboardButton("🇨🇦 CANADA", callback_data='get_ca')],
        [InlineKeyboardButton("🇧🇷 BRAZIL", callback_data='get_br')],
        [InlineKeyboardButton("📁 EXPORT SEMUA", callback_data='export_all')],
    ]
    await update.message.reply_text(
        "🌍 **PILIH NEGARA UNTUK NOMOR SEGAR:**\n\n"
        "_Klik tombol di bawah, bot kirim nomor + bisa langsung dimonitor._",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def addchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS: return
    try:
        cid = ctx.args[0]; ids = load_chat_ids()
        if cid not in ids:
            ids.append(cid); save_chat_ids(ids)
            await update.message.reply_text(f"✅ Chat ID `{cid}` ditambahin!")
        else: await update.message.reply_text("⚠️ Udah ada goblok!")
    except: await update.message.reply_text("❌ Format: /addchat <id>")

async def remchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS: return
    try:
        cid = ctx.args[0]; ids = load_chat_ids()
        if cid in ids:
            ids.remove(cid); save_chat_ids(ids)
            await update.message.reply_text(f"✅ Chat ID `{cid}` dikick!")
        else: await update.message.reply_text("🤔 Gak ketemu tuh ID!")
    except: await update.message.reply_text("❌ Format: /remchat <id>")

async def listchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS: return
    ids = load_chat_ids()
    msg = "📜 *Chat ID Terdaftar:*\n" + "\n".join(f"`{i}`" for i in ids) if ids else "Kosong!"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monitored(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_CHAT_IDS: return
    numbers = load_monitored_numbers()
    if not numbers:
        return await update.message.reply_text("❌ Belum ada nomor yang dimonitor.")
    text = "📡 *Nomor yang lagi dimonitor:*\n"
    for n in numbers:
        text += f"• `{n['number']}` ({n['source']})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# -------------------- CALLBACK HANDLER (TOMBOL) --------------------
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "export_all":
        all_nums = []
        for key in TARGET_COUNTRIES:
            all_nums.extend(await scrape_numbers_by_country(key))
        if not all_nums:
            return await query.edit_message_text("❌ Gak ada nomor.")
        fname = "all_numbers.txt"
        with open(fname, "w") as f:
            for n in all_nums: f.write(f"{n['number']} [{n['source']}]\n")
        with open(fname, "rb") as f:
            await query.message.reply_document(InputFile(f, filename=fname),
                                               caption=f"📦 {len(all_nums)} nomor segar.")
        os.remove(fname)
        return

    if data.startswith("monitor_"):
        # Tambahkan nomor ke daftar monitor
        _, number, source = data.split("_", 2)
        monitored = load_monitored_numbers()
        if not any(m['number'] == number for m in monitored):
            monitored.append({"number": number, "source": source})
            save_monitored_numbers(monitored)
            await query.edit_message_text(f"✅ Nomor `{number}` sekarang dimonitor. OTP akan otomatis dikirim.", parse_mode="Markdown")
        else:
            await query.answer("Nomor ini sudah dimonitor.", show_alert=True)
        return

    # Jika bukan monitor, berarti permintaan negara
    country_key = data.split("_")[1]
    country_info = TARGET_COUNTRIES[country_key]
    numbers = await scrape_numbers_by_country(country_key)
    if not numbers:
        return await query.edit_message_text(f"❌ Gak ada nomor untuk {country_info['flag']} {country_info['name']}.")

    sample = random.sample(numbers, min(5, len(numbers)))
    text = f"🎲 *5 Nomor {country_info['flag']} {country_info['name']}*\n\n"
    keyboard = []
    for n in sample:
        text += f"📞 `{n['number']}` — {n['source']}\n"
        # Tombol monitor per nomor
        keyboard.append([InlineKeyboardButton(f"🛰 Monitor {n['number']}", callback_data=f"monitor_{n['number']}_{n['source']}")])
    text += "\n_Klik tombol di bawah untuk mulai memonitor OTP dari nomor itu._"

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# -------------------- SMS FETCHER (iVasms) --------------------
async def fetch_ivasms(client, headers, csrf_token):
    all_msgs = []
    try:
        today = datetime.utcnow(); start = today - timedelta(days=1)
        fdate = start.strftime('%m/%d/%Y'); tdate = today.strftime('%m/%d/%Y')
        r1 = await client.post(SMS_API_ENDPOINT, headers=headers,
                               data={'from': fdate, 'to': tdate, '_token': csrf_token})
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        groups = soup1.find_all('div', class_='pointer')
        if not groups: return []
        group_ids = []
        for g in groups:
            m = re.search(r"getDetials\('(.+?)'\)", g.get('onclick',''))
            if m: group_ids.append(m.group(1))
        for gid in group_ids:
            r2 = await client.post(f"{BASE_URL}portal/sms/received/getsms/number",
                                   headers=headers,
                                   data={'start': fdate, 'end': tdate, 'range': gid, '_token': csrf_token})
            soup2 = BeautifulSoup(r2.text, 'html.parser')
            phones = [d.text.strip() for d in soup2.select("div[onclick*='getDetialsNumber']")]
            for phone in phones:
                r3 = await client.post(f"{BASE_URL}portal/sms/received/getsms/number/sms",
                                       headers=headers,
                                       data={'start': fdate, 'end': tdate, 'Number': phone, 'Range': gid, '_token': csrf_token})
                soup3 = BeautifulSoup(r3.text, 'html.parser')
                for card in soup3.find_all('div', class_='card-body'):
                    p = card.find('p', class_='mb-0')
                    if not p: continue
                    txt = p.get_text(separator='\n').strip()
                    country = gid.split('(')[0].strip() if '(' in gid else gid.strip()
                    service = "Unknown"
                    for svc, kws in SERVICE_KEYWORDS.items():
                        if any(k in txt.lower() for k in kws): service = svc; break
                    code = re.search(r'\b(\d{4,8})\b', txt)
                    code = code.group(1) if code else "N/A"
                    flag = COUNTRY_FLAGS.get(country, "🏴‍☠️")
                    uid = f"ivasms-{phone}-{hash(txt)}"
                    all_msgs.append({
                        "id": uid, "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "number": phone, "country": country, "flag": flag,
                        "service": service, "code": code, "full_sms": txt
                    })
        return all_msgs
    except Exception as e:
        print(f"❌ iVasms error: {e}")
        return []

async def send_msg(ctx, chat_id, msg):
    try:
        emoji = SERVICE_EMOJIS.get(msg['service'], "❓")
        text = (f"🔔 *OTP MASUK [{msg.get('source', 'iVasms')}]*\n\n"
                f"📞 *Nomor:* `{msg['number']}`\n"
                f"🔑 *Kode:* `{msg['code']}`\n"
                f"🏆 *Layanan:* {emoji} {msg['service']}\n"
                f"🌍 *Negara:* {msg['flag']} {msg['country']}\n"
                f"⏰ *Waktu:* `{msg['time']}`\n\n"
                f"💬 *Pesan:*\n```\n{msg['full_sms']}\n```")
        await ctx.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Exception as e: print(f"❌ Send error: {e}")

# -------------------- BACKGROUND JOBS --------------------
async def ivasms_job(ctx: ContextTypes.DEFAULT_TYPE):
    print(f"\n--- [{datetime.utcnow()}] iVasms Check ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Origin': 'https://www.ivasms.com',
        'Referer': 'https://www.ivasms.com/login'
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            login_page = await client.get(LOGIN_URL, headers=headers)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            token_input = soup.find('input', {'name': '_token'})
            login_data = {'email': USERNAME, 'password': PASSWORD}
            if token_input: login_data['_token'] = token_input['value']
            login_res = await client.post(LOGIN_URL, data=login_data, headers=headers)
            if "login" in str(login_res.url):
                print("❌ iVasms login gagal")
                return
            print("✅ iVasms login sukses")
            dash_soup = BeautifulSoup(login_res.text, 'html.parser')
            meta = dash_soup.find('meta', {'name': 'csrf-token'})
            if not meta: return
            csrf = meta.get('content')
            headers['Referer'] = str(login_res.url)
            messages = await fetch_ivasms(client, headers, csrf)
            if not messages:
                print("✔️ iVasms: gak ada SMS baru.")
                return
            processed = load_processed_ids()
            recipients = load_chat_ids()
            new_count = 0
            for msg in reversed(messages):
                if msg['id'] not in processed:
                    new_count += 1
                    print(f"✔️ iVasms SMS: {msg['number']} | {msg['service']}")
                    for cid in recipients:
                        await send_msg(ctx, cid, msg)
                    save_processed_id(msg['id'])
            if new_count: print(f"✅ iVasms: {new_count} SMS terkirim.")
        except Exception as e:
            print(f"❌ iVasms job error: {e}")

async def public_monitor_job(ctx: ContextTypes.DEFAULT_TYPE):
    monitored = load_monitored_numbers()
    if not monitored: return
    print(f"\n--- [{datetime.utcnow()}] Public Monitor ---")
    processed = load_processed_ids()
    recipients = load_chat_ids()
    for item in monitored:
        number = item['number']
        source = item['source']
        sms_list = await check_public_sms(number, source)
        for sms in sms_list:
            txt = sms['text']
            uid = f"pub-{number}-{hash(txt)}"
            if uid in processed: continue
            service = "Unknown"
            for svc, kws in SERVICE_KEYWORDS.items():
                if any(k in txt.lower() for k in kws): service = svc; break
            code = re.search(r'\b(\d{4,8})\b', txt)
            code = code.group(1) if code else "N/A"
            msg = {
                "id": uid, "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "number": number, "country": "Unknown", "flag": "🏴‍☠️",
                "service": service, "code": code, "full_sms": txt,
                "source": source
            }
            for cid in recipients:
                await send_msg(ctx, cid, msg)
            save_processed_id(uid)

# -------------------- MAIN --------------------
def main():
    print("🚀 dhekzEdan Multi-Source Bot Starting...")
    app = Application.builder().token(YOUR_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addchat", addchat))
    app.add_handler(CommandHandler("remchat", remchat))
    app.add_handler(CommandHandler("listchat", listchat))
    app.add_handler(CommandHandler("monitored", monitored))
    app.add_handler(CallbackQueryHandler(button_handler))
    # Jobs
    app.job_queue.run_repeating(ivasms_job, interval=POLLING_INTERVAL, first=5)
    app.job_queue.run_repeating(public_monitor_job, interval=30, first=10)  # cek nomor publik tiap 30 detik
    print("🔄 Bot online! iVasms + Public Monitor aktif.")
    app.run_polling()

if __name__ == "__main__":
    main()
