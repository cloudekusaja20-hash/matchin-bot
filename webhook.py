"""
Server HTTP kecil (aiohttp) yang menerima callback/webhook dari Tripay tiap kali
status transaksi berubah (mis. jadi PAID), lalu otomatis mengaktifkan VIP user.

Didaftarkan sebagai URL callback di dashboard Tripay:
{PUBLIC_BASE_URL}/tripay/callback
"""
import logging

from aiohttp import web

import database as db
import tripay
from config import ADMIN_GROUP_ID, PACKAGE_DAYS, PORT

logger = logging.getLogger(__name__)


async def handle_tripay_callback(request: web.Request):
    bot = request.app["bot"]
    raw_body = await request.read()
    signature = request.headers.get("X-Callback-Signature", "")

    if not tripay.verify_callback_signature(raw_body, signature):
        logger.warning("Tripay callback: signature tidak valid.")
        return web.json_response({"success": False, "message": "invalid signature"}, status=403)

    try:
        payload = tripay.parse_callback_body(raw_body)
    except Exception:
        return web.json_response({"success": False, "message": "invalid json"}, status=400)

    event = request.headers.get("X-Callback-Event", "payment_status")
    if event != "payment_status":
        return web.json_response({"success": True})

    merchant_ref = payload.get("merchant_ref")
    status = payload.get("status")  # PAID, EXPIRED, FAILED, dsb.

    req = await db.get_payment_by_merchant_ref(merchant_ref)
    if not req:
        logger.warning("Tripay callback: merchant_ref %s tidak ditemukan.", merchant_ref)
        return web.json_response({"success": True})  # tetap 200 supaya Tripay tidak retry terus

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
                        f"✅ Pembayaran Tripay #{req['id']} (user {req['user_id']}, "
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
    app.router.add_post("/tripay/callback", handle_tripay_callback)
    app.router.add_get("/", health)
    return app


async def run_webhook_server(bot):
    app = build_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("Webhook server Tripay jalan di port %s", PORT)
    return runner
