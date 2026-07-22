import time
import uuid

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

import database as db
import keyboards as kb
import tripay
from states import VipPurchase
from config import (
    ADMIN_GROUP_ID, PROMO_PRICE, PRICE_WEEK, PRICE_MONTH, PRICE_LIFETIME, QRIS_INFO_TEXT,
    PACKAGE_AMOUNT, PUBLIC_BASE_URL,
)

router = Router()

PACKAGE_LABELS = {
    "promo": f"Promo Perdana ({PROMO_PRICE})",
    "week": f"1 Minggu ({PRICE_WEEK})",
    "month": f"1 Bulan ({PRICE_MONTH})",
    "lifetime": f"Lifetime ({PRICE_LIFETIME})",
}


def vip_packages(is_promo: bool):
    """Urutan paket yang ditawarkan, tergantung apakah user masih berhak promo perdana."""
    packages = []
    if is_promo:
        packages.append(("promo", f"🎁 Promo Perdana — {PROMO_PRICE}"))
    packages.append(("week", f"1 Minggu — {PRICE_WEEK}"))
    packages.append(("month", f"1 Bulan (Best Value) — {PRICE_MONTH}"))
    packages.append(("lifetime", f"Lifetime — {PRICE_LIFETIME}"))
    return packages


def vip_packages_kb(packages) -> "InlineKeyboardBuilder":
    b = InlineKeyboardBuilder()
    for i, (key, _label) in enumerate(packages):
        b.button(text=kb.NUMBER_EMOJIS[i], callback_data=f"vipn_{key}")
    b.adjust(len(packages))
    return b.as_markup()


async def show_vip_offer(chat_id: int, user_id: int, bot: Bot):
    user = await db.get_user(user_id)
    is_promo_available = not user["has_used_promo"]
    packages = vip_packages(is_promo_available)

    lines = [f"{kb.NUMBER_EMOJIS[i]} {label}" for i, (_, label) in enumerate(packages)]
    text = (
        "💎 <b>Upgrade ke VIP</b>\n\nFitur VIP:\n- Unlimited swipe\n- Kirim pesan media\n"
        "- Fitur Rewind ↩️\n- Lihat siapa yang menyukaimu\n\nPilih paket:\n\n" + "\n".join(lines)
    )
    await bot.send_message(chat_id, text, reply_markup=vip_packages_kb(packages), parse_mode="HTML")


@router.message(F.text == "/vip")
async def cmd_vip(message: Message, bot: Bot):
    await show_vip_offer(message.chat.id, message.from_user.id, bot)


@router.callback_query(F.data == "menu_vip")
async def menu_vip_cb(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await show_vip_offer(callback.message.chat.id, callback.from_user.id, bot)


def _checkout_kb(checkout_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💳 Bayar Sekarang", url=checkout_url)
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data.startswith("vipn_"))
async def choose_package(callback: CallbackQuery, state: FSMContext, bot: Bot):
    package = callback.data.replace("vipn_", "")
    if package not in PACKAGE_LABELS:
        await callback.answer()
        return
    if package == "promo":
        user = await db.get_user(callback.from_user.id)
        if user["has_used_promo"]:
            await callback.answer("Promo hanya berlaku sekali untuk pendaftar baru.", show_alert=True)
            return

    await callback.answer()
    user = await db.get_user(callback.from_user.id)
    amount = PACKAGE_AMOUNT[package]
    merchant_ref = f"VIP-{callback.from_user.id}-{package}-{int(time.time())}-{uuid.uuid4().hex[:6]}"

    await callback.message.answer(
        f"Kamu memilih paket: <b>{PACKAGE_LABELS[package]}</b>\n\nSedang menyiapkan pembayaran QRIS...",
        parse_mode="HTML",
    )

    callback_url = f"{PUBLIC_BASE_URL}/tripay/callback" if PUBLIC_BASE_URL else None

    try:
        trx = await tripay.create_transaction(
            merchant_ref=merchant_ref,
            amount=amount,
            customer_name=user["name"] or f"user{callback.from_user.id}",
            customer_email=f"user{callback.from_user.id}@matchin.local",
            order_items=[{
                "sku": package,
                "name": f"VIP MatchIn - {PACKAGE_LABELS[package]}",
                "price": amount,
                "quantity": 1,
            }],
            callback_url=callback_url,
        )
    except tripay.TripayError as e:
        await callback.message.answer(
            f"⚠️ Gagal membuat transaksi pembayaran: {e}\n\n"
            "Coba lagi beberapa saat, atau hubungi admin."
        )
        return

    await db.create_tripay_payment_request(
        user_id=callback.from_user.id,
        package=package,
        merchant_ref=merchant_ref,
        amount=amount,
        tripay_reference=trx["reference"],
        checkout_url=trx["checkout_url"],
    )

    qr_url = trx.get("qr_url")
    text = (
        f"💎 Paket: <b>{PACKAGE_LABELS[package]}</b>\n"
        f"Total: <b>Rp{amount:,}</b>\n\n"
        "Scan QRIS di gambar (atau klik tombol di bawah untuk buka halaman pembayaran), "
        "lalu bayar sesuai nominal. VIP akan aktif OTOMATIS begitu pembayaran terkonfirmasi — "
        "tidak perlu upload bukti bayar lagi 🙌"
    ).replace(",", ".")

    if qr_url:
        await bot.send_photo(
            callback.message.chat.id, qr_url, caption=text, parse_mode="HTML",
            reply_markup=_checkout_kb(trx["checkout_url"]),
        )
    else:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=_checkout_kb(trx["checkout_url"])
        )


# ---------- Fallback lama: upload bukti bayar manual (kalau Tripay belum diset / error) ----------

@router.message(F.text == "/bayarmanual")
async def cmd_manual_proof_info(message: Message, state: FSMContext):
    await state.set_state(VipPurchase.waiting_proof)
    await message.answer(
        "Mode fallback manual. Pilih paket dulu di /vip, lalu kalau pembayaran otomatis "
        "bermasalah, upload screenshot bukti transfer di sini dan admin akan cek manual.\n\n"
        + QRIS_INFO_TEXT
    )


@router.message(VipPurchase.waiting_proof, F.photo)
async def receive_payment_proof(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    package = data.get("package", "week")
    await state.clear()

    proof_photo_id = message.photo[-1].file_id
    request_id = await db.create_payment_request(message.from_user.id, package, proof_photo_id)
    user = await db.get_user(message.from_user.id)

    await message.answer(
        "Bukti pembayaran diterima! Admin akan segera memverifikasi & mengaktifkan VIP kamu 🙏"
    )

    if ADMIN_GROUP_ID:
        caption = (
            f"💳 Permintaan aktivasi VIP manual #{request_id}\n\n"
            f"Paket: {PACKAGE_LABELS.get(package, package)}\n"
            f"Nama: {user['name']}\nUser ID: {user['user_id']}\n"
            f"Username: @{message.from_user.username or '-'}\n\n"
            f"Kalau tombol di bawah error, ketik manual: /accbayar {request_id} atau /tolakbayar {request_id}"
        )
        admin_msg = await bot.send_photo(
            ADMIN_GROUP_ID, proof_photo_id, caption=caption,
            reply_markup=kb.payment_admin_kb(request_id),
        )
        await db.set_payment_admin_msg(request_id, admin_msg.message_id)


@router.message(VipPurchase.waiting_proof)
async def wrong_proof(message: Message):
    await message.answer("Mohon upload foto/screenshot bukti pembayaran QRIS.")
