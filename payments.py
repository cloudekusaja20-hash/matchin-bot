"""
Saklar payment gateway. Pilih provider aktif lewat env var PAYMENT_GATEWAY
("tripay" atau "duitku"). handlers/vip.py dan webhook.py cukup import modul ini,
tidak perlu tahu detail Tripay/Duitku.

Cara ganti gateway: ubah PAYMENT_GATEWAY di environment variable Koyeb, isi
kredensial provider yang dipilih, redeploy. Tidak perlu ubah kode lain.
"""
from config import PAYMENT_GATEWAY

if PAYMENT_GATEWAY == "duitku":
    import duitku as _gateway
    CALLBACK_PATH = "/duitku/callback"
elif PAYMENT_GATEWAY == "tripay":
    import tripay as _gateway
    CALLBACK_PATH = "/tripay/callback"
else:
    raise RuntimeError(
        f"PAYMENT_GATEWAY tidak dikenal: '{PAYMENT_GATEWAY}'. Pakai 'tripay' atau 'duitku'."
    )

GatewayError = _gateway.DuitkuError if PAYMENT_GATEWAY == "duitku" else _gateway.TripayError


async def create_transaction(*args, **kwargs) -> dict:
    return await _gateway.create_transaction(*args, **kwargs)


def parse_callback(raw_body: bytes, headers) -> dict | None:
    """Return dict standar {merchant_ref, status, reference} atau None kalau signature invalid
    / bukan event yang relevan."""
    return _gateway.parse_callback(raw_body, headers)
