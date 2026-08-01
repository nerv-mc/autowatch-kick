import sqlite3
import requests
import time
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Set
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kick Bot - Real-Time Drop Monitor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "drops.db"
WIB_TZ = ZoneInfo("Asia/Jakarta")

TELEGRAM_BOT_TOKEN = "8690067581:AAF04GBDtp7qa1Sb0GOjuim779qES_na-NE"
TELEGRAM_CHAT_ID = "-5447124497"

def send_telegram_sync(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Gagal kirim Telegram: {e}")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT,
            streamer TEXT,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

KICK_ACCESS_TOKEN = "YJJHNZY3NJETNMU5MS0ZNDUXLWI3NDUTMZQZNDFMYJFLMZVI"
CATEGORY_ID = 28
LIMIT_LIVE = 1000  # Ambil seluruh streamer live di Slots & Casino
MAX_STREAMS_PER_BOT = 3

bot_assignments: Dict[str, dict] = {}
daily_blacklisted_streamers: Dict[str, Set[str]] = {}
blacklisted_pending_until: Dict[str, float] = {}
seen_campaign_ids: Set[str] = set()

ALL_REGISTERED_BOTS = [
    "RestyFadilah12", "Asnbumai", "Inisaripudin", 
    "Suraptbegg", "Distriyana", "Widiastusi1219"
]

KEYWORD_FILTER = ['slot', 'casino', 'stake', 'bonus']

def get_today_wib_str() -> str:
    return datetime.now(WIB_TZ).strftime("%Y-%m-%d")

def add_to_daily_blacklist_with_delay(streamer: str, delay_minutes: int = 10):
    s_lower = streamer.lower()
    unlock_time = time.time() + (delay_minutes * 60)
    blacklisted_pending_until[s_lower] = unlock_time

def is_blacklisted_today(streamer: str) -> bool:
    s_lower = streamer.lower()
    today = get_today_wib_str()

    if s_lower in daily_blacklisted_streamers.get(today, set()):
        return True

    if s_lower in blacklisted_pending_until:
        unlock_time = blacklisted_pending_until[s_lower]
        if time.time() >= unlock_time:
            if today not in daily_blacklisted_streamers:
                daily_blacklisted_streamers[today] = set()
            daily_blacklisted_streamers[today].add(s_lower)
            del blacklisted_pending_until[s_lower]
            return True
        else:
            return False

    return False

# ================== ASYNC BACKGROUND DETECTOR ==================
def is_slots_casino_campaign(camp: dict) -> bool:
    name = camp.get('name', '')
    cat_obj = camp.get('category', {})
    cat_name = cat_obj.get('name', '') if isinstance(cat_obj, dict) else ''
    cat_slug = cat_obj.get('slug', '') if isinstance(cat_obj, dict) else ''
    text = f"{name} {cat_name} {cat_slug}".lower()
    return any(k in text for k in KEYWORD_FILTER)

async def async_campaign_checker_loop():
    while True:
        try:
            url = "https://web.kick.com/api/v1/drops/campaigns"
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                campaigns = res.json().get("data", [])
                for camp in campaigns:
                    camp_id = str(camp.get("id"))
                    if camp_id in seen_campaign_ids:
                        continue

                    if not is_slots_casino_campaign(camp):
                        continue

                    seen_campaign_ids.add(camp_id)

                    channels = camp.get("channels", [])
                    target_streamer = None
                    if channels:
                        live_ch = next((c for c in channels if c.get("is_live") or c.get("livestream")), None)
                        ch = live_ch or channels[0]
                        target_streamer = ch.get("slug") or ch.get("username") or (ch.get("user", {}).get("username") if isinstance(ch.get("user"), dict) else None)

                    if target_streamer:
                        s_lower = target_streamer.lower()
                        camp_name = camp.get("name", "Slots Drop")

                        add_to_daily_blacklist_with_delay(s_lower, delay_minutes=10)

                        msg_t1 = (
                            f"🚨 <b>[TIPE 1: DROP RELEASED REAL-TIME!]</b>\n\n"
                            f"🎁 <b>{camp_name}</b>\n"
                            f"👤 Streamer: <b>{s_lower}</b>\n"
                            f"⚡ Status: <b>Drop terdeteksi di API Kick!</b>\n"
                            f"🔗 <a href='https://kick.com/{s_lower}'>Buka Stream {s_lower}</a>\n\n"
                            f"⏳ Grace period 10 menit diaktifkan."
                        )
                        send_telegram_sync(msg_t1)

                        now_wib = datetime.now(WIB_TZ).strftime("%H:%M:%S WIB")
                        msg_t3 = (
                            f"📊 <b>[TIPE 3: DASHBOARD UPDATED!]</b>\n\n"
                            f"🖥️ Server mengunci target <b>{s_lower}</b>.\n"
                            f"🕒 Waktu Update: {now_wib}\n"
                            f"⚠️ Streamer akan masuk Blacklist Harian dalam 10 Menit."
                        )
                        send_telegram_sync(msg_t3)

        except Exception as e:
            pass

        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(async_campaign_checker_loop())

def get_top_drops_counts() -> Dict[str, int]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT streamer, COUNT(*) as total FROM drops GROUP BY streamer ORDER BY total DESC")
    rows = cursor.fetchall()
    conn.close()
    return {row[0].lower(): row[1] for row in rows}

def fetch_kick_live_slots_v2() -> List[dict]:
    url = f"https://api.kick.com/public/v2/livestreams?category_id={CATEGORY_ID}&limit={LIMIT_LIVE}"
    headers = {
        "Authorization": f"Bearer {KICK_ACCESS_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    top_drops_db = get_top_drops_counts()

    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            json_data = res.json()
            data_list = json_data.get("data", [])
            live_list = []

            for item in data_list:
                channel_obj = item.get("channel", {})
                broadcaster = item.get("broadcaster_user", {})
                slug = channel_obj.get("slug") or broadcaster.get("username") or "unknown"
                slug = slug.lower()

                raw_viewers = item.get("viewer_count") or 0
                drop_score = top_drops_db.get(slug, 0)
                sort_val = (drop_score * 1000000) + raw_viewers

                live_list.append({
                    "slug": slug,
                    "title": item.get("title") or "-",
                    "viewers_display": f"{raw_viewers:,} Viewers",
                    "raw_viewers": raw_viewers,
                    "sort_value": sort_val,
                    "drop_count": drop_score,
                    "language": item.get("language_code") or "EN"
                })

            live_list.sort(key=lambda x: x["sort_value"], reverse=True)
            return live_list

    except Exception as e:
        print(f"⚠️ Error Kick API v2: {e}")

    return []

def assign_stable_targets_for_bot(bot_id: str, live_streamers: List[dict]) -> List[str]:
    current_assigned = bot_assignments.get(bot_id, {}).get("targets", [])
    live_slugs_set = {s["slug"] for s in live_streamers}

    kept_targets = [
        s for s in current_assigned 
        if s in live_slugs_set and not is_blacklisted_today(s)
    ]

    needed = MAX_STREAMS_PER_BOT - len(kept_targets)
    if needed > 0:
        used_by_others = set()
        for b_id, b_data in bot_assignments.items():
            if b_id != bot_id:
                used_by_others.update(b_data.get("targets", []))

        for item in live_streamers:
            slug = item["slug"]
            if slug not in kept_targets and slug not in used_by_others and not is_blacklisted_today(slug):
                kept_targets.append(slug)
                needed -= 1
                if needed == 0:
                    break

    return kept_targets

@app.get("/")
def read_root():
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/assign-streamer/{bot_id}")
def assign_streamer(bot_id: str):
    live_data = fetch_kick_live_slots_v2()
    now_ts = time.time()
    
    if bot_id not in bot_assignments:
        targets = assign_stable_targets_for_bot(bot_id, live_data)
        bot_assignments[bot_id] = {
            "mode": "AUTO",
            "targets": targets,
            "last_seen": now_ts,
            "start_times": {t: now_ts for t in targets}
        }
    else:
        bot_assignments[bot_id]["last_seen"] = now_ts
        if bot_assignments[bot_id].get("mode") == "AUTO":
            new_targets = assign_stable_targets_for_bot(bot_id, live_data)
            bot_assignments[bot_id]["targets"] = new_targets
            if "start_times" not in bot_assignments[bot_id]:
                bot_assignments[bot_id]["start_times"] = {}
            for t in new_targets:
                if t not in bot_assignments[bot_id]["start_times"]:
                    bot_assignments[bot_id]["start_times"][t] = now_ts

    return {
        "bot_id": bot_id,
        "mode": bot_assignments[bot_id].get("mode", "AUTO"),
        "assigned_to": bot_assignments[bot_id].get("targets", [])
    }

@app.post("/record-drop")
def record_drop(payload: dict):
    bot_id = payload.get("bot_id")
    streamer = payload.get("streamer")
    if bot_id and streamer:
        s_lower = streamer.lower()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO drops (bot_id, streamer) VALUES (?, ?)", (bot_id, s_lower))
        conn.commit()
        conn.close()

        msg_t2 = (
            f"🎉 <b>[TIPE 2: BOT CLAIM SUCCESS!]</b>\n\n"
            f"🤖 Bot ID: <code>{bot_id}</code>\n"
            f"📺 Streamer Target: <b>{s_lower}</b>\n"
            f"✅ Status: <b>BERHASIL KLIK KLAIM & MASUK INVENTORY!</b>"
        )
        send_telegram_sync(msg_t2)

        return {"status": "success", "message": f"Drop claimed by {bot_id}"}
    return {"status": "error", "message": "Invalid payload"}

@app.get("/api/kill-streamer-bot")
def kill_streamer_bot(bot_id: str, streamer: str, ref: str = "bot-manager"):
    if bot_id in bot_assignments:
        targets = bot_assignments[bot_id].get("targets", [])
        if streamer in targets:
            targets.remove(streamer)
        
        bot_assignments[bot_id]["mode"] = "MANUAL"
        bot_assignments[bot_id]["targets"] = targets
        if streamer in bot_assignments[bot_id].get("start_times", {}):
            del bot_assignments[bot_id]["start_times"][streamer]
            
    return RedirectResponse(url=f"/{ref}", status_code=303)

@app.get("/api/set-bot-streamer")
def set_bot_streamer(bot_id: str, streamer: str, ref: str = "bot-manager"):
    streamer = streamer.strip().lower()
    now_ts = time.time()
    if bot_id in bot_assignments and streamer:
        targets = bot_assignments[bot_id].get("targets", [])
        if streamer not in targets and len(targets) < MAX_STREAMS_PER_BOT:
            targets.append(streamer)
            bot_assignments[bot_id]["mode"] = "MANUAL"
            bot_assignments[bot_id]["targets"] = targets
            if "start_times" not in bot_assignments[bot_id]:
                bot_assignments[bot_id]["start_times"] = {}
            bot_assignments[bot_id]["start_times"][streamer] = now_ts
    return RedirectResponse(url=f"/{ref}", status_code=303)

@app.get("/api/reset-bot-auto")
def reset_bot_auto(bot_id: str, ref: str = "bot-manager"):
    if bot_id in bot_assignments:
        bot_assignments[bot_id]["mode"] = "AUTO"
    return RedirectResponse(url=f"/{ref}", status_code=303)

GLOBAL_CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0c10; color: #a9b7c6; padding: 24px; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
    .header-title { display: flex; align-items: center; gap: 12px; }
    .header-title h1 { font-size: 20px; font-weight: 800; color: #ffffff; }
    .header-subtitle { font-size: 11px; color: #5c6b73; margin-top: 2px; }
    .header-subtitle span { color: #00e676; font-weight: 600; }
    .btn-panel { background: #6366f1; color: #ffffff; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 12px; text-decoration: none; }
    .players-badge { background: #1f2430; border: 1px solid #2d3446; color: #a9b7c6; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; margin-left: 10px; }
    .stats-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-box { background: #131722; border: 1px solid #1e2433; border-radius: 10px; padding: 20px; }
    .stat-box .title { font-size: 11px; font-weight: 700; color: #5c6b73; text-transform: uppercase; margin-bottom: 12px; }
    .stat-box .val { font-size: 34px; font-weight: 800; color: #ffffff; margin-bottom: 10px; }
    .stat-box .val.active { color: #00e676; }
    .stat-box .val.danger { color: #ff4d4f; }
    .stat-box .link { font-size: 12px; color: #6366f1; text-decoration: none; font-weight: 600; }
    .dashboard-layout { display: grid; grid-template-columns: 2.3fr 1fr; gap: 24px; }
    .panel-card { background: #131722; border: 1px solid #1e2433; border-radius: 12px; padding: 24px; }
    .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .panel-header h2 { font-size: 14px; font-weight: 800; color: #ffffff; text-transform: uppercase; }
    .stream-list { display: flex; flex-direction: column; gap: 10px; }
    .stream-item { background: #181c28; border: 1px solid #222838; border-radius: 8px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; }
    .stream-left { display: flex; align-items: center; gap: 14px; }
    .stream-rank { font-size: 12px; font-weight: 700; color: #5c6b73; width: 24px; }
    .stream-name { font-size: 14px; font-weight: 700; color: #ffffff; }
    .stream-title { font-size: 11px; color: #788596; margin-top: 3px; max-width: 480px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .viewers-count { font-size: 13px; font-weight: 700; color: #00e676; }
    .priority-tag { background: #1e293b; color: #6366f1; border: 1px solid #334155; font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 5px; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    .btn-back { background: #1f2430; color: #ffffff; border: 1px solid #2d3446; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 12px; text-decoration: none; }
    select, input { background: #181c28; border: 1px solid #222838; color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 12px; }
    select:focus, input:focus { outline: 1px solid #00e676; }
</style>
"""

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    live_streamers = fetch_kick_live_slots_v2()
    now_ts = time.time()
    now_wib = datetime.now(WIB_TZ).strftime("%H:%M:%S WIB")

    total_bots = len(ALL_REGISTERED_BOTS)
    active_bots_count = sum(1 for b in bot_assignments.values() if b.get("targets"))
    active_streams_count = sum(len(b.get("targets", [])) for b in bot_assignments.values())
    idle_bots_count = total_bots - active_bots_count

    top_drops_map = get_top_drops_counts()
    sidebar_drops_rows = ""
    if top_drops_map:
        for idx, (s_name, count) in enumerate(top_drops_map.items(), 1):
            sidebar_drops_rows += f"""
            <div style="display:flex; justify-content:space-between; align-items:center; background:#181c28; border:1px solid #222838; padding:10px 14px; border-radius:6px; margin-bottom:8px;">
                <span style="font-size:13px; font-weight:700; color:#fff;">#{idx} {s_name}</span>
                <span style="font-size:12px; font-weight:700; color:#00e676;">{count} Drops</span>
            </div>
            """
    else:
        sidebar_drops_rows = '<div style="font-size:12px; color:#5c6b73; font-style:italic;">Belum ada histori drop tercatat.</div>'

    ranking_cards = ""
    for idx, item in enumerate(live_streamers[:15], 1):
        s_slug = item['slug']
        is_bl = is_blacklisted_today(s_slug)
        is_pending = s_slug in blacklisted_pending_until

        status_badge = '<span class="priority-tag">🎁 Priority Drops</span>'
        if is_bl:
            status_badge = '<span style="background:#3f1721; color:#ff4d4f; border:1px solid #ff4d4f44; font-size:10px; font-weight:700; padding:4px 8px; border-radius:5px;">🚫 Blacklisted Today</span>'
        elif is_pending:
            rem_sec = int(blacklisted_pending_until[s_slug] - now_ts)
            status_badge = f'<span style="background:#3d3215; color:#ffc107; border:1px solid #ffc10744; font-size:10px; font-weight:700; padding:4px 8px; border-radius:5px;">⏳ Grace {rem_sec//60}m {rem_sec%60}s</span>'

        ranking_cards += f"""
        <div class="stream-item">
            <div class="stream-left">
                <div class="stream-rank">#{idx}</div>
                <div style="width:8px; height:8px; background:#00e676; border-radius:50%;"></div>
                <div>
                    <div class="stream-name">{s_slug} <span style="font-size:10px; color:#5c6b73;">[{item['language'].upper()}]</span></div>
                    <div class="stream-title">{item['title']}</div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                <div class="viewers-count">{item['viewers_display']}</div>
                {status_badge}
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Kick Bot - Live Tracker</title><meta http-equiv="refresh" content="10">{GLOBAL_CSS}</head>
    <body>
        <div class="header-bar">
            <div class="header-title">
                <div style="font-size:24px;">🎮</div>
                <div>
                    <h1>Kick Bot - Live Tracker</h1>
                    <div class="header-subtitle">Official Kick API v2 | Jam Lokal: <span>{now_wib}</span></div>
                </div>
            </div>
            <div>
                <a href="/bot-manager" class="btn-panel">⚙️ Buka Panel Manajemen Bot →</a>
                <div class="players-badge">🤖 Players: <strong>{total_bots}</strong></div>
            </div>
        </div>

        <div class="stats-container">
            <div class="stat-box">
                <div class="title">TOTAL PLAYERS (BOT)</div>
                <div class="val">{total_bots}</div>
                <a href="/bot-manager" class="link">Kelola Semua Bot →</a>
            </div>
            <div class="stat-box">
                <div class="title">STATUS ACTIVE STREAMS</div>
                <div class="val active">{active_streams_count}</div>
                <a href="/bot-manager" class="link">Kelola Bot Aktif →</a>
            </div>
            <div class="stat-box">
                <div class="title">STANDBY / IDLE BOTS</div>
                <div class="val">{idle_bots_count}</div>
                <a href="/bot-manager" class="link">Kelola Bot Standby →</a>
            </div>
            <div class="stat-box">
                <div class="title">STATUS STUCK / OFFLINE</div>
                <div class="val danger">{total_bots - active_bots_count}</div>
                <a href="/bot-manager" class="link">Lihat Bot Stuck →</a>
            </div>
        </div>

        <div class="dashboard-layout">
            <div class="panel-card">
                <div class="panel-header">
                    <h2>🔥 CATEGORY SLOTS LIVE RANKING (TOP 15 REAL-TIME)</h2>
                    <div style="font-size:11px; color:#5c6b73;">Kick API v2 Total Live: <strong>{len(live_streamers)} Streamers</strong></div>
                </div>
                <div class="stream-list">{ranking_cards}</div>
            </div>

            <div class="panel-card">
                <div class="panel-header"><h2>🏆 TOP DROPS STREAMER</h2></div>
                <div style="font-size:11px; color:#5c6b73; margin-bottom:16px;">Streamer dengan histori penerimaan drop terbanyak yang menjadi prioritas utama bot.</div>
                <div>{sidebar_drops_rows}</div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/bot-manager", response_class=HTMLResponse)
def get_bot_manager_page():
    live_streamers = fetch_kick_live_slots_v2()
    now_ts = time.time()
    bot_table_rows = ""

    # Generate 200+ list streamer live untuk isi dropdown otomatis (dari viewer tertinggi ke terkecil)
    select_options = '<option value="">-- Pilih Streamer Live ({len(live_streamers)}) --</option>'
    for item in live_streamers:
        s_slug = item['slug']
        v_disp = item['viewers_display']
        select_options += f'<option value="{s_slug}">{s_slug} ({v_disp})</option>'

    for b_id in ALL_REGISTERED_BOTS:
        b_data = bot_assignments.get(b_id, {})
        targets = b_data.get("targets", [])
        start_times = b_data.get("start_times", {})

        targets_badges = []
        for t in targets:
            start_t = start_times.get(t, now_ts)
            dur_min = int((now_ts - start_t) // 60)
            targets_badges.append(
                f'<span style="background:#1e293b; color:#00e676; border:1px solid #334155; padding:5px 10px; border-radius:6px; font-size:12px; margin-right:6px; display:inline-block; margin-bottom:4px;">'
                f'<b>{t}</b> <span style="color:#788596; font-size:11px;">({dur_min}m)</span> '
                f'<a href="/api/kill-streamer-bot?bot_id={b_id}&streamer={t}" style="color:#ff4d4f; text-decoration:none; margin-left:6px; font-weight:bold;">✕</a>'
                f'</span>'
            )

        badge_str = "".join(targets_badges) or '<span style="color:#ffc107; font-weight:bold;">STANDBY / NO STREAMS</span>'

        bot_table_rows += f"""
        <tr style="border-bottom:1px solid #1e2433;">
            <td style="padding:16px; font-weight:bold; font-size:14px; color:#fff;">🤖 {b_id}</td>
            <td style="padding:16px;">{badge_str}</td>
            <td style="padding:16px; color:#00e676; font-weight:bold;">{len(targets)}/{MAX_STREAMS_PER_BOT} Active</td>
            <td style="padding:16px;">
                <form action="/api/set-bot-streamer" method="get" style="display:flex; gap:6px; align-items:center;">
                    <input type="hidden" name="bot_id" value="{b_id}">
                    <select name="streamer" style="width:200px; cursor:pointer;" required>
                        {select_options}
                    </select>
                    <button type="submit" style="background:#00e676; color:#000; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">+ Add</button>
                    <a href="/api/reset-bot-auto?bot_id={b_id}" style="color:#6366f1; font-size:11px; font-weight:bold; text-decoration:none; margin-left:6px;">Auto Lock</a>
                </form>
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Bot Manager - Kick Tracker</title><meta http-equiv="refresh" content="10">{GLOBAL_CSS}</head>
    <body>
        <div class="header-bar">
            <div class="header-title">
                <div style="font-size:24px;">⚙️</div>
                <div>
                    <h1>Panel Manajemen Bot</h1>
                    <div class="header-subtitle">Status Real-Time Akun & Stream Target Locked</div>
                </div>
            </div>
            <a href="/dashboard" class="btn-back">← Kembali ke Dashboard</a>
        </div>
        <div class="panel-card">
            <table>
                <thead>
                    <tr style="border-bottom:2px solid #1e2433; color:#5c6b73; font-size:12px;">
                        <th style="padding:12px;">BOT ID</th>
                        <th style="padding:12px;">STREAMERS LOCKED (DURASI TONTON)</th>
                        <th style="padding:12px;">SLOTS</th>
                        <th style="padding:12px;">MANUAL CONTROL</th>
                    </tr>
                </thead>
                <tbody>{bot_table_rows}</tbody>
            </table>
        </div>
    </body>
    </html>
    """