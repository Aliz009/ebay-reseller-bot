"""ตรรกะร่วม: สร้าง client, ประเมินราคา/กำไร, และส่ง item เข้า Telegram.

ใช้ร่วมกันทั้ง main.py (หาแบบตั้งเวลา) และ listener.py (ค้นจากรูปที่ส่งเข้าบอท)
เพื่อไม่ให้ตรรกะซ้ำซ้อน 2 ที่
"""
from __future__ import annotations

import base64
import os

from . import authenticity, ebay, market, state, telegram

ROOT = os.path.dirname(os.path.dirname(__file__))


def make_client(config: dict, env: dict) -> ebay.EbayClient:
    return ebay.EbayClient(
        env["EBAY_CLIENT_ID"], env["EBAY_CLIENT_SECRET"],
        marketplace=config.get("marketplace", "EBAY_US"),
        environment=config.get("environment", "production"),
    )


def load_image_b64(path: str) -> str:
    """อ่านไฟล์รูป (relative กับโฟลเดอร์โปรเจกต์ได้) แล้ว encode เป็น base64."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def resale_value_for(client: ebay.EbayClient, watch: dict, config: dict) -> tuple[float | None, str | None]:
    """หาราคาขายต่อ: ใช้ resale_price ที่ตั้งเอง ถ้าไม่มีก็ประเมินจาก eBay median."""
    manual = watch.get("resale_price")
    if manual:
        return float(manual), "ราคาที่คุณตั้ง (FB)"
    rc = config.get("resale", {})
    est = market.estimate_resale(client, watch, rc.get("min_comparables", 5), rc.get("comparable_limit", 100))
    if est:
        return est["median"], "อ้างอิง eBay (คร่าว ๆ)"
    return None, None


def profit_for(item: dict, resale_value: float | None, config: dict, source: str | None = None) -> dict | None:
    if resale_value is None:
        return None
    fees = config.get("fees", {})
    fee_percent = fees.get("resale_fee_percent", fees.get("final_value_percent", 0))
    fixed_fee = fees.get("fixed_fee", 0.0)
    import_cost = config.get("costs", {}).get("import_shipping_usd", 0.0)
    p = market.evaluate_profit(item, resale_value, fee_percent, fixed_fee, import_cost)
    if p and source:
        p["resale_source"] = source
    return p


def _image_url(item: dict) -> str | None:
    url = (item.get("image") or {}).get("imageUrl")
    if not url:
        thumbs = item.get("thumbnailImages") or []
        url = thumbs[0].get("imageUrl") if thumbs else None
    return url


def _chat_ids(chat_id) -> list[str]:
    """รองรับหลายปลายทาง: ใส่ chat id คั่นด้วยจุลภาคได้ เช่น 'aliceId,-groupId'."""
    return [c.strip() for c in str(chat_id).split(",") if c.strip()]


def send_item(env: dict, chat_id: str, name: str, item: dict, profit: dict | None,
              auth: dict | None = None) -> bool:
    """ส่ง 1 item เข้า Telegram (รูป+ข้อมูล+ปุ่ม) — ส่งได้หลายปลายทาง (คน/กลุ่ม).

    chat_id ใส่ได้หลายค่าโดยคั่นด้วยจุลภาค เช่น ส่งเข้า DM ตัวเอง + กลุ่มเพื่อนพร้อมกัน
    auth = ผลคัดกรองความแท้ (ถ้าไม่ส่งมา จะคัดจากชื่อประกาศให้เอง)
    """
    item_id = item.get("itemId")
    if auth is None:
        auth = authenticity.assess(item.get("title", ""))
    msg = telegram.format_item(name, item, profit, auth)
    token = env["TELEGRAM_BOT_TOKEN"]
    img = _image_url(item)

    any_sent = False
    for cid in _chat_ids(chat_id):
        if img:
            ok = telegram.send_photo(token, cid, img, msg, buttons_item_id=item_id)
        else:
            ok = telegram.send_message(token, cid, msg, buttons_item_id=item_id)
        any_sent = any_sent or ok

    if any_sent and item_id:
        state.remember_item(item_id, {
            "itemId": item_id,
            "watch": name,
            "title": item.get("title"),
            "price": item.get("price"),
            "url": item.get("itemWebUrl"),
            "profit": profit,
        })
    return any_sent
