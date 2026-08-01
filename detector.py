import requests
import time

KICK_ACCESS_TOKEN = "MWI5ZDI4NDMTNDNJMI0ZY2FILTHHODUTMZRMZJQ5NTRIOGVK"
API_LOCAL_URL = "https://web-production-b7b73.up.railway.app/record-drop"

TELEGRAM_BOT_TOKEN = "8690067581:AAF04GBDtp7qa1Sb0GOjuim779qES_na-NE"
TELEGRAM_CHAT_ID = "-1004428214791"

CHECK_INTERVAL = 5
KEYWORD_FILTER = ['slot', 'casino', 'stake', 'bonus']

HEADERS = {
    "Authorization": f"Bearer {KICK_ACCESS_TOKEN}",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

seen_campaigns = set()

def is_slots_casino(camp):
    camp_name = camp.get("name") or ""
    category_info = camp.get("category") or {}
    cat_name = category_info.get("name") or ""
    cat_slug = category_info.get("slug") or ""
    combined_text = f"{camp_name} {cat_name} {cat_slug}".lower()
    return any(k in combined_text for k in KEYWORD_FILTER)

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def update_db_frequency(streamer_name, category):
    try:
        res = requests.post(API_LOCAL_URL, json={"streamer_name": streamer_name, "category": category}, timeout=5)
        if res.status_code == 200:
            print(f"  └── [DB UPDATED] Frekuensi drop {streamer_name} bertambah di Database!")
    except Exception as e:
        print(f"  └── [ERROR API] Gagal update DB: {e}")

def check_kick_drops():
    url = "https://web.kick.com/api/v1/drops/campaigns"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            campaigns = response.json().get("data", [])
            print(f"[{time.strftime('%H:%M:%S')}] Pindaian berhasil. Memeriksa {len(campaigns)} campaign...")
            
            for camp in campaigns:
                camp_id = str(camp.get("id"))
                if not is_slots_casino(camp): continue
                
                if camp_id not in seen_campaigns:
                    seen_campaigns.add(camp_id)
                    camp_name = camp.get("name", "")
                    
                    channels = camp.get("channels", [])
                    target_streamer = None
                    if channels:
                        live_ch = next((c for c in channels if c.get("is_live") or c.get("livestream")), None)
                        ch = live_ch if live_ch else channels[0]
                        target_streamer = ch.get("slug") or ch.get("username")
                    
                    if target_streamer:
                        print(f"\n[🎁 DROP TERDETEKSI] {camp_name} | Streamer: {target_streamer}")
                        update_db_frequency(target_streamer, "Slots")
                        send_telegram(
                            f"🎁 <b>Drop Slots Terdeteksi!</b>\n\n"
                            f"Campaign: <b>{camp_name}</b>\n"
                            f"Streamer: <b>{target_streamer}</b>\n"
                            f"Status: <i>Frekuensi streamer ini telah diperbarui di Database!</i>"
                        )
    except Exception as e:
        print(f"[ERROR] Gangguan koneksi: {e}")

if __name__ == "__main__":
    print("=== BOT DETECTOR & DATA HARVESTER DIMULAI ===")
    while True:
        check_kick_drops()
        time.sleep(CHECK_INTERVAL)