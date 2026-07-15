"""รับ event จาก Telegram: ปุ่มกด บันทึก/ข้าม + รูปที่ผู้ใช้ส่งเข้ามาเพื่อค้นทันที.

รันเป็น process แยกจากตัวหาของ (main.py):
    python -m bot.listener

- กดปุ่ม 💾 บันทึก / 🗑 ข้าม บนแจ้งเตือน
- ส่ง "รูปเสื้อ" เข้าแชทบอท → บอทเอาไปค้น eBay ด้วยภาพ แล้วส่งผลลัพธ์กลับทันที
- พิมพ์ /start → ข้อความต้อนรับ

ใช้ getUpdates (long polling) — ไม่ต้องเปิด public webhook
"""
from __future__ import annotations

import base64
import os
import time
import requests
from dotenv import load_dotenv

from . import authenticity, pipeline, state, telegram

ROOT = os.path.dirname(os.path.dirname(__file__))


def _load_env() -> dict:
    load_dotenv(os.path.join(ROOT, ".env"))
    required = ["EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    env = {k: os.getenv(k) for k in required}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise SystemExit("❌ ยังไม่ได้ตั้งค่าใน .env: " + ", ".join(missing))
    return env


# ---------- ปุ่มกด บันทึก/ข้าม ----------

def _handle_callback(token: str, cb: dict) -> None:
    data = cb.get("data", "")
    callback_id = cb["id"]
    message = cb.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    is_photo = "photo" in message
    original = (message.get("caption") if is_photo else message.get("text", "")) or ""

    def update(text: str) -> None:
        if is_photo:
            telegram.edit_message_caption(token, chat_id, message_id, text)
        else:
            telegram.edit_message_text(token, chat_id, message_id, text)

    if data.startswith("save:"):
        item_id = data[len("save:"):]
        added = state.add_saved(item_id, state.load_index())
        note = "💾 บันทึกแล้ว" if added else "💾 บันทึกไว้อยู่แล้ว"
        telegram.answer_callback(token, callback_id, "บันทึกเข้ารายการแล้ว ✅")
        update(f"{original}\n\n<b>✅ {note}</b>")
    elif data.startswith("skip:"):
        telegram.answer_callback(token, callback_id, "ข้ามแล้ว")
        update(f"{original}\n\n<b>🗑 ข้ามแล้ว</b>")
    else:
        telegram.answer_callback(token, callback_id)


# ---------- ค้นด้วยรูปที่ผู้ใช้ส่งเข้ามา ----------

def _download_photo_b64(token: str, file_id: str) -> str:
    r = requests.get(telegram.API.format(token=token, method="getFile"),
                     params={"file_id": file_id}, timeout=30)
    r.raise_for_status()
    file_path = r.json()["result"]["file_path"]
    fr = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=60)
    fr.raise_for_status()
    return base64.b64encode(fr.content).decode()


def _handle_photo(token: str, config: dict, env: dict, client, message: dict) -> None:
    chat_id = message["chat"]["id"]
    file_id = message["photo"][-1]["file_id"]  # เอาไซส์ใหญ่สุด
    telegram.send_message(token, chat_id, "🔎 กำลังค้นบน eBay ด้วยรูปที่ส่งมา ...")

    try:
        image_b64 = _download_photo_b64(token, file_id)
    except Exception as e:  # noqa: BLE001
        telegram.send_message(token, chat_id, f"❌ โหลดรูปไม่สำเร็จ: {e}")
        return

    isc = config.get("instant_search", {})
    watch = {
        "name": "ค้นด้วยรูป (คุณส่งมา)",
        "max_price": isc.get("max_price"),
        "currency": isc.get("currency", "USD"),
        "conditions": isc.get("conditions"),
        "buying_options": isc.get("buying_options"),
        "resale_price": isc.get("resale_price"),
    }
    max_results = isc.get("max_results", 5)

    try:
        items = client.search_by_image(image_b64, watch, limit=max_results * 3)
    except Exception as e:  # noqa: BLE001
        telegram.send_message(token, chat_id,
                              f"❌ ค้นไม่สำเร็จ: {e}\n(Production key ผ่านการยืนยันแล้วหรือยัง?)")
        return

    if not items:
        telegram.send_message(token, chat_id,
                              "😕 ไม่เจอของที่คล้ายกันในกรอบราคา/เงื่อนไข — ลองรูปชัด ๆ หรือปรับ max_price")
        return

    if config.get("calculate_profit", False):
        resale_value, source = pipeline.resale_value_for(client, watch, config)
    else:
        resale_value, source = None, None
    auth_mode = config.get("authenticity_screen", {}).get("mode", "filter_repro")
    sent = 0
    for item in items:
        if sent >= max_results:
            break
        verdict = authenticity.assess(item.get("title", ""))
        if auth_mode in ("filter_repro", "strict") and verdict["level"] == "likely_repro":
            continue
        profit = pipeline.profit_for(item, resale_value, config, source)
        if pipeline.send_item(env, chat_id, watch["name"], item, profit):
            sent += 1
            time.sleep(0.4)
    telegram.send_message(token, chat_id, f"✅ ส่งผลลัพธ์ที่คล้ายที่สุด {sent} รายการ")


# ---------- main loop ----------

def main() -> None:
    env = _load_env()
    config = pipeline_config()
    token = env["TELEGRAM_BOT_TOKEN"]
    client = pipeline.make_client(config, env)
    offset = None
    print("👂 กำลังฟัง Telegram ... (ปุ่มกด + รับรูปค้นของ) — Ctrl+C เพื่อหยุด")

    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(telegram.API.format(token=token, method="getUpdates"),
                                params=params, timeout=40)
            for upd in resp.json().get("result", []):
                offset = upd["update_id"] + 1
                if "callback_query" in upd:
                    _handle_callback(token, upd["callback_query"])
                elif "message" in upd:
                    m = upd["message"]
                    if "photo" in m:
                        _handle_photo(token, config, env, client, m)
                    elif str(m.get("text", "")).startswith("/start"):
                        telegram.send_message(token, m["chat"]["id"],
                                              "สวัสดีครับ 👋 ส่ง <b>รูปเสื้อ</b> เข้ามาได้เลย "
                                              "เดี๋ยวผมค้นของคล้าย ๆ กันบน eBay พร้อมคิดกำไรให้")
        except requests.RequestException as e:
            print(f"[listener] เชื่อมต่อสะดุด: {e} — ลองใหม่ใน 5 วิ")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 หยุดการฟังแล้ว")
            break


def pipeline_config() -> dict:
    import json
    with open(os.path.join(ROOT, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    main()
