"""จำสถานะบอท: item ที่เคยแจ้ง, ข้อมูลย่อของ item (สำหรับปุ่ม), และรายการที่กด "บันทึก"."""
from __future__ import annotations

import json
import os

_DIR = os.path.dirname(os.path.dirname(__file__))
STATE_FILE = os.path.join(_DIR, "seen_items.json")   # id ที่แจ้งไปแล้ว (กันซ้ำ)
INDEX_FILE = os.path.join(_DIR, "items_index.json")  # id -> ข้อมูลย่อ (ให้ปุ่มบันทึกใช้)
SAVED_FILE = os.path.join(_DIR, "saved_items.json")  # รายการที่ผู้ใช้กดบันทึก


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def load_seen() -> set[str]:
    return set(_load_json(STATE_FILE, []))


def save_seen(seen: set[str]) -> None:
    # เก็บแค่ 5000 รายการล่าสุดพอ กันไฟล์บวม
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-5000:], f)


def load_index() -> dict:
    return _load_json(INDEX_FILE, {})


def remember_item(item_id: str, info: dict) -> None:
    """เก็บข้อมูลย่อของ item ไว้ให้ปุ่ม 'บันทึก' ดึงมาใช้ตอนกด."""
    index = load_index()
    index[item_id] = info
    # เก็บล่าสุด 2000 รายการพอ
    if len(index) > 2000:
        index = dict(list(index.items())[-2000:])
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def add_saved(item_id: str, index: dict) -> bool:
    """ย้าย item จาก index ไปยังรายการ 'บันทึกแล้ว'. คืน False ถ้าบันทึกซ้ำ."""
    saved = _load_json(SAVED_FILE, [])
    if any(s.get("itemId") == item_id for s in saved):
        return False
    info = index.get(item_id, {"itemId": item_id})
    info = {**info, "itemId": item_id}
    saved.append(info)
    with open(SAVED_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    return True
