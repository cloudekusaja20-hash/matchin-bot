"""
Server HTTP kecil (aiohttp) yang menerima callback/webhook dari payment gateway
(Tripay atau Duitku, tergantung PAYMENT_GATEWAY) tiap kali status transaksi berubah,
lalu otomatis mengaktifkan VIP user.

Path callback disesuaikan otomatis lewat payments.CALLBACK_PATH:
- Tripay  -> {PUBLIC_BASE_URL}/tripay/callback
- Duitku  -> {PUBLIC_BASE_URL}/duitku/callback
"""
import logging

from aiohttp import web

import database as db
import payments
from config import ADMIN_GROUP_ID, PACKAGE_DAYS, PORT

logger = logging.getLogger(__name__)


async def handle_payment_callback(request: web.Request):
    bot = request.app["bot"]
    raw_body = await request.read()

    parsed = payments.parse_callback(raw_body, request.headers)
    if parsed is None:
        logger.warning("Callback pembayaran ditolak (signature invalid / event tidak relevan).")
        return web.json_response({"success": False, "message": "invalid signature"}, status=403)

    merchant_ref = parsed["merchant_ref"]
    status = parsed["status"]  # PAID, EXPIRED, FAILED, dsb.

    req = await db.get_payment_by_merchant_ref(merchant_ref)
    if not req:
        logger.warning("Callback: merchant_ref %s tidak ditemukan.", merchant_ref)
        return web.json_response({"success": True})  # tetap 200 supaya gateway tidak retry terus

    if status == "PAID":
        if req["status"] == "pending":
            await db.mark_payment_paid(req["id"])
            await db.set_payment_status(req["id"], "approved")
            days = PACKAGE_DAYS.get(req["package"], 7)
            await db.grant_vip_days(req["user_id"], days)
            if req["package"] == "promo":
                await db.update_user_field(req["user_id"], "has_used_promo", True)

            try:
                await bot.send_message(
                    req["user_id"],
                    f"🎉 Pembayaran berhasil! VIP kamu sudah aktif selama {days} hari. "
                    "Nikmati fitur unlimited swipe, rewind, dan lainnya!",
                )
            except Exception:
                pass

            if ADMIN_GROUP_ID:
                try:
                    await bot.send_message(
                        ADMIN_GROUP_ID,
                        f"✅ Pembayaran #{req['id']} (user {req['user_id']}, "
                        f"paket {req['package']}) LUNAS otomatis via webhook.",
                    )
                except Exception:
                    pass
    elif status in ("EXPIRED", "FAILED", "REFUND"):
        if req["status"] == "pending":
            await db.set_payment_status(req["id"], status.lower())

    return web.json_response({"success": True})


async def health(request: web.Request):
    return web.json_response({"status": "ok"})


def build_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post(payments.CALLBACK_PATH, handle_payment_callback)
    app.router.add_get("/", health)
    return app


async def run_webhook_server(bot):
    app = build_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("Webhook server jalan di port %s, path callback: %s", PORT, payments.CALLBACK_PATH)
    return runner
