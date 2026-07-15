"""OCR อ่านตัวหนังสือจากรูปสินค้า (เช่น รูปแท็กคอ) ด้วย Tesseract (ฟรี, โอเพนซอร์ส).

ใช้เพื่อดึงคำในแท็กจริง เช่น ALSTYLE / MADE IN USA / ASSEMBLED IN MEXICO / GILDAN
มาป้อนเข้าตัวคัดกรองความแท้ → ดัน % ความแม่นขึ้นอีกโดยไม่เสียเงิน

ต้องมี binary 'tesseract' ในเครื่อง:
- Mac:   brew install tesseract
- Ubuntu (GitHub Actions): apt-get install -y tesseract-ocr
ถ้าไม่มี จะข้ามอย่างนุ่มนวล (คืนค่าว่าง ไม่ทำให้บอทล้ม)
"""
from __future__ import annotations

import io
import requests

try:
    import pytesseract
    from PIL import Image
except ImportError:  # ยังไม่ได้ลง lib
    pytesseract = None
    Image = None

_warned = False


def available() -> bool:
    global _warned
    if pytesseract is None or Image is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 — ไม่มี binary tesseract
        if not _warned:
            print("[ocr] ไม่พบ tesseract ในเครื่อง — ข้ามการอ่านแท็ก (ลง: brew install tesseract)")
            _warned = True
        return False


def read_images_text(image_urls: list[str], max_images: int = 6) -> str:
    """โหลดรูปแล้ว OCR รวมข้อความทั้งหมด (lowercase). คืน '' ถ้าอ่านไม่ได้/ไม่มี tesseract."""
    if not available():
        return ""
    texts = []
    for url in image_urls[:max_images]:
        if not url:
            continue
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            txt = pytesseract.image_to_string(img)
            if txt and txt.strip():
                texts.append(txt)
        except Exception:  # noqa: BLE001 — รูปเดียวพลาดข้ามไป
            continue
    return " ".join(texts).lower()
