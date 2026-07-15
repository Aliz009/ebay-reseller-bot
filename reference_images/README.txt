วางรูปเสื้อตัวอย่างที่อยากได้ไว้ในโฟลเดอร์นี้ (.jpg / .png)

ตัวอย่างการใช้งาน:
1. เซฟรูปเสื้อ WCC OG ที่อยากได้ → วางไว้ที่นี่ เช่น  wcc_og_sample.jpg
2. เพิ่ม watch แบบค้นด้วยรูปใน config.json:

   {
     "name": "WCC OG (ค้นด้วยรูป)",
     "image": "reference_images/wcc_og_sample.jpg",
     "max_price": 170,
     "currency": "USD",
     "conditions": ["USED"],
     "buying_options": ["FIXED_PRICE", "AUCTION"],
     "resale_price": 250,
     "min_profit_percent": 20
   }

หมายเหตุ:
- โหมดค้นด้วยรูป "ไม่มีคีย์เวิร์ด" → ระบุไซส์ในคำค้นไม่ได้
  ถ้าอยากบังคับไซส์ ให้เพิ่ม  "title_must_include": ["XL", "Large"]
  (บอทจะเก็บเฉพาะประกาศที่ชื่อมีคำนั้น)
- โหมดรูปประเมินราคาตลาดอัตโนมัติไม่ได้ → แนะนำตั้ง "resale_price" เอง
  (ราคาที่คุณจะขายต่อบน FB) เพื่อให้คำนวณกำไรได้
- รูปยิ่งชัด เห็นลายเต็มตัว ผลค้นยิ่งตรง
