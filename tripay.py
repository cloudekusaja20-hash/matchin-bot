"""
Integrasi Tripay (Payment Gateway lokal Indonesia) — Closed Payment / QRIS.

Dokumentasi resmi: https://tripay.co.id/developer

Alur:
1. Bot memanggil create_transaction() -> dapat checkout_url / qr_url + reference.
2. User bayar via QRIS.
3. Tripay mengirim POST callback ke {PUBLIC_BASE_URL}/tripay/callback berisi status
   transaksi terbaru. Signature callback diverifikasi pakai verify_callback_signature().

Catatan: pendaftaran merchant baru Tripay kadang ditutup sementara oleh mereka.
Modul ini tetap disiapkan supaya tinggal aktifkan lagi (isi env var TRIPAY_* dan
set PAYMENT_GATEWAY=tripay) begitu pendaftaran dibuka lagi atau kalau kamu sudah
punya akun Tripay dari sumber lain.
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
    """Buat transaksi baru di Tripay (Closed Payment). Return dict berisi antara
    lain: reference, checkout_url, qr_url, status, expired_time."""
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
    data = body["data"]
    return {
        "reference": data.get("reference"),
        "checkout_url": data.get("checkout_url"),
        "qr_url": data.get("qr_url"),
        "raw": data,
    }


async def get_transaction_detail(reference: str) -> dict:
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


def parse_callback(raw_body: bytes, headers) -> dict | None:
    """Parse callback Tripay -> dict standar {merchant_ref, status, reference} atau None kalau
    bukan event pembayaran / signature tidak valid."""
    signature = headers.get("X-Callback-Signature", "")
    if not verify_callback_signature(raw_body, signature):
        return None
    event = headers.get("X-Callback-Event", "payment_status")
    if event != "payment_status":
        return None
    payload = json.loads(raw_body.decode("utf-8"))
    status_map = {"PAID": "PAID", "EXPIRED": "EXPIRED", "FAILED": "FAILED", "REFUND": "REFUND"}
    return {
        "merchant_ref": payload.get("merchant_ref"),
        "status": status_map.get(payload.get("status"), payload.get("status")),
        "reference": payload.get("reference"),
    }
