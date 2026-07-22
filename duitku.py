"""
Integrasi Duitku (Payment Gateway lokal Indonesia) — Create Invoice API v2.

Dokumentasi resmi: https://docs.duitku.com/api/id/

Alur:
1. Bot memanggil create_transaction() -> dapat checkout_url (halaman pembayaran hosted
   Duitku, di sana user tinggal pilih QRIS) + reference.
2. User bayar via QRIS di halaman itu.
3. Duitku mengirim POST callback ke {PUBLIC_BASE_URL}/duitku/callback tiap kali status
   transaksi berubah. Signature diverifikasi di parse_callback().
"""
import hashlib

import aiohttp

from config import (
    DUITKU_BASE_URL,
    DUITKU_MERCHANT_CODE,
    DUITKU_API_KEY,
)


class DuitkuError(Exception):
    pass


def _sign_create_invoice(merchant_ref: str, amount: int) -> str:
    """Signature Create Invoice (v2): MD5(merchantCode + merchantOrderId + paymentAmount + apiKey)."""
    data = f"{DUITKU_MERCHANT_CODE}{merchant_ref}{amount}{DUITKU_API_KEY}"
    return hashlib.md5(data.encode()).hexdigest()


async def create_transaction(
    merchant_ref: str,
    amount: int,
    customer_name: str,
    customer_email: str,
    order_items: list[dict],
    callback_url: str | None = None,
    method: str | None = None,
) -> dict:
    """Buat invoice baru di Duitku. Tidak set paymentMethod secara default supaya
    Duitku menampilkan halaman pilihan metode pembayaran (user tinggal pilih QRIS di sana).
    Return dict standar: reference, checkout_url, qr_url (selalu None untuk Duitku), raw."""
    if not (DUITKU_MERCHANT_CODE and DUITKU_API_KEY):
        raise DuitkuError(
            "DUITKU_MERCHANT_CODE / DUITKU_API_KEY belum diset di environment variable."
        )

    product_details = ", ".join(item.get("name", "") for item in order_items) or "VIP MatchIn"

    payload = {
        "merchantCode": DUITKU_MERCHANT_CODE,
        "paymentAmount": amount,
        "merchantOrderId": merchant_ref,
        "productDetails": product_details,
        "email": customer_email,
        "customerVaName": customer_name,
        "signature": _sign_create_invoice(merchant_ref, amount),
    }
    if callback_url:
        payload["callbackUrl"] = callback_url
        payload["returnUrl"] = callback_url
    if method:
        payload["paymentMethod"] = method

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DUITKU_BASE_URL}/api/merchant/v2/inquiry",
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            body = await resp.json()

    if "paymentUrl" not in body:
        raise DuitkuError(body.get("statusMessage") or body.get("Message") or "Gagal membuat invoice Duitku.")

    return {
        "reference": body.get("reference"),
        "checkout_url": body.get("paymentUrl"),
        "qr_url": None,
        "raw": body,
    }


def _sign_callback(merchant_ref: str, amount: str) -> str:
    """Signature callback: MD5(merchantCode + amount + merchantOrderId + apiKey)."""
    data = f"{DUITKU_MERCHANT_CODE}{amount}{merchant_ref}{DUITKU_API_KEY}"
    return hashlib.md5(data.encode()).hexdigest()


def parse_callback(raw_body: bytes, headers) -> dict | None:
    """Parse callback Duitku (dikirim sebagai application/x-www-form-urlencoded) -> dict standar
    {merchant_ref, status, reference} atau None kalau signature tidak valid."""
    from urllib.parse import parse_qsl

    form = dict(parse_qsl(raw_body.decode("utf-8")))
    merchant_ref = form.get("merchantOrderId", "")
    amount = form.get("amount", "")
    signature = form.get("signature", "")

    expected = _sign_callback(merchant_ref, amount)
    if expected != signature:
        return None

    result_code = form.get("resultCode")
    status = "PAID" if result_code == "00" else "FAILED"
    return {
        "merchant_ref": merchant_ref,
        "status": status,
        "reference": form.get("reference"),
    }
