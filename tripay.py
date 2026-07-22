"""
Integrasi Tripay (Payment Gateway lokal Indonesia) — Closed Payment / QRIS.

Dokumentasi resmi: https://tripay.co.id/developer

Alur:
1. Bot memanggil create_transaction() -> dapat checkout_url / qr_url + reference.
2. User bayar via QRIS.
3. Tripay mengirim POST callback ke {PUBLIC_BASE_URL}/tripay/callback berisi status
   transaksi terbaru. Signature callback diverifikasi pakai verify_callback_signature().
"""
import hashlib
import hmac
import json

import aiohttp

from config import (
    TRIPAY_BASE_URL,
    TRIPAY_MERCHANT_CODE,
    TRIPAY_API_KEY,
    TRIPAY_PRIVATE_KEY,
    TRIPAY_PAYMENT_METHOD,
)


class TripayError(Exception):
    pass


def _sign_create_transaction(merchant_ref: str, amount: int) -> str:
    """Signature untuk request pembuatan transaksi: HMAC-SHA256 dari
    merchant_code + merchant_ref + amount, pakai private key."""
    data = f"{TRIPAY_MERCHANT_CODE}{merchant_ref}{amount}"
    return hmac.new(
        TRIPAY_PRIVATE_KEY.encode(), data.encode(), hashlib.sha256
    ).hexdigest()


async def create_transaction(
    merchant_ref: str,
    amount: int,
    customer_name: str,
    customer_email: str,
    order_items: list[dict],
    callback_url: str | None = None,
    method: str | None = None,
) -> dict:
    """Buat transaksi baru di Tripay (Closed Payment). Return dict hasil dari Tripay
    (berisi antara lain: reference, checkout_url, qr_url, status, expired_time)."""
    if not (TRIPAY_MERCHANT_CODE and TRIPAY_API_KEY and TRIPAY_PRIVATE_KEY):
        raise TripayError(
            "TRIPAY_MERCHANT_CODE / TRIPAY_API_KEY / TRIPAY_PRIVATE_KEY belum diset di environment variable."
        )

    payload = {
        "method": method or TRIPAY_PAYMENT_METHOD,
        "merchant_ref": merchant_ref,
        "amount": amount,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "order_items": order_items,
        "signature": _sign_create_transaction(merchant_ref, amount),
    }
    if callback_url:
        payload["callback_url"] = callback_url

    headers = {"Authorization": f"Bearer {TRIPAY_API_KEY}"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{TRIPAY_BASE_URL}/transaction/create", data=payload, headers=headers
        ) as resp:
            body = await resp.json()

    if not body.get("success"):
        raise TripayError(body.get("message", "Gagal membuat transaksi Tripay."))
    return body["data"]


async def get_transaction_detail(reference: str) -> dict:
    """Cek status transaksi langsung ke Tripay (dipakai kalau mode webhook tidak dipakai,
    atau untuk double-check manual)."""
    headers = {"Authorization": f"Bearer {TRIPAY_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{TRIPAY_BASE_URL}/transaction/detail",
            params={"reference": reference},
            headers=headers,
        ) as resp:
            body = await resp.json()
    if not body.get("success"):
        raise TripayError(body.get("message", "Gagal ambil detail transaksi Tripay."))
    return body["data"]


def verify_callback_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verifikasi signature callback dari Tripay: HMAC-SHA256(private_key, raw_body_json)."""
    calc = hmac.new(TRIPAY_PRIVATE_KEY.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, signature_header or "")


def parse_callback_body(raw_body: bytes) -> dict:
    return json.loads(raw_body.decode("utf-8"))
