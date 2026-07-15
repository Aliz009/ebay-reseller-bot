"""ส่งข้อความแจ้งเตือนเข้า Telegram (พร้อมปุ่มกด บันทึก/ข้าม)."""
from __future__ import annotations

import json
import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, payload: dict) -> dict | None:
    resp = requests.post(API.format(token=token, method=method), data=payload, timeout=30)
    if resp.status_code != 200:
        print(f"[telegram] {method} ล้มเหลว {resp.status_code}: {resp.text}")
        return None
    return resp.json()


def _buttons(item_id: str) -> str:
    return json.dumps({
        "inline_keyboard": [[
            {"text": "💾 บันทึก", "callback_data": f"save:{item_id}"},
            {"text": "🗑 ข้าม", "callback_data": f"skip:{item_id}"},
        ]]
    })


def send_message(bot_token: str, chat_id: str, text: str, buttons_item_id: str | None = None) -> bool:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if buttons_item_id:
        payload["reply_markup"] = _buttons(buttons_item_id)
    return _call(bot_token, "sendMessage", payload) is not None


def send_photo(bot_token: str, chat_id: str, photo_url: str, caption: str,
               buttons_item_id: str | None = None) -> bool:
    """ส่งรูปสินค้าพร้อมแคปชั่น (มีลิงก์กดได้ในแคปชั่น) + ปุ่ม."""
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,      # caption รองรับ HTML รวมลิงก์ <a>
        "parse_mode": "HTML",
    }
    if buttons_item_id:
        payload["reply_markup"] = _buttons(buttons_item_id)
    return _call(bot_token, "sendPhoto", payload) is not None


def answer_callback(token: str, callback_id: str, text: str = "") -> None:
    _call(token, "answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def edit_message_text(token: str, chat_id: str, message_id: int, text: str) -> None:
    """แก้ข้อความเดิม (ตอนกดปุ่มแล้วอยากอัปเดตสถานะ) และลบปุ่มออก."""
    _call(token, "editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })


def edit_message_caption(token: str, chat_id: str, message_id: int, caption: str) -> None:
    """แก้แคปชั่นของข้อความรูป (ใช้ตอนกดปุ่มบนโพสต์ที่เป็นรูป)."""
    _call(token, "editMessageCaption", {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": caption,
        "parse_mode": "HTML",
    })


def _auth_line(auth: dict | None) -> str:
    """บรรทัดสรุปสัญญาณความเป็นวินเทจแท้ (ถ้ามีข้อมูล)."""
    if not auth:
        return ""
    level = auth.get("level")
    pos = ", ".join(auth.get("positives", []))
    neg = ", ".join(auth.get("negatives", []))
    if level == "likely_authentic":
        return f"\n🏷️ <b>สัญญาณวินเทจ:</b> {pos}  (ขอรูปแท็กยืนยันก่อนซื้อ)"
    if level == "likely_repro":
        return f"\n🚩 <b>ธงแดง repro:</b> {neg}  — ระวัง!"
    return "\n🏷️ ไม่มีสัญญาณยุคในชื่อ — ต้องดูรูปแท็กเอง"


def format_item(watch_name: str, item: dict, profit: dict | None = None, auth: dict | None = None) -> str:
    """จัดรูปแบบข้อความสินค้า + กำไร (ถ้ามี) + สัญญาณความแท้ (ถ้ามี)."""
    title = item.get("title", "(ไม่มีชื่อ)")
    price = item.get("price", {})
    price_str = f"{price.get('value', '?')} {price.get('currency', '')}".strip()
    condition = item.get("condition", "-")
    url = item.get("itemWebUrl", "")

    seller = item.get("seller", {})
    feedback = seller.get("feedbackPercentage")
    seller_str = ""
    if feedback:
        seller_str = f"\n👤 ผู้ขาย: {seller.get('username', '-')} ({feedback}%)"

    shipping = ""
    options = item.get("shippingOptions") or []
    if options:
        cost = options[0].get("shippingCost", {})
        val = cost.get("value")
        if val is not None:
            shipping = f"\n🚚 ค่าส่ง: {val} {cost.get('currency', '')}"

    # บรรทัดกำไร — โชว์เฉพาะเมื่อเปิดคิดกำไร (profit ไม่ None) ไม่งั้นเว้นไว้
    if profit is None:
        profit_line = ""
    else:
        emoji = "🟢" if profit["margin_pct"] >= 30 else "🟡"
        # แจกแจงต้นทุน: ราคาของ + ค่าส่ง/นำเข้า
        extra = profit.get("extra_cost", 0)
        cost_breakdown = f"ของ {profit.get('item_price', '?')}"
        if extra:
            cost_breakdown += f" + ส่ง/นำเข้า {extra}"
        source = profit.get("resale_source", "")
        source_str = f" [{source}]" if source else ""
        profit_line = (
            f"\n{emoji} <b>กำไรประเมิน: {profit['net_profit']} ({profit['margin_pct']}%)</b>"
            f"\n   ต้นทุนรวม {profit['buy_cost']} ({cost_breakdown})"
            f"\n   ขายต่อ ~{profit['resale_estimate']}{source_str}"
        )

    # ป้ายบอกว่าประกาศนี้เปิดรับต่อราคา → กดเข้าไปยื่นข้อเสนอได้
    offer_line = ""
    if "BEST_OFFER" in (item.get("buyingOptions") or []):
        offer_line = "\n💬 <b>รับข้อเสนอราคา — กดลิงก์แล้ว Make Offer ได้</b>"

    return (
        f"🔔 <b>{watch_name}</b>\n"
        f"📦 {title}\n"
        f"💰 <b>{price_str}</b>  ·  สภาพ: {condition}"
        f"{profit_line}"
        f"{_auth_line(auth)}"
        f"{shipping}{seller_str}"
        f"{offer_line}\n"
        f'🔗 <a href="{url}">เปิดหน้าสินค้า / ต่อราคาบน eBay</a>'
    )
