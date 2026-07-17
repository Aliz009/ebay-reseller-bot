"""บอทหาของบน eBay มาขายต่อ → แจ้งเตือนเข้า Telegram.

โหมดใช้งาน:
  python -m bot.main            # รันครั้งเดียว (เหมาะกับ cron)
  python -m bot.main --loop     # รันวนตาม poll_interval_seconds ใน config.json
  python -m bot.main --test     # ทดสอบว่าต่อ eBay + Telegram ได้ไหม
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

from dotenv import load_dotenv

from . import authenticity, ebay, ocr, pipeline, state, telegram

ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(ROOT, "config.json")


def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_env() -> dict:
    load_dotenv(os.path.join(ROOT, ".env"))
    required = ["EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    env = {k: os.getenv(k) for k in required}
    missing = [k for k, v in env.items() if not v]
    if missing:
        print("❌ ยังไม่ได้ตั้งค่า: " + ", ".join(missing))
        print("   → คัดลอก .env.example เป็น .env แล้วเติมค่าให้ครบ")
        sys.exit(1)
    return env


def run_once(client: ebay.EbayClient, config: dict, env: dict, prime: bool = False) -> int:
    """สแกน watch ทั้งหมด ส่งแจ้งเตือนของใหม่ คืนจำนวนที่ส่ง.

    prime=True → รอบเตรียม: จำของที่มีอยู่ตอนนี้ว่า 'เคยเห็นแล้ว' โดยไม่ส่ง
                 (ใช้รันครั้งแรกกันดัมพ์ก้อนใหญ่ แล้วค่อยส่งเฉพาะของใหม่รอบต่อไป)
    """
    seen = state.load_seen()
    limit = config.get("max_results_per_watch", 50)
    max_sends = config.get("max_sends_per_run", 0)         # 0 = ไม่จำกัด
    calc_profit = config.get("calculate_profit", False)
    alert_unknown = config.get("resale", {}).get("alert_when_unknown_profit", True)
    auth_cfg = config.get("authenticity_screen", {})
    auth_mode = auth_cfg.get("mode", "filter_repro")       # off | annotate | filter_repro | strict
    deep_check = auth_cfg.get("deep_check", False)          # ดึงรายละเอียด getItem มาเช็กด้วย
    ocr_check = auth_cfg.get("ocr_check", False)            # OCR อ่านรูปแท็กเพิ่ม
    ocr_max = auth_cfg.get("ocr_max_images", 6)
    chat_id = env["TELEGRAM_CHAT_ID"]
    new_count = 0
    primed = 0

    for watch in config.get("watches", []):
        name = watch.get("name", watch.get("query", "watch"))
        min_profit = watch.get("min_profit_percent")
        image_path = watch.get("image")
        image_dir = watch.get("image_dir")   # ค้นจากทุกรูปในโฟลเดอร์ (jpg/png)
        try:
            if image_dir:
                folder = image_dir if os.path.isabs(image_dir) else os.path.join(pipeline.ROOT, image_dir)
                paths = sorted(glob.glob(os.path.join(folder, "*.jpg"))
                               + glob.glob(os.path.join(folder, "*.jpeg"))
                               + glob.glob(os.path.join(folder, "*.png")))
                if not paths:
                    print(f"[{name}] ไม่มีรูป jpg/png ใน {image_dir} — ข้าม (ปกติบน cloud, รูปอยู่เฉพาะเครื่อง)")
                    continue
                items, seen_ids = [], set()
                for p in paths:
                    for it in client.search_by_image(pipeline.load_image_b64(p), watch, limit=limit):
                        iid = it.get("itemId")
                        if iid and iid not in seen_ids:
                            seen_ids.add(iid)
                            items.append(it)
                print(f"[{name}] ค้นจาก {len(paths)} รูป → รวมได้ {len(items)} รายการ")
            elif image_path:
                # โหมดค้นด้วยรูปเดียว
                items = client.search_by_image(pipeline.load_image_b64(image_path), watch, limit=limit)
            else:
                items = client.search(watch, limit=limit)
        except FileNotFoundError:
            print(f"[{name}] ไม่พบไฟล์รูป: {image_path} — ข้าม watch นี้")
            continue
        except Exception as e:  # noqa: BLE001 — ไม่ให้ watch เดียวล้มทั้งบอท
            print(f"[{name}] ค้นหาไม่สำเร็จ: {e}")
            continue

        # กรองซ้ำด้วยคำในชื่อ (ถ้าตั้งไว้) เช่น บังคับมีไซส์ในชื่อประกาศ
        must = watch.get("title_must_include")
        if must:
            items = [i for i in items
                     if any(m.lower() in (i.get("title", "").lower()) for m in must)]
        # กันเสื้อชนิดที่ไม่เอา (เช่น เสื้อเชิ้ตกระดุม) จากคำในชื่อ
        excl = config.get("title_must_exclude", []) + (watch.get("title_must_exclude") or [])
        if excl:
            items = [i for i in items
                     if not any(x.lower() in (i.get("title", "").lower()) for x in excl)]
        print(f"[{name}] ค้นเจอดิบ {len(items)} รายการ กำลังตรวจความแท้...")

        if calc_profit:
            resale_value, source = pipeline.resale_value_for(client, watch, config)
            if source:
                print(f"[{name}] ราคาขายต่ออ้างอิง ~{resale_value:.2f} ({source})")
        else:
            resale_value, source = None, None   # โหมดประหยัดเวลา: ไม่คิดกำไร แค่หาของ

        skipped_low = 0
        skipped_repro = 0
        capped = False
        for item in items:
            item_id = item.get("itemId")
            if not item_id or item_id in seen:
                continue

            # รอบเตรียม (prime): แค่จำว่าเคยเห็น ไม่ส่ง ไม่ต้องตรวจความแท้
            if prime:
                seen.add(item_id)
                primed += 1
                continue

            # ถึงเพดานจำนวนต่อรอบแล้ว → หยุดส่ง (ที่เหลือไม่ mark seen จะได้ส่งรอบหน้า)
            if max_sends and new_count >= max_sends:
                capped = True
                break

            # คัดกรองความแท้: ด่านแรกดูชื่อ (เร็ว) — ถ้า repro ชัดตัดทิ้งเลย ไม่ต้องยิง getItem
            verdict = authenticity.assess(item.get("title", ""))
            if auth_mode in ("filter_repro", "strict") and verdict["level"] == "likely_repro":
                seen.add(item_id)
                skipped_repro += 1
                continue

            # ด่านสอง (ฟรี): ดึงรายละเอียดเต็มมาเช็ก Made in USA / เสื้อเปล่า / คำอธิบาย
            # + ด่านสาม (ฟรี): OCR อ่านตัวหนังสือในรูปแท็ก
            if deep_check:
                try:
                    detail = client.get_item(item_id)
                    verdict = authenticity.assess_deep(detail)   # จาก aspects+คำอธิบายก่อน (เร็ว)
                    # OCR เฉพาะตัวที่ยัง "ตัดสินไม่ได้" เท่านั้น (ประหยัดเวลามาก)
                    if ocr_check and verdict["level"] == "uncertain":
                        imgs = [(detail.get("image") or {}).get("imageUrl")]
                        imgs += [a.get("imageUrl") for a in (detail.get("additionalImages") or [])]
                        ocr_text = ocr.read_images_text([u for u in imgs if u], ocr_max)
                        if ocr_text:
                            verdict = authenticity.assess_deep(detail, ocr_text)
                except Exception as e:  # noqa: BLE001 — getItem พลาดก็ใช้ผลจากชื่อไปก่อน
                    print(f"[{name}] getItem พลาด ({e}) ใช้ผลจากชื่อแทน")

            if auth_mode in ("filter_repro", "strict") and verdict["level"] == "likely_repro":
                seen.add(item_id)
                skipped_repro += 1
                continue
            if auth_mode == "strict" and verdict["level"] != "likely_authentic":
                seen.add(item_id)
                skipped_repro += 1
                continue

            profit = pipeline.profit_for(item, resale_value, config, source)

            # กรองตามเกณฑ์กำไร
            if profit is not None:
                if min_profit is not None and profit["margin_pct"] < min_profit:
                    seen.add(item_id)   # จำไว้ ไม่ต้องประเมินซ้ำ แต่ไม่แจ้ง
                    skipped_low += 1
                    continue
            elif not alert_unknown:
                continue  # ไม่มีข้อมูลกำไร และตั้งค่าไม่ให้แจ้ง → ข้าม

            if pipeline.send_item(env, chat_id, name, item, profit, verdict):
                seen.add(item_id)
                new_count += 1
                time.sleep(0.5)  # กันชน Telegram rate limit

        print(f"[{name}] เจอ {len(items)} รายการ · ข้าม repro {skipped_repro} · กำไรต่ำ {skipped_low}")
        if capped:
            print(f"⏸ ถึงเพดาน {max_sends} ตัว/รอบ — ที่เหลือรอรอบถัดไป")
            break

    state.save_seen(seen)
    if prime:
        print(f"✅ รอบเตรียม: จำของที่มีอยู่ {primed} ตัว (ไม่ส่ง) — รอบต่อไปจะส่งเฉพาะของใหม่")
    else:
        print(f"✅ ส่งของใหม่ {new_count} รายการ")
    return new_count


def test_connection(client: ebay.EbayClient, env: dict) -> None:
    print("🔌 ทดสอบ eBay ...")
    items = client.search({"query": "test", "max_price": 100, "currency": "USD"}, limit=1)
    print(f"   eBay OK (ดึงมาได้ {len(items)} รายการ)")

    print("🔌 ทดสอบ Telegram ...")
    ok = telegram.send_message(
        env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"],
        "✅ บอทหาของ eBay เชื่อมต่อสำเร็จ! พร้อมใช้งานแล้ว",
    )
    print("   Telegram OK" if ok else "   Telegram ล้มเหลว — เช็ค token/chat_id")


def main() -> None:
    parser = argparse.ArgumentParser(description="eBay reseller bot → Telegram")
    parser.add_argument("--loop", action="store_true", help="รันวนตาม interval")
    parser.add_argument("--test", action="store_true", help="ทดสอบการเชื่อมต่อ")
    parser.add_argument("--prime", action="store_true",
                        help="รอบเตรียม: จำของที่มีอยู่ตอนนี้ (ไม่ส่ง) กันดัมพ์ก้อนใหญ่รอบแรก")
    args = parser.parse_args()

    config = load_config()
    env = get_env()
    environment = config.get("environment", "production")
    client = ebay.EbayClient(
        env["EBAY_CLIENT_ID"], env["EBAY_CLIENT_SECRET"],
        marketplace=config.get("marketplace", "EBAY_US"),
        environment=environment,
    )
    print(f"🌐 โหมด eBay: {environment}")

    if args.test:
        test_connection(client, env)
        return

    if args.prime:
        print("🧰 รอบเตรียม (prime): จะจำของที่มีอยู่โดยไม่ส่ง")
        run_once(client, config, env, prime=True)
        return

    if args.loop:
        interval = config.get("poll_interval_seconds", 300)
        print(f"🔁 เริ่มโหมดวนซ้ำ ทุก {interval} วินาที (กด Ctrl+C เพื่อหยุด)")
        while True:
            run_once(client, config, env)
            time.sleep(interval)
    else:
        run_once(client, config, env)


if __name__ == "__main__":
    main()
