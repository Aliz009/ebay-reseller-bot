"""คัดกรอง "ความเป็นวินเทจแท้ตรงยุค" ของเสื้อ West Coast Choppers จากชื่อประกาศ.

อ้างอิงจากสัญญาณของแท้ยุคปลาย 90s–กลาง 2000s (Long Beach, CA era):
- เสื้อเปล่า/แท็กยุคนั้น: Alstyle (AAA), Hanes, Oneita, Delta + Made in USA
- ลาย/คำ: Long Beach, OG, vintage, 90s/y2k, Jesse James, single stitch, faded
ธงแดง repro/ของใหม่:
- เสื้อเปล่ายุคใหม่: Gildan, Bella Canvas, Port & Company
- คำ: reproduction/repro/replica/reprint/bootleg/custom, NWT/brand new, official reissue

ข้อจำกัด: ประเมินจาก "ชื่อประกาศ" เท่านั้น (eBay ไม่ได้ส่งข้อความในแท็ก/รายละเอียดมาใน
ผลค้นหา) → เป็นตัวคัดด่านแรก ไม่ใช่คำตัดสินของแท้ ต้องดูรูปแท็กจริงก่อนซื้อเสมอ
"""
from __future__ import annotations

import re

# สัญญาณ "วินเทจแท้ตรงยุค" (เจอแล้วน่าเชื่อถือขึ้น)
POSITIVE = [
    "vintage", "og", "90s", "1990", "y2k", "2000s", "early 2000",
    "made in usa", "usa made", "alstyle", "hanes", "oneita", "delta",
    "single stitch", "single-stitch", "jesse james", "long beach",
    "distressed", "faded", "thrashed", "grail",
]

# ธงแดง repro/ของใหม่ (เจอแล้วน่าสงสัย)
NEGATIVE = [
    "reproduction", "repro", "replica", "reprint", "bootleg", "custom",
    "nwt", "new with tags", "brand new", "gildan", "bella canvas",
    "port & company", "official reissue", "reissue", "2019", "2020",
    "2021", "2022", "2023", "2024", "2025", "2026",
]


def _hits(title_lower: str, words: list[str]) -> list[str]:
    return [w for w in words if w in title_lower]


def assess(title: str) -> dict:
    """คัดจาก 'ชื่อประกาศ' อย่างเดียว (เร็ว) — คืน {level, positives, negatives}.

    level = 'likely_authentic' | 'uncertain' | 'likely_repro'
    """
    t = (title or "").lower()
    pos = _hits(t, POSITIVE)
    neg = _hits(t, NEGATIVE)

    if neg:
        level = "likely_repro"
    elif pos:
        level = "likely_authentic"
    else:
        level = "uncertain"

    return {"level": level, "positives": pos, "negatives": neg}


# ตารางน้ำหนักคะแนนความแท้ (อิงสเปกผู้ใช้ + เสื้อจริงของ Alice = Alstyle)
# แต่ละคู่ = (แพตเทิร์นที่จับใน "ข้อความแบบตัดช่องว่าง", คะแนน, ป้ายที่โชว์)
POSITIVE_SIGNALS = [
    ("allsport", 30, "AllSport (แท็กยุคนั้น)"),
    ("beefy", 30, "Hanes Beefy"),
    ("fruitoftheloom", 25, "Fruit of the Loom"),
    ("deltaproweight", 25, "Delta Pro Weight"),
    ("alstyle", 25, "Alstyle"),
    ("delta", 20, "Delta"),
    ("aaa", 20, "Alstyle AAA"),
    ("unitedstates", 20, "ผลิตในสหรัฐฯ (แท็ก)"),
    ("madeinusa", 20, "Made in USA"),
    ("hanes", 15, "Hanes"),
    ("oneita", 15, "Oneita"),
    ("assembledinmexico", 15, "Assembled in Mexico"),
    ("madeinmexico", 15, "Made in Mexico"),
    ("madeinhonduras", 15, "Made in Honduras"),
    ("ironcross", 15, "Iron Cross"),
    ("jessejames", 15, "Jesse James"),
    ("copyright", 10, "Vintage Copyright"),
    ("crackedscreen", 10, "Cracked Print"),
    ("cracked", 8, "Cracked Print"),
    ("longbeach", 10, "Long Beach"),
    ("singlestitch", 5, "Single Stitch"),
    ("doublestitch", 5, "Double Stitch"),
    ("vintage", 8, "vintage"),
    ("90s", 8, "90s"),
    ("y2k", 8, "y2k"),
    ("distressed", 6, "distressed"),
    ("faded", 6, "faded"),
]

NEGATIVE_SIGNALS = [
    ("bootleg", 80, "bootleg"),
    ("reprint", 70, "reprint"),
    ("replica", 60, "replica"),
    ("reproduction", 60, "reproduction"),
    ("directtogarment", 40, "DTG print"),
    ("dtg", 40, "DTG print"),
    ("gildanmodern", 30, "Modern Gildan"),
    ("gildan", 30, "Gildan (เสื้อยุคใหม่)"),
    ("bellacanvas", 30, "Bella Canvas"),
    ("nextlevel", 25, "Next Level"),
    ("comfortcolors", 25, "Comfort Colors"),
    ("portcompany", 25, "Port & Company"),
]


def _aspects_dict(item: dict) -> dict:
    """แปลง localizedAspects ของ eBay เป็น dict {ชื่อ(lower): ค่า(lower)}."""
    out = {}
    for a in item.get("localizedAspects", []) or []:
        name = str(a.get("name", "")).lower()
        val = str(a.get("value", "")).lower()
        if name:
            out[name] = val
    return out


def assess_deep(item: dict, ocr_text: str = "") -> dict:
    """คัดแบบละเอียดจากรายละเอียดเต็ม (getItem): ชื่อ + aspects + คำอธิบาย + OCR แท็ก.

    ให้คะแนนถ่วงน้ำหนัก แล้วสรุป level + score. แม่นกว่าดูชื่ออย่างเดียวเยอะ.
    ocr_text = ข้อความที่อ่านจากรูปแท็ก (ถ้ามี) — เพิ่มความแม่นอีกขั้น
    """
    # รวมทุกแหล่งข้อความ: ชื่อ + คำอธิบาย + OCR แท็ก + ค่าใน aspects ทั้งหมด
    parts = [item.get("title") or "", item.get("description") or "",
             item.get("shortDescription") or "", ocr_text or ""]
    aspects = _aspects_dict(item)
    parts += list(aspects.values())
    blob = " ".join(parts).lower()
    # ตัวอักษร/เลขติดกันล้วน — ทน OCR/สะกดที่คำติดกัน เช่น "MADE IN U.S.A." → "madeinusa"
    compact = re.sub(r"[^a-z0-9]", "", blob)

    score = 0
    positives: list[str] = []
    negatives: list[str] = []

    for pat, wt, label in POSITIVE_SIGNALS:
        if pat in compact and label not in positives:
            score += wt
            positives.append(label)
    for pat, wt, label in NEGATIVE_SIGNALS:
        if pat in compact and label not in negatives:
            score -= wt
            negatives.append(label)

    # เกณฑ์ (คะแนนถ่วงน้ำหนักช่วงกว้าง): แท้ ≥30 · ปลอม ≤−30
    if score <= -30:
        level = "likely_repro"
    elif score >= 30:
        level = "likely_authentic"
    else:
        level = "uncertain"

    return {"level": level, "score": score, "positives": positives, "negatives": negatives}
