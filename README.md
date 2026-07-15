# eBay Reseller Bot → Telegram

บอทหาของบน **eBay** มาขายต่อ (arbitrage) แล้วแจ้งเตือนเข้า **Telegram**
ใช้ eBay Browse API ทางการ + จับเฉพาะของที่ "เพิ่งลงใหม่" ตรงเงื่อนไข → คุณคว้าก่อนคนอื่น

## ✨ ทำอะไรได้
- ตั้ง watch ได้หลายอัน (คีย์เวิร์ด + งบซื้อสูงสุด + สภาพสินค้า + แบบซื้อ)
- ดึงของใหม่ล่าสุด กรองตามราคา/สภาพ → เด้งเข้า Telegram พร้อมลิงก์ ราคา ค่าส่ง เรตติ้งผู้ขาย
- **คำนวณกำไรอัตโนมัติ** — ประเมินราคาขายต่อจากราคาตลาด (median ของประกาศที่ยังขายอยู่) หักค่าธรรมเนียม eBay + ค่าส่ง → แจ้งเฉพาะของที่กำไร ≥ เกณฑ์ที่ตั้ง พร้อมบอกกำไรเป็น % 
- **ปุ่มกดใน Telegram** — 💾 บันทึก / 🗑 ข้าม (บันทึกเก็บลง `saved_items.json`)
- กันแจ้งซ้ำ (จำ item id ที่ส่งไปแล้วใน `seen_items.json`)

> ⚠️ **เรื่องราคาขายต่อ:** eBay Browse API ไม่ให้ข้อมูล "ราคาขายจริง (sold)" บอทจึงประเมินจาก
> ราคาประกาศที่ยังขายอยู่ — เป็นตัวเลข *ประเมิน* ควรเช็กเองก่อนซื้อ ถ้าอยากแม่นขึ้นต้องขอสิทธิ์
> Marketplace Insights API จาก eBay (โครงโค้ดรองรับไว้แล้วใน `bot/market.py`)

## 🚀 ติดตั้ง (ครั้งเดียว)

### 1. ติดตั้ง dependencies
```bash
cd ebay-reseller-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. ขอ eBay API key (ฟรี)
1. สมัคร/ล็อกอิน https://developer.ebay.com/
2. ไปที่ **My Account → Application Keys**
3. ใต้หัวข้อ **Production** เอา **App ID (Client ID)** และ **Cert ID (Client Secret)** มา

### 3. สร้าง Telegram bot
1. แชทกับ **@BotFather** → `/newbot` → ตั้งชื่อ → ได้ **bot token**
2. แชทกับ **@userinfobot** → ได้ **chat id** ของคุณ
   (อยากส่งเข้ากลุ่ม: เพิ่มบอทเข้ากลุ่ม แล้วใช้ chat id ของกลุ่ม)

### 4. ใส่ค่า
```bash
cp .env.example .env
# แล้วเปิด .env เติมค่าทั้ง 4 ตัวให้ครบ
```

### 5. ทดสอบการเชื่อมต่อ
```bash
python -m bot.main --test
```
ถ้าเห็นข้อความเด้งเข้า Telegram = พร้อมใช้ ✅

## ▶️ ใช้งาน

รันครั้งเดียว:
```bash
python -m bot.main
```

รันวนอัตโนมัติ (ทุก 5 นาที ตาม config):
```bash
python -m bot.main --loop
```

**เปิด listener ค้างไว้อีก 1 หน้าต่าง** (คนละ process กับตัวหาของ) เพื่อใช้:
```bash
python -m bot.listener
```
listener ทำ 2 อย่าง:
- **ปุ่ม บันทึก/ข้าม** — ของที่กด 💾 บันทึก จะไปกองใน `saved_items.json`
- **ค้นด้วยรูปสด ๆ** — เปิดแชทบอทในมือถือ → **ส่งรูปเสื้อเข้าไป** → บอทค้น eBay ด้วยภาพนั้นแล้วส่งผลลัพธ์ (พร้อมกำไร) กลับทันที ใช้เกณฑ์จาก `instant_search` ใน config.json

> listener ต้องมี key ครบใน `.env` เหมือน main (ใช้ eBay ค้นด้วย)

## ⚙️ ตั้งค่า watch — แก้ `config.json`
```json
{
  "name": "ชื่อที่อยากเห็นในแจ้งเตือน",
  "query": "คีย์เวิร์ดค้นหา",
  "max_price": 40,            // งบซื้อสูงสุด
  "currency": "USD",
  "conditions": ["USED", "NEW"],       // NEW / USED / etc.
  "buying_options": ["FIXED_PRICE"],   // FIXED_PRICE / AUCTION
  "min_profit_percent": 30             // แจ้งเฉพาะของที่กำไร ≥ 30% (ตัดออกได้ถ้าไม่อยากกรอง)
}
```
- `marketplace`: เปลี่ยนตลาดได้ เช่น `EBAY_US`, `EBAY_GB`, `EBAY_DE`
- `poll_interval_seconds`: ความถี่ในการเช็ค (โหมด --loop)
- `fees.final_value_percent` / `fees.fixed_fee`: ค่าธรรมเนียม eBay ที่ใช้คำนวณกำไร (ปรับตามหมวดสินค้าจริงได้)
- `resale.min_comparables`: ต้องมีประกาศเทียบราคาอย่างน้อยกี่รายการถึงจะเชื่อราคาตลาด
- `resale.alert_when_unknown_profit`: ถ้าประเมินราคาไม่ได้ (ข้อมูลน้อย) จะยังแจ้งไหม (`true` = แจ้งแต่บอกว่าไม่มีข้อมูลกำไร)

## 🗓️ ให้รันเองอัตโนมัติ (แนะนำ)
ใช้ cron บน Mac (ทุก 5 นาที):
```bash
crontab -e
# เพิ่มบรรทัด (แก้ path ให้ตรงเครื่องคุณ):
*/5 * * * * cd /Users/mac/ClaudeProjects/ebay-reseller-bot && .venv/bin/python -m bot.main >> bot.log 2>&1
```

## ⚠️ หมายเหตุ
- eBay Browse API มีโควตาฟรีต่อวัน — ถ้า watch เยอะมากให้ลดความถี่ลง
- ตัวเลข "กำไร" บอทยังไม่คำนวณให้ (ต้องดูราคาขายต่อเอง) — เฟสถัดไปเพิ่มได้ เช่น เทียบราคาเฉลี่ยของ sold listings
