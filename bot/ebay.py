"""eBay Browse API client — ดึงสินค้าที่เพิ่งลงใหม่ตามเงื่อนไข watch.

ใช้ OAuth2 client_credentials (application token) ซึ่งเป็นช่องทางทางการของ eBay
เอกสาร: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""
from __future__ import annotations

import base64
import time
import urllib.parse
import requests

SCOPE = "https://api.ebay.com/oauth/api_scope"

# host ต่างกันระหว่างของจริง (production) กับสนามทดสอบ (sandbox)
_HOSTS = {
    "production": "https://api.ebay.com",
    "sandbox": "https://api.sandbox.ebay.com",
}


def _build_filters(watch: dict) -> list[str]:
    """สร้างเงื่อนไขกรอง (ราคา/สภาพ/แบบซื้อ) ใช้ร่วมกันทั้งค้นข้อความและค้นด้วยรูป."""
    filters = []
    max_price = watch.get("max_price")
    if max_price is not None:
        currency = watch.get("currency", "USD")
        filters.append(f"price:[..{max_price}]")
        filters.append(f"priceCurrency:{currency}")
    conditions = watch.get("conditions")
    if conditions:
        filters.append("conditions:{" + "|".join(conditions) + "}")
    buying = watch.get("buying_options")
    if buying:
        filters.append("buyingOptions:{" + "|".join(buying) + "}")
    return filters


class EbayClient:
    def __init__(self, client_id: str, client_secret: str, marketplace: str = "EBAY_US",
                 environment: str = "production"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace = marketplace
        host = _HOSTS.get(environment, _HOSTS["production"])
        self.token_url = f"{host}/identity/v1/oauth2/token"
        self.search_url = f"{host}/buy/browse/v1/item_summary/search"
        self.search_by_image_url = f"{host}/buy/browse/v1/item_summary/search_by_image"
        self.item_url = f"{host}/buy/browse/v1/item"
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _get_token(self) -> str:
        # cache token จนกว่าจะใกล้หมดอายุ (เผื่อ 60 วิ)
        if self._token and time.time() < self._token_expiry - 60:
            return self._token

        creds = f"{self.client_id}:{self.client_secret}".encode()
        headers = {
            "Authorization": "Basic " + base64.b64encode(creds).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials", "scope": SCOPE}
        resp = requests.post(self.token_url, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + int(payload.get("expires_in", 7200))
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": "Bearer " + self._get_token(),
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
            "Content-Type": "application/json",
        }

    def search(self, watch: dict, limit: int = 50) -> list[dict]:
        """ค้นหาด้วยคีย์เวิร์ด คืน list ของ item (เรียงของใหม่สุดก่อน)."""
        params = {
            "q": watch["query"],
            "limit": min(limit, 200),
            "sort": "newlyListed",  # ของที่เพิ่งลง = โอกาสคว้าก่อนคนอื่น
        }
        filters = _build_filters(watch)
        if filters:
            params["filter"] = ",".join(filters)

        resp = requests.get(self.search_url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []

    def search_by_image(self, image_b64: str, watch: dict, limit: int = 50) -> list[dict]:
        """ค้นหาด้วย 'รูปภาพ' — หา item ที่หน้าตา/ลายคล้ายรูปที่ส่งเข้ามา.

        image_b64 = รูปที่ encode เป็น base64 (string) แล้ว
        ใช้เงื่อนไขกรองราคา/สภาพ/แบบซื้อเดียวกับ watch ปกติ
        """
        params = {"limit": min(limit, 200)}
        filters = _build_filters(watch)
        if filters:
            params["filter"] = ",".join(filters)

        resp = requests.post(
            self.search_by_image_url,
            headers=self._headers(),
            params=params,
            json={"image": image_b64},
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []

    def get_item(self, item_id: str) -> dict:
        """ดึงรายละเอียดเต็มของสินค้า 1 ชิ้น (aspects + description) เพื่อเช็กความแท้.

        คืน dict ของ item (มี localizedAspects, description ฯลฯ) — โยน exception ถ้าพลาด
        """
        encoded = urllib.parse.quote(item_id, safe="")
        resp = requests.get(f"{self.item_url}/{encoded}", headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()
