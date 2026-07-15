# คู่มือดูเสื้อ West Coast Choppers วินเทจแท้ตรงยุค

ยุค OG ที่ตามหา: **ปลาย 1990s – กลาง 2000s** (ยุค "Long Beach, CA" ของ Jesse James)

## ✅ สัญญาณของแท้ (เทียบตอนขอรูปแท็ก/ตะเข็บ)
| จุด | ของแท้ยุคนั้น |
|---|---|
| แท็ก/เสื้อเปล่า | **Alstyle (AAA)**, Hanes, Oneita, Delta (US blanks ยุคนั้น) |
| แหล่งผลิต | **Made in USA** หรือ Fabric Made in USA / Assembled in Mexico |
| ลายสกรีน | iron cross + **"LONG BEACH, CA"** ใต้โลโก้ + ฟอนต์กอธิค + TM/® |
| เนื้อ/ตะเข็บ | ผ้าฝ้าย, คอ rib knit ดี, บางตัว single stitch, สภาพเฟด/ใช้จริง |
| ทรง | หลวมช่วงตัว/ไหล่ (ยุคนั้นตัดหลวม) |

> อ้างอิงจากเสื้อตัวอย่างของ Alice: Alstyle AAA · Made in USA/Assembled in Mexico · Long Beach, CA · Size XL — เป็นเรฟของแท้

## 🚩 ธงแดง repro / ของใหม่
- เสื้อเปล่ายุคใหม่: **Gildan, Bella Canvas, Port & Company**
- คำในประกาศ: reproduction, repro, replica, reprint, bootleg, custom, NWT/brand new, official reissue
- แหล่งผลิตยุคใหม่ (Bangladesh/Honduras/Nicaragua) บนแท็กเสื้อเปล่าสมัยใหม่
- ลายคมกริบเว่อร์/สกรีนหนาแบบงานใหม่, ทรงเข้ารูปแบบ modern

## บอทคัดกรองให้อัตโนมัติ 2 ด่าน (ฝังใน `bot/authenticity.py`)
**ด่าน 1 — ดูชื่อประกาศ (เร็ว):** จับสัญญาณ/ธงแดงในชื่อ → ตัด repro ชัด ๆ ทิ้งก่อน (ไม่เปลืองโควตา)

**ด่าน 2 — `deep_check` ดึงรายละเอียดเต็ม (getItem, ฟรี):** อ่านข้อมูลโครงสร้าง
- **Country of Manufacture = United States** → +แรง
- **แบรนด์เสื้อเปล่า** Alstyle/Hanes/Oneita (+แรง) vs Gildan/Bella (−แรง)
- คำในคำอธิบายเต็ม: made in usa, single stitch, long beach, vintage/OG
- ให้คะแนนถ่วงน้ำหนัก → `likely_authentic` (≥3) · `uncertain` · `likely_repro` (≤−2)

**ด่าน 3 — `ocr_check` OCR อ่านรูปแท็ก (Tesseract, ฟรี):** โหลดรูปสินค้าทุกใบ อ่านตัวหนังสือ
มองหา ALSTYLE / MADE IN USA / ASSEMBLED IN MEXICO (แท้) หรือ GILDAN / MADE IN HONDURAS (repro)
→ เสื้อที่ชื่อประกาศไม่บอกอะไร แต่รูปแท็กชัด ก็ถูกยกเป็น "แท้" ได้
> ต้องมี tesseract: Mac `brew install tesseract` · GitHub Actions ลงให้แล้วใน workflow · ถ้าไม่มีจะข้ามเอง

**โหมด (config `authenticity_screen.mode`):**
- `filter_repro` (ค่าเริ่มต้น): ตัด likely_repro ทิ้ง ที่เหลือส่งพร้อมป้ายสัญญาณ
- `strict`: ส่งเฉพาะ likely_authentic (แม่นสุด แต่พลาดตัวข้อมูลไม่ครบ)
- `annotate`: ส่งทุกตัว แค่ติดป้าย

**ความแม่นโดยประมาณ (อัตโนมัติ):** ดูชื่อ ~25-30% · + `deep_check` ~55-65% · + `ocr_check` อ่านแท็ก ~65-70% (เพดานของฟรี) · + คุณดูรูปแท็กยืนยัน ~90%+

> ⚠️ ยังเป็น **ตัวคัดกรอง ไม่ใช่คำตัดสินของแท้** — ของปลอมที่ก๊อปแท็ก Made in USA เนียน ๆ ยังหลุดได้ ต้องขอรูปแท็ก/ตะเข็บจริงมาเทียบก่อนซื้อทุกครั้ง

## แหล่งข้อมูล
- [Defunkd — Is this a legit West Coast Choppers tee](https://www.defunkd.com/forum/real-or-repro-f8/is-this-a-legit-west-coast-choppers-tee-t9277.html)
- [Defunkd — WCC Legit check](https://www.defunkd.com/forum/real-or-repro-f8/wcc-legit-check-t9701.html)
- [Grailed — Vintage West Coast Choppers](https://www.grailed.com/browse/vintage-west-coast-choppers)
