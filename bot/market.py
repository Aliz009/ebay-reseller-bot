"""ประเมินราคาขายต่อ + คำนวณกำไร.

ข้อจำกัด: eBay Browse API ไม่ให้ข้อมูล "sold listings" (ราคาขายจริง)
เราจึงใช้ค่ามัธยฐาน (median) ของประกาศที่ "ยังขายอยู่" เป็นตัวประเมินราคาตลาด
— median ทนต่อค่าผิดปกติ (ของแพงเว่อร์/ถูกเว่อร์) ได้ดีกว่าค่าเฉลี่ย

อยากแม่นขึ้น: ขอสิทธิ์ Marketplace Insights API จาก eBay แล้วมาเสียบใน
estimate_resale() แทน (ดู TODO ด้านล่าง) — โครงพร้อมรองรับ
"""
from __future__ import annotations

import statistics


def _price_of(item: dict) -> float | None:
    try:
        return float(item.get("price", {}).get("value"))
    except (TypeError, ValueError):
        return None


def _shipping_of(item: dict) -> float:
    """ค่าส่งของประกาศ (ถ้าไม่มีข้อมูลถือว่า 0 = ส่งฟรี/ไม่ทราบ)."""
    options = item.get("shippingOptions") or []
    if not options:
        return 0.0
    try:
        return float(options[0].get("shippingCost", {}).get("value", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def estimate_resale(client, watch: dict, min_comparables: int, comparable_limit: int) -> dict | None:
    """ประเมินราคาขายต่อจากประกาศที่ยังขายอยู่ (active listings).

    คืน {"median": float, "sample_size": int} หรือ None ถ้าข้อมูลน้อยเกินเชื่อถือ.
    """
    # ค้นด้วยคีย์เวิร์ด/สภาพเดียวกับ watch แต่ "ไม่จำกัดราคาสูงสุด"
    # เพื่อให้เห็นช่วงราคาตลาดจริง
    query = watch.get("resale_query") or watch.get("query")
    if not query:
        # watch แบบค้นด้วยรูปที่ไม่ได้ตั้งคีย์เวิร์ดเทียบราคา → ประเมินไม่ได้
        # (ให้ไปตั้ง resale_price เองแทน)
        return None
    comp_watch = {
        "query": query,
        "conditions": watch.get("conditions"),
        "buying_options": ["FIXED_PRICE"],  # ใช้ราคาซื้อทันทีเป็นฐานราคาตลาด
    }
    try:
        comps = client.search(comp_watch, limit=comparable_limit)
    except Exception:  # noqa: BLE001
        return None

    prices = [p for p in (_price_of(c) for c in comps) if p and p > 0]
    if len(prices) < min_comparables:
        return None

    return {"median": statistics.median(prices), "sample_size": len(prices)}

    # TODO(marketplace-insights): ถ้าได้สิทธิ์ Marketplace Insights API
    # ให้เรียก item_sales/search ดึง "ราคาขายจริง" ย้อนหลัง 90 วัน แล้วคืน
    # median ของราคานั้นแทน — จะแม่นกว่ามาก


def evaluate_profit(
    item: dict,
    resale_value: float,
    fee_percent: float,
    fixed_fee: float,
    extra_cost: float = 0.0,
) -> dict | None:
    """คำนวณกำไรของ item หนึ่งชิ้น.

    resale_value  = ราคาที่คาดว่าจะขายต่อได้ (จาก eBay median หรือราคาที่ผู้ใช้ตั้งเอง)
    fee_percent   = ค่าธรรมเนียมฝั่งที่ขาย (FB ขายเอง = 0, eBay ~13.25)
    extra_cost    = ต้นทุนแฝงต่อชิ้น เช่น ค่าส่ง+นำเข้ามาไทย

    คืน dict สรุปกำไร หรือ None ถ้าราคาไม่ครบ.
    """
    price = _price_of(item)
    if price is None:
        return None

    shipping = _shipping_of(item)                        # ค่าส่งจากผู้ขาย eBay
    buy_cost = price + shipping + extra_cost              # ต้นทุนรวมกว่าจะถึงมือเรา
    selling_fee = resale_value * (fee_percent / 100.0) + fixed_fee
    net_profit = resale_value - selling_fee - buy_cost
    margin_pct = (net_profit / buy_cost * 100.0) if buy_cost > 0 else 0.0

    return {
        "buy_cost": round(buy_cost, 2),
        "item_price": round(price, 2),
        "extra_cost": round(extra_cost, 2),
        "resale_estimate": round(resale_value, 2),
        "selling_fee": round(selling_fee, 2),
        "net_profit": round(net_profit, 2),
        "margin_pct": round(margin_pct, 1),
    }
