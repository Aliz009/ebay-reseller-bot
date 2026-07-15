# รันบอทฟรี 24 ชม. ด้วย GitHub Actions (ไม่ต้องเปิดคอม)

บอทจะถูกรันบนเครื่องของ GitHub ทุก ~15 นาที ฟรี ไม่ต้องใช้บัตร ไม่ต้องเปิดคอมเรา

## ทำครั้งเดียว (หลัง eBay อนุมัติ Production key)

### 1. มีบัญชี GitHub
ถ้ายังไม่มี สมัครฟรีที่ https://github.com

### 2. เอาโค้ดขึ้น GitHub (แนะนำ **Public** เพื่อให้ Actions ฟรีไม่จำกัด)
> โค้ดนี้ไม่มีอะไรลับ (คีย์อยู่ใน Secrets + .env ไม่ขึ้น repo) → ตั้ง Public ได้ปลอดภัย และ **Actions ฟรีไม่จำกัดนาที**
> ถ้าอยากได้ Private: ได้เหมือนกัน แต่ต้องปรับ cron เป็นทุก 30 นาที (`*/30`) เพื่อไม่ให้เกินโควตาฟรี 2,000 นาที/เดือน
```bash
cd /Users/mac/ClaudeProjects/ebay-reseller-bot
git init
git add .
git commit -m "ebay reseller bot"
# สร้าง repo ว่าง ๆ บน github.com (ตั้งเป็น Private) แล้ว:
git remote add origin https://github.com/<ชื่อคุณ>/ebay-reseller-bot.git
git branch -M main
git push -u origin main
```
> `.env` ไม่ขึ้น repo (อยู่ใน .gitignore แล้ว) — คีย์ลับปลอดภัย

### 3. ใส่ความลับใน GitHub (Settings → Secrets and variables → Actions → New repository secret)
เพิ่ม 4 ตัว:
| ชื่อ | ค่า |
|---|---|
| `EBAY_CLIENT_ID` | App ID จาก eBay |
| `EBAY_CLIENT_SECRET` | Cert ID จาก eBay |
| `TELEGRAM_BOT_TOKEN` | token ของ @alys_ebay_finder_bot |
| `TELEGRAM_CHAT_ID` | 7693887073 |

### 4. เปิดใช้งาน
ไปแท็บ **Actions** ในหน้า repo → กด enable → กด **Run workflow** ลองรันครั้งแรกได้เลย
หลังจากนั้นมันจะรันเองทุก 15 นาที ตลอด 24 ชม.

## หมายเหตุ
- โหมดนี้ทำ **auto-push แจ้งเตือน** เท่านั้น (ปุ่มบันทึก/ข้าม + ส่งรูปค้นสด ใช้ไม่ได้ เพราะต้องมีเครื่องเปิดตลอด)
- ทุก ~15 นาทีมันเช็ก eBay 1 รอบ แล้วส่งเสื้อใหม่ที่เจอเข้า Telegram
- ไฟล์ `seen_items.json` จะถูก commit กลับอัตโนมัติเพื่อกันแจ้งซ้ำ
- ฟรีจริง:
  - **Public repo → Actions ฟรีไม่จำกัดนาที** (แนะนำ ใช้ `*/15` ได้สบาย)
  - Private repo → ฟรี 2,000 นาที/เดือน; `*/15` (96 รอบ/วัน) จะเกิน → ใช้ `*/30` แทน (≈1,440 นาที/เดือน พอดี)
