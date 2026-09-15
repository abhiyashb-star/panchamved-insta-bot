# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import random
import threading
import http.server
import requests

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from instagrapi import Client

Client.expose = lambda self: {}

SESSION_FILE = 'insta_session.json'
COMMENT_CACHE_FILE = 'replied_comments.json'
DM_CACHE_FILE = 'replied_dms.json'
MEDIA_ID = os.getenv('MEDIA_ID', '3983819681704241718')

import base64
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8762256150:AAGVBrN6YG7W9_FsqhRkelgMcBzD_kjWoTI')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '5707480311'))
GEMINI_KEY = os.getenv('GEMINI_KEY') or base64.b64decode('QVEuQWI4Uk42SVpKZEtrNUZNZU51MGM5YjVqaTBnc3JNNUl5aDI5dW1oTVd5cWd2dW8wMWc=').decode()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_KEY}"

BOT_STATS = {
    'status': 'initializing',
    'started_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
    'account': 'panchamvedproduction_',
    'target_reel': f'https://www.instagram.com/reel/DdJXuSxMOo2/',
    'comments_replied': 0,
    'dms_replied': 0,
    'last_active': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
}

COMMENT_REPLIES = [
    '🌸 Jai Shree Krishna @{username}! Maine aapko poore bhajan ka link DM me bhej diya hai, kripya check kijiye 🙏✨',
    '✨ Radhe Radhe @{username}! Aapke inbox me divya bhajan ka YouTube link bhej diya gaya hai 🙏🦚',
    '🙏 Pranam @{username}! Bhajan ka poora video link aapke DM me share kar diya hai, anand lijiye 🌸'
]

SYSTEM_PROMPT = """You are the AI Co-Founder and Executive Creative Director of 'Panchamved Production Studios' (पञ्चमवेद), partnering directly with Founder Abhishek Tiwari on Telegram.

Brand Identity & Context:
- Brand Name: Panchamved (पञ्चमवेद - The 5th Veda of Sacred Sound, Divine Music & Spiritual Media)
- Founder: Abhishek Tiwari
- Official Instagram: @panchamvedproduction_
- Official YouTube: @panchamvedproduction
- Website: panchamved-official-web (Devotional music streaming, services, lyrics vault, WhatsApp/Telegram booking)
- Flagship Projects:
  1. 'राधे के नयना' (The Divine Flute of Vrindavan in Raag Yaman, 432Hz, soothing prema-bhakti)
  2. 'काल के भी काल — महाकाल तांडव' (High-energy Vedic Psy-Trance, 138 BPM, Raag Bhairav, 528Hz)
- Official 3D/4D Logo: Sculpted 24K gold Sanskrit 5 rising from an open ancient Vedic Granth, crowned by a sacred Jyoti flame, encircled by celestial orbital rings and golden planetary spheres.

Your Personality & Instructions:
- You speak in respectful, warm, and inspiring Hindi/Hinglish (addressing Abhishek ji with respect, using 'राधे राधे / जय श्री कृष्ण / हर हर महादेव').
- You are a brilliant creative director, marketing strategist, Vedic scholar, and production mastermind.
- Provide direct, concise, high-impact answers. Format with clear bullet points and emojis. Help him write viral scripts, plan content, grow Instagram followers, and build the business.
"""

conversation_history = []
history_lock = threading.Lock()
cl_client = None

def load_cache(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_cache(filepath, cache_set):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(list(cache_set), f, indent=2)

def send_telegram_alert(text):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': ADMIN_CHAT_ID, 'text': text}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f'[!] Telegram alert error: {e}', flush=True)

def send_chat_action(chat_id, action="typing"):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"
        requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception:
        pass

def send_telegram_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        res_json = r.json()
        if not res_json.get('ok'):
            payload.pop('parse_mode', None)
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Send error: {e}", flush=True)

def call_gemini(user_msg):
    global conversation_history
    with history_lock:
        sanitized = []
        last_role = None
        for item in conversation_history:
            role = item.get("role")
            if role != last_role and role in ("user", "model"):
                sanitized.append(item)
                last_role = role
        conversation_history = sanitized

        conversation_history.append({"role": "user", "parts": [{"text": user_msg}]})
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
            if conversation_history and conversation_history[0].get("role") != "user":
                conversation_history = conversation_history[1:]

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": conversation_history,
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 1000
            }
        }

    try:
        res = requests.post(GEMINI_URL, json=payload, timeout=45)
        if res.status_code == 200:
            reply = res.json()['candidates'][0]['content']['parts'][0]['text']
            with history_lock:
                conversation_history.append({"role": "model", "parts": [{"text": reply}]})
            return reply
        else:
            print(f"[!] Gemini Error HTTP {res.status_code}: {res.text}", flush=True)
            with history_lock:
                if conversation_history and conversation_history[-1].get("role") == "user":
                    conversation_history.pop()
            return "माफ कीजियेगा अभिषेक जी, AI सर्वर से उत्तर प्राप्त करने में क्षणिक बाधा आई। कृपया दोबारा लिखें।"
    except Exception as e:
        print(f"[!] Gemini Exception: {e}", flush=True)
        with history_lock:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()
        return "माफ कीजियेगा अभिषेक जी, नेटवर्क टाइमआउट हुआ। कृपया एक बार फिर संदेश भेजें।"

def get_instagram_stats_text():
    global cl_client
    if not cl_client:
        return "⚠️ Instagram क्लाइंट अभी इनिशियलाइज़ हो रहा है..."
    try:
        info = cl_client.user_info_by_username("panchamvedproduction_")
        return (
            f"📊 *PANCHAMVED INSTAGRAM LIVE STATS*\n\n"
            f"🏷️ *Username:* `@{info.username}`\n"
            f"👥 *Followers:* {info.follower_count}\n"
            f"👣 *Following:* {info.following_count}\n"
            f"🎬 *Total Posts/Reels:* {info.media_count}\n"
            f"📝 *Bio:* {info.biography}\n\n"
            f"☁️ *Cloud Status:* 24/7 Running on Render"
        )
    except Exception as e:
        return f"⚠️ Instagram stats fetch error: {e}"

def generate_chat_reply(text, username):
    t = (text or '').lower().strip()
    if any(w in t for w in ['radhe', 'krishna', 'ram', 'hare', 'har har', 'mahadev', 'namaste', 'pranam', 'jai mata', 'hello', 'hi', 'hey']):
        return (
            f'🌸 राधे राधे @{username}! जय श्री कृष्ण! 🌸\n\n'
            'पंचमवेद (Panchamved) परिवार में आपका हार्दिक स्वागत है 🙏\n'
            'प्रभु श्री राधा-कृष्ण की कृपा आप और आपके परिवार पर सदा बनी रहे।\n\n'
            'हमारे नए भक्ति भजनों को सुनने के लिए यूट्यूब चैनल पर जरूर पधारें:\n'
            '🔗 https://youtube.com/@panchamvedproduction ✨'
        )

    if any(w in t for w in ['sundar', 'achha', 'acha', 'badhiya', 'nice', 'super', 'superb', 'great', 'peace', 'shanti', 'anand', 'prem', 'khoob', 'pyara']):
        return (
            f'🙏 बहुत-बहुत आभार @{username}! यह सब ठाकुर जी और राधा रानी की कृपा है।\n\n'
            'अगर आपको यह भजन अच्छा लगा तो अपनों के साथ भी जरूर साझा करें। हमारे आने वाले नए भजनों के लिए चैनल सब्सक्राइब अवश्य करें:\n'
            '🔗 https://youtube.com/@panchamvedproduction 🌸✨\n'
            'राधे राधे!'
        )

    if any(w in t for w in ['link', 'song', 'bhajan', 'audio', 'video', 'yt', 'youtube', 'full', 'track']):
        return (
            f'🦚 जय श्री कृष्ण @{username}!\n\n'
            'दिव्य भजन का संपूर्ण वीडियो व ऑडियो आप हमारे ऑफिशियल यूट्यूब चैनल पर सुन सकते हैं:\n'
            '🔗 https://youtube.com/@panchamvedproduction\n\n'
            'चैनल को सब्सक्राइब करके बेल आइकन जरूर दबाएं ताकि कोई भी नया भजन न छूटे 🙏✨'
        )

    if any(w in t for w in ['collab', 'contact', 'number', 'shoot', 'details', 'kaha se', 'kaun ho', 'about', 'singer']):
        return (
            '🙏 पंचमवेद प्रोडक्शन (Panchamved Production) सनातन संस्कृति, भक्ति संगीत और उच्च गुणवत्ता वाले भजनों का निर्माण करता है।\n\n'
            'किसी भी सहयोग (Collaboration), भक्ति गीत निर्माण या पूछताछ के लिए कृपया अपना संपर्क विवरण या ईमेल यहां छोड़ें, हमारी टीम आपसे शीघ्र संपर्क करेगी ✨\n'
            'राधे राधे!'
        )

    if any(w in t for w in ['thank', 'dhanyawad', 'shukriya', 'ok', 'thk', 'theek']):
        return '🌸 सदैव स्वागत है! प्रभु की भक्ति में लीन रहें और आनंदित रहें। राधे राधे! 🙏🦚'

    return (
        f'🌸 जय श्री कृष्ण @{username}! राधे राधे! 🌸\n\n'
        'आपके संदेश के लिए धन्यवाद। अगर आपका कोई सुझाव या प्रश्न है तो अवश्य बताएं।\n'
        'हमारे नए भक्ति भजनों का आनंद लेने के लिए यूट्यूब पर जुड़ें:\n'
        '🔗 https://youtube.com/@panchamvedproduction 🙏✨'
    )

def handle_admin_telegram_message(text):
    text_clean = text.strip()
    print(f"\n[📩 RECEIVED FROM ABHISHEK ON TELEGRAM]: {text_clean}", flush=True)

    send_chat_action(ADMIN_CHAT_ID, "typing")

    if text_clean.lower() == "/stats":
        send_telegram_msg(ADMIN_CHAT_ID, "⏳ इंस्टाग्राम से लाइव आंकड़े फेच हो रहे हैं...")
        stats_reply = get_instagram_stats_text()
        send_telegram_msg(ADMIN_CHAT_ID, stats_reply)
        return

    if text_clean.lower() == "/clear":
        global conversation_history
        with history_lock:
            conversation_history = []
        send_telegram_msg(ADMIN_CHAT_ID, "🧹 बातचीत की मेमोरी रीसेट कर दी गई है! नए सिरे से शुरुआत करते हैं। राधे राधे! 🙏")
        return

    ai_reply = call_gemini(text_clean)
    print(f"[🤖 AI REPLY SENT TO ABHISHEK]: {ai_reply[:80]}...", flush=True)
    send_telegram_msg(ADMIN_CHAT_ID, ai_reply)

def run_telegram_ai_listener():
    print('=' * 60)
    print('✨ 24/7 TELEGRAM AI CO-FOUNDER ACTIVE ON CLOUD ✨', flush=True)
    print('=' * 60, flush=True)

    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            resp = requests.get(url, params=params, timeout=25)
            data = resp.json()

            if data.get("ok"):
                for item in data.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message")
                    if not msg:
                        continue

                    sender_id = msg.get("from", {}).get("id")
                    sender_name = msg.get("from", {}).get("first_name", "Devotee")
                    text = msg.get("text", "").strip()

                    if sender_id != ADMIN_CHAT_ID:
                        send_telegram_msg(
                            sender_id,
                            f"🌸 जय श्री कृष्ण {sender_name}! पंचमवेद परिवार में आपका स्वागत है। हमारे नए भक्ति भजनों को सुनने के लिए यूट्यूब चैनल पर जरूर पधारें:\n🔗 https://youtube.com/@panchamvedproduction 🙏✨"
                        )
                        continue

                    t = threading.Thread(target=handle_admin_telegram_message, args=(text,))
                    t.start()

        except Exception as e:
            print(f"[!] Telegram polling error: {e}", flush=True)
            time.sleep(3)

def run_instagram_bot():
    global cl_client
    print('=' * 60)
    print('✨ CLOUD WORKER: PANCHAMVED INSTAGRAM BOT ACTIVE ✨')
    print('=' * 60, flush=True)

    cl = Client()
    cl.delay_range = [2, 4]
    
    if not os.path.exists(SESSION_FILE):
        print(f'[!] Critical: {SESSION_FILE} missing!', flush=True)
        BOT_STATS['status'] = 'error: session file missing'
        return

    try:
        cl.load_settings(SESSION_FILE)
        cl.login('panchamvedproduction_', 'abhishek8080')
        my_user_id = str(cl.user_id)
        cl_client = cl
        BOT_STATS['status'] = 'running_healthy'
        print(f'[+] Cloud worker logged in as @panchamvedproduction_ ({my_user_id})!', flush=True)
    except Exception as e:
        print(f'[!] Cloud login error: {e}', flush=True)
        BOT_STATS['status'] = f'error: {e}'
        return

    replied_comments = load_cache(COMMENT_CACHE_FILE)
    replied_dms = load_cache(DM_CACHE_FILE)

    if not os.path.exists(DM_CACHE_FILE):
        try:
            initial_threads = cl.direct_threads(amount=15)
            for t in initial_threads:
                if t.messages:
                    replied_dms.add(str(t.messages[0].id))
            save_cache(DM_CACHE_FILE, replied_dms)
        except Exception:
            pass

    while True:
        try:
            BOT_STATS['last_active'] = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            
            # 1. Check Reel Comments
            try:
                comments = cl.media_comments(MEDIA_ID, amount=50)
                for c in comments:
                    cid = str(c.pk)
                    username = c.user.username
                    comment_text = c.text.strip()

                    if username.lower() == 'panchamvedproduction_':
                        continue

                    if cid not in replied_comments:
                        print(f'\n[🔔 REEL COMMENT] From @{username}: {comment_text}', flush=True)
                        public_reply = random.choice(COMMENT_REPLIES).format(username=username)
                        try:
                            cl.media_comment(MEDIA_ID, public_reply, replied_to_comment_id=int(c.pk))
                        except Exception as ce:
                            print(f'  [!] Comment reply: {ce}', flush=True)

                        time.sleep(random.randint(2, 4))

                        dm_text = (
                            f'🌸 जय श्री कृष्ण @{username}! राधे राधे! 🌸\n\n'
                            'हमारे भक्ति भजन से जुड़ने के लिए आपका हार्दिक आभार।\n\n'
                            'आनंदमय और दिव्य पूर्ण भजन सुनने के लिए नीचे दिए गए लिंक पर क्लिक करें:\n'
                            '🔗 https://youtube.com/@panchamvedproduction\n\n'
                            'पंचमवेद (Panchamved) परिवार से जुड़े रहने के लिए चैनल को सब्सक्राइब अवश्य करें 🙏✨\n'
                            'राधे राधे!'
                        )
                        try:
                            cl.direct_send(dm_text, user_ids=[int(c.user.pk)])
                            BOT_STATS['comments_replied'] += 1
                            send_telegram_alert(f"🔔 NEW INSTAGRAM REEL COMMENT!\n\nUser: @{username}\nComment: '{comment_text}'\nAction: Public reply sent + YouTube link DM delivered! ✨")
                        except Exception as de:
                            print(f'  [!] DM: {de}', flush=True)

                        replied_comments.add(cid)
                        save_cache(COMMENT_CACHE_FILE, replied_comments)
            except Exception:
                pass

            # 2. Check DM Inbox Chats
            try:
                threads = cl.direct_threads(amount=10)
                for t in threads:
                    if not t.messages:
                        continue
                    last_msg = t.messages[0]
                    msg_id = str(last_msg.id)
                    msg_sender_id = str(last_msg.user_id)
                    msg_text = (last_msg.text or '').strip()

                    if msg_sender_id != my_user_id and msg_id not in replied_dms:
                        sender_username = 'Bhakt'
                        for u in t.users:
                            if str(u.pk) == msg_sender_id:
                                sender_username = u.username
                                break
                        if sender_username == 'Bhakt' and t.users:
                            sender_username = t.users[0].username

                        print(f'\n[💬 DM CHAT] From @{sender_username}: {msg_text}', flush=True)
                        reply_text = generate_chat_reply(msg_text, sender_username)
                        time.sleep(random.randint(2, 4))

                        try:
                            cl.direct_answer(int(t.id), reply_text)
                            BOT_STATS['dms_replied'] += 1
                            send_telegram_alert(f"💬 NEW INSTAGRAM INBOX DM!\n\nUser: @{sender_username}\nMessage: '{msg_text}'\n\n🤖 Bot Replied:\n'{reply_text[:120]}...' ✨")
                        except Exception as ae:
                            print(f'  [!] Direct answer error: {ae}', flush=True)

                        replied_dms.add(msg_id)
                        save_cache(DM_CACHE_FILE, replied_dms)
            except Exception:
                pass

            time.sleep(15)

        except Exception as ex:
            print(f'[!] Cloud loop error: {ex}', flush=True)
            time.sleep(20)

def run_self_pinger():
    while True:
        time.sleep(600)
        url = os.getenv('RENDER_EXTERNAL_URL')
        if url:
            try:
                requests.get(f'{url}/health', timeout=10)
            except Exception:
                pass

class WebHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        resp = json.dumps(BOT_STATS, indent=2)
        self.wfile.write(resp.encode('utf-8'))

    def log_message(self, format, *args):
        pass

def main():
    port = int(os.getenv('PORT', 10000))
    print(f'[*] Starting HTTP Server on port {port}...', flush=True)

    # 1. Start Instagram Bot Worker
    t_bot = threading.Thread(target=run_instagram_bot, daemon=True)
    t_bot.start()

    # 2. Start Telegram AI Co-Founder Listener
    t_tg = threading.Thread(target=run_telegram_ai_listener, daemon=True)
    t_tg.start()

    # 3. Start Keep-Alive Pinger
    t_ping = threading.Thread(target=run_self_pinger, daemon=True)
    t_ping.start()

    # 4. Start HTTP Server
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), WebHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()
