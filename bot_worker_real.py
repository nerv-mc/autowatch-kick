import asyncio
import requests
from pyppeteer import launch

# ==================== KONFIGURASI BOT ====================
BOT_ID = "Nayamul"
API_URL = f"http://127.0.0.1:8000/assign-streamer/{BOT_ID}"
HEARTBEAT_INTERVAL = 10

# Cookie Session Akun Kick
KICK_SESSION_TOKEN = "405249993%7COT6chS54Q7JWj3AB34BGvgS1F4f2RmRZ5XQVTr3O"
KICK_SESSION = "eyJpdiI6IlFSa3FpZUVNbjhWS3JZNks0NHlCMGc9PSIsInZhbHVlIjoiWDVIc2lYTENwaG1hZi9uQ29Yc0NBYjhsYXJQRVZlOW0yVEttaUhBY0NlYlk2RHFadEhpb3hVMjRKZzBYTnc1UkJqSHJyYU5hdXJseXJzL0JXYitkL2hQclZPQW91Z2VFMDRlb0dHdVpldUJWVlBJcGRLMEFNQ0Y3TXpoMjd1N2kiLCJtYWMiOiJiNzI0NTI2MWY5ZGI4YjFmMzI1YzQwODQ5M2RlODUzYzJiYWQ4ZmFiNzQwZTc1MDExM2YzNTg2M2Q4OThlODVmIiwidGFnIjoiIn0="
# =========================================================

async def run_real_bot():
    print(f"🚀 [START] Memulai Worker Kick Asli ({BOT_ID}) - Mode Silent...")

    # Headless = True (Browser berjalan di background tanpa buka jendela)
    browser = await launch(
        headless=True,
        executablePath=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--mute-audio',
            '--autoplay-policy=no-user-gesture-required'
        ],
        viewport={'width': 1280, 'height': 720}
    )

    pages = await browser.pages()
    page = pages[0] if len(pages) > 0 else await browser.newPage()

    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Inject Cookies
    await page.setCookie(
        {
            'name': 'session_token',
            'value': KICK_SESSION_TOKEN,
            'domain': '.kick.com',
            'path': '/',
            'secure': True
        },
        {
            'name': 'kick_session',
            'value': KICK_SESSION,
            'domain': '.kick.com',
            'path': '/',
            'secure': True
        }
    )
    print("🔐 Cookie Login berhasil dipasang.")

    current_streamer = ""

    while True:
        try:
            res = requests.get(API_URL, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                target_streamer = data.get("assigned_to", "hanvee")

                if target_streamer != current_streamer:
                    current_streamer = target_streamer
                    target_url = f"https://kick.com/{current_streamer}"
                    print(f"🔄 [{BOT_ID}] Membuka Streamer LIVE: {current_streamer}")
                    try:
                        await page.goto(target_url, {'waitUntil': 'domcontentloaded', 'timeout': 30000})
                    except Exception as goto_err:
                        print(f"⚠️ [{BOT_ID}] Warning navigasi ringan (diabaikan): {goto_err}")
                else:
                    print(f"🟢 [{BOT_ID}] Active Watching -> {current_streamer} | Status: OK")

        except Exception as e:
            print(f"❌ [{BOT_ID}] Error Heartbeat: {e}")

        await asyncio.sleep(HEARTBEAT_INTERVAL)

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_real_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot dihentikan oleh user.")