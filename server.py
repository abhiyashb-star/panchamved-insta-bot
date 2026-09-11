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

def run_instagram_bot():
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
                        except Exception as de:
                            print(f'  [!] DM: {de}', flush=True)

                        replied_comments.add(cid)
                        save_cache(COMMENT_CACHE_FILE, replied_comments)
            except Exception as e:
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
                        except Exception as ae:
                            print(f'  [!] Direct answer error: {ae}', flush=True)

                        replied_dms.add(msg_id)
                        save_cache(DM_CACHE_FILE, replied_dms)
            except Exception as e:
                pass

            time.sleep(12)

        except Exception as ex:
            print(f'[!] Cloud loop error: {ex}', flush=True)
            time.sleep(20)

def run_self_pinger():
    while True:
        time.sleep(600)  # Ping every 10 minutes to prevent Render free instance spin-down
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

    # Start bot background worker
    t_bot = threading.Thread(target=run_instagram_bot, daemon=True)
    t_bot.start()

    # Start keep-alive pinger
    t_ping = threading.Thread(target=run_self_pinger, daemon=True)
    t_ping.start()

    # Start HTTP server
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), WebHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()
