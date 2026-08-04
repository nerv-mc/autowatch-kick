import asyncio
import urllib.parse
import aiohttp
from pyppeteer import launch

# ================== PENGATURAN TELEGRAM & RAILWAY ==================
TELEGRAM_BOT_TOKEN = "8690067581:AAF04GBDtp7qa1Sb0GOjuim779qES_na-NE"
TELEGRAM_CHAT_ID = "-5447124497"

API_BASE_URL = "https://web-production-b7b73.up.railway.app"
HEARTBEAT_INTERVAL = 10
CLAIM_CHECK_INTERVAL = 60  # Cek inventory tiap 60 detik

active_bot_pages = {}
claimed_history = set()
released_history = set()
browser_instance = None

def handle_async_exception(loop, context):
    msg = context.get("exception")
    if msg and ("No session with given id" in str(msg) or "detachFromTarget" in str(msg)):
        return
    loop.default_exception_handler(context)

def clean_cookie_val(val: str) -> str:
    return urllib.parse.unquote(val)

# ================== DAFTAR 6 AKUN BOT RDP ==================
BOT_ACCOUNTS = [
    {
        "bot_id": "RestyFadilah12",
        "token": "403624318%7CQ3wReTBgDa1PKIsHHHuYwQFQkc2xuUVvsYAFFz2F",
        "session": "eyJpdiI6InYrc29yUktGWnYxdXBaWUUwQlFmMVE9PSIsInZhbHVlIjoiekErbDVxTmNqaFF1SHB2bFM1UGdoWlVQcVg4TXNYeVRTWkxYNG42ZmRmMzdBekNFYlRyeTFWVFowSTdSZHQwS1JVQXY3cUY1L3Yra1QwTVpWR0xDTWlleDVUMDA5UW4rT3hBOEZrYmtLcHRuRldON2lwbkRxWkpkVldYRHlHUVEiLCJtYWMiOiIxOWZiZWZjZmFkNDcwMzMzY2IwZDZmODhmYzk5ZGUxMThhN2U0NDIwNzBmZDJkY2RmN2UwODAyNWFhYWNkMjY5IiwidGFnIjoiIn0%3D"
    },
    {
        "bot_id": "Asnbumai",
        "token": "405240603%7CRZB2Wod212JfK9ZXrugWPd0iHr3rSRAfL1vdJ9Uw",
        "session": "eyJpdiI6IkE5SjVFam9TZFFNVHVqeENFSmFWUFE9PSIsInZhbHVlIjoicDZSdTBobGZqZTcwS09rYmVYQzhqUHc0dmF4YmxSeXZDYjZiZ3Y1RmgzSHBWbVBxczJQWHBoSnhnZlVNcHNHUmMyUzJUb09GM2E3eXBTTDZDWVBFOEZmOVlqTEw3WGRtTGhUWG8wdTBkQjVEc3NrbnQ1RzZWSXdlb1FoU2JzUzIiLCJtYWMiOiI6NThlMTdjZjIwZWIyNzJhNzI0N2M1NzMwMmJiMDhlMzY4MjdjZTQ0Y2VjNGMwMzFhMmNmMDI4YWM4OTk3NjI2IiwidGFnIjoiIn0%3D"
    },
    {
        "bot_id": "Inisaripudin",
        "token": "403575458%7CqWMGNsmBD0by7jSFMv5NmLuVEK6LGHWZcZLXDgEj",
        "session": "eyJpdiI6IjN0SGRQQXBEdWR0cllUd3BjN3ZMQ3c9PSIsInZhbHVlIjoiUHF2NHc2TVhSem9BbENwcWNtYVQ2QjVtajhmclpGa21HTHorOGVJM2NOZ3FIWmFHUHZiSkhvSWdWMlIwSEpFSkxUZ0xwVWZ4Z1FDRVBpK0pmY2l3QVRyRUNOY0dTTm02UnJ2V3l3OGFZWkFLUkwxNXVycnR6L3ZvYUF2NmIxTSsiLCJtYWMiOiI9MmI3OTk4NDA1MzE3MzI0ODQxMTBjMDVmMDZmNzcxNGZkZGFjMDU3NjIwZDI2OTJjMGJhZmE3YWFmNjY3NzRkIiwidGFnIjoiIn0%3D"
    },
    {
        "bot_id": "Suraptbegg",
        "token": "403572566%7CDcFLwq6f1z1snq26PdVoDBtQrbikh0FuPqKSsktk",
        "session": "eyJpdiI6Ijh1SjNUdzRnZENFQ01EZGlBWGdiNlE9PSIsInZhbHVlIjoiaDdsYW51MlhxYzhmakdHbzk5eS9zNVozZWE4Nk1mbzBtaTBockFoWmpuTW9HUGjnNW13Yk01V2VNcE9wU1JnVGhJZWhtSC9sRnNSZWhUa0ZaVjdxdkFWVWVRVWR5am1NSkljbW5Fdk9FQjd4WURMUkxkWERjTWxibUFsNWFWeFYiLCJtYWMiOiIyMjVkZjVlYjBiNzQzNTlhOWNlMjAxYTRlYjc0Yzg0MTdlZDViNzdhOWIwNWZhMGE4ZDI4NjdjODkyNTlhZmQ3IiwidGFnIjoiIn0%3D"
    },
    {
        "bot_id": "Distriyana",
        "token": "402993214%7CUIjd2FvohZY0yjDoHu505lbFNsDasA76X0gzM414",
        "session": "eyJpdiI6ImgvcmZsYWZweCtaS1FmVERUUzloQmc9PSIsInZhbHVlIjoiL2pFbDFjYnF2bnk0ZmxMa1Y8MVhEcGNibDkxdzZ5bjBiOUt4a1RFMWNKalBXV0pwMS9mbU5NSjE3ZU1teTlhUjF6SjBobE5VcVA0N2ptY0Vwb1oxbFJUL3V4TDJkeU9oRFNLdVloMzRJdXRLUm0xVnlUZ0tjNDlyRG5ZN1doSG4iLCJtYWMiOiI4ZWFhNDZjYmU1MDFjZmQ0NjczMmI4ZGE4YTdiMDBhZmU3MzlkZWIxMGE4ZTZiNmM0NDBjMTliY2ZjY2RlYWExIiwidGFnIjoiIn0%3D"
    },
    {
        "bot_id": "Widiastusi1219",
        "token": "402998622%7C9WWGaOkXV9xFvoJa8cRQPeLh0XZ4gbqpkbbQe08j",
        "session": "eyJpdiI6ImQwUjBzSVo1Kzc5VjNvS3pFcEZpN3c9PSIsInZhbHVlIjoibTRabW55YXVHYTFDVkFrVE1LOGJBd0krZGNKeDYwUmkvQzFqVlNhcUthMGFQNUJDTUpSbm52VVB4MzFiSnIzUG1xR2ZJSko1YjFvRUtzM2g2bFZOK1pJWEpETHRHYk93YlcvWEpURE9lb0tKVDFvMXBLS1B5WVErM2hZUnNISWUiLCJtYWMiOiIyZTcyYTJmODU3Nzk3YzQyZjQwNzg1YjlkNjY2ZGI4MTg4MjNjODhiNGE2MGNhMDIzZTA3YTM1MDMzNDJhZGI3IiwidGFnIjoiIn0%3D"
    }
]

# ================== HELPER TAB STREAMER ==================
async def create_streamer_page(browser, account_info: dict, streamer_name: str, http_session):
    page = await browser.newPage()
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    tok = clean_cookie_val(account_info.get("token", ""))
    sess = clean_cookie_val(account_info.get("session", ""))

    if tok and sess:
        await page.setCookie(
            {'name': 'session_token', 'value': tok, 'domain': '.kick.com', 'path': '/', 'secure': True},
            {'name': 'kick_session', 'value': sess, 'domain': '.kick.com', 'path': '/', 'secure': True}
        )

    try:
        await page.goto(f"https://kick.com/{streamer_name}", {'waitUntil': 'domcontentloaded', 'timeout': 30000})
        await asyncio.sleep(3)

        # Force Play Video Player
        await page.evaluate('''() => {
            const v = document.querySelector('video');
            if (v) { v.muted = false; v.play().catch(() => {}); }
        }''')
    except Exception:
        pass

    return page

# ================== INVENTORY AUTO CLAIMER ==================
async def check_and_execute_claim(browser, account_info: dict) -> list:
    """Membuka tab inventory, mencari tombol 'Klaim' / 'Claim' yang unlocked, lalu mengeklik tombol tersebut."""
    claim_page = None
    try:
        claim_page = await browser.newPage()
        await claim_page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        tok = clean_cookie_val(account_info.get("token", ""))
        sess = clean_cookie_val(account_info.get("session", ""))

        if tok and sess:
            await claim_page.setCookie(
                {'name': 'session_token', 'value': tok, 'domain': '.kick.com', 'path': '/', 'secure': True},
                {'name': 'kick_session', 'value': sess, 'domain': '.kick.com', 'path': '/', 'secure': True}
            )

        await claim_page.goto("https://kick.com/drops/inventory", {'waitUntil': 'networkidle2', 'timeout': 30000})
        await asyncio.sleep(4)

        # Tutup pop-up Daily Reward jika muncul
        await claim_page.evaluate('''() => {
            const dialogs = document.querySelectorAll('div[role="dialog"]');
            dialogs.forEach(d => {
                const closeBtn = d.querySelector('button');
                if (closeBtn) closeBtn.click();
            });
        }''')
        await asyncio.sleep(1)

        # Eksekusi Klik Claim
        claimed_items = await claim_page.evaluate('''() => {
            const successList = [];
            const elements = Array.from(document.querySelectorAll('button, a, [role="button"]'));

            for (const el of elements) {
                const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();

                if (aria.includes('daily reward') || text.includes('daily')) continue;

                const isClaimBtn = text === 'klaim' || text === 'claim' || aria.includes('klaim') || (aria.includes('claim') && !aria.includes('daily'));
                const isDisabled = el.disabled || el.getAttribute('aria-disabled') === 'true' || text.includes('claimed') || text.includes('diklaim');

                if (isClaimBtn && !isDisabled) {
                    try {
                        el.scrollIntoView();
                        el.click();
                        successList.push("claimed_item");
                    } catch (e) {}
                }
            }
            return successList;
        }''')

        await asyncio.sleep(2)
        return claimed_items

    except Exception:
        return []
    finally:
        if claim_page:
            try:
                await claim_page.close()
            except Exception:
                pass

# ================== BATCH CLAIMER (TIPE 2 EVENT) ==================
async def batch_inventory_claimer(browser, http_session):
    await asyncio.sleep(20)

    while True:
        for bot_id, info in list(active_bot_pages.items()):
            account_info = info["account_info"]
            active_tabs = info.get("streamers", {})

            claimed_cards = await check_and_execute_claim(browser, account_info)

            if claimed_cards:
                for streamer_name in list(active_tabs.keys()):
                    claim_key = f"{bot_id}_{streamer_name}"

                    if claim_key not in claimed_history:
                        claimed_history.add(claim_key)
                        print(f"🎉 [TIPE 2: BOT CLAIM SUCCESS] Bot {bot_id} BERHASIL KLAIM DROP {streamer_name}!")

                        # Kirim laporan ke Backend Railway (Memicu Notifikasi Tipe 2)
                        try:
                            await http_session.post(
                                f"{API_BASE_URL}/record-drop",
                                json={"bot_id": bot_id, "streamer": streamer_name},
                                timeout=aiohttp.ClientTimeout(total=5)
                            )
                        except Exception as e:
                            print(f"⚠️ Gagal lapor claim ke Railway: {e}")

        await asyncio.sleep(CLAIM_CHECK_INTERVAL)

# ================== WORKER BOT MAIN ==================
async def start_single_worker(account_info, browser, http_session):
    bot_id = account_info["bot_id"]
    api_url = f"{API_BASE_URL}/assign-streamer/{bot_id}"
    print(f"🚀 [WORKER START] Memulai Worker ({bot_id})...")

    active_bot_pages[bot_id] = {
        "streamers": {},
        "account_info": account_info
    }

    while True:
        try:
            async with http_session.get(api_url, timeout=aiohttp.ClientTimeout(total=20)) as res:
                if res.status == 200:
                    data = await res.json()
                    target_streamers = data.get("assigned_to", [])
                    if isinstance(target_streamers, str):
                        target_streamers = [target_streamers]

                    current_tabs = active_bot_pages[bot_id]["streamers"]
                    current_streamers_set = set(current_tabs.keys())
                    new_streamers_set = set(target_streamers)

                    # Close tab HANYA jika diperintahkan Backend (misal setelah Grace Period 10m habis)
                    to_remove = current_streamers_set - new_streamers_set
                    for s in to_remove:
                        print(f"❌ [{bot_id}] Closing Tab -> {s}")
                        try:
                            await current_tabs[s].close()
                        except Exception:
                            pass
                        del current_tabs[s]

                    # Open tab streamer baru
                    to_add = new_streamers_set - current_streamers_set
                    for s in to_add:
                        print(f"🔄 [{bot_id}] Opening New Tab -> {s}")
                        p = await create_streamer_page(browser, account_info, s, http_session)
                        current_tabs[s] = p

                    active_list = list(current_tabs.keys())
                    print(f"🟢 [{bot_id}] Watching ({len(active_list)} Streams) -> {', '.join(active_list)}")

        except Exception as e:
            print(f"❌ [{bot_id}] Error Worker: {e}")

        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def main():
    global browser_instance
    print(f"🔥 Membuka Master Browser untuk {len(BOT_ACCOUNTS)} Akun Bot...")

    browser_instance = await launch(
        headless=True,
        executablePath=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--mute-audio',
            '--autoplay-policy=no-user-gesture-required',
            '--ignore-certificate-errors',
            '--no-first-run'
        ],
        viewport={'width': 1280, 'height': 720}
    )

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as http_session:
        for acc in BOT_ACCOUNTS:
            asyncio.create_task(start_single_worker(acc, browser_instance, http_session))
            await asyncio.sleep(0.5)

        asyncio.create_task(batch_inventory_claimer(browser_instance, http_session))

        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(handle_async_exception)
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 [SHUTDOWN] Menghentikan bot...")
        if browser_instance:
            try:
                loop.run_until_complete(browser_instance.close())
            except Exception: pass