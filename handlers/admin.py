from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import (
    ADMIN_GROUP_ID, ADMIN_USER_IDS, PROMO_PRICE, PRICE_WEEK, PRICE_MONTH, PRICE_LIFETIME,
    PACKAGE_DAYS,
)

router = Router()

USERS_PAGE_SIZE = 10


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def _is_admin_chat(callback: CallbackQuery) -> bool:
    return callback.message.chat.id == ADMIN_GROUP_ID


def _is_admin_context(message: Message) -> bool:
    """Diizinkan kalau dari grup admin (ADMIN_GROUP_ID) ATAU dari user yang ID-nya
    ada di ADMIN_USER_IDS (misal chat pribadi admin ke bot)."""
    if ADMIN_GROUP_ID and message.chat.id == ADMIN_GROUP_ID:
        return True
    return _is_admin(message.from_user.id)


# ---------- LIST USER (teks saja, tanpa foto; foto bisa diminta terpisah) ----------

async def _render_users_page(offset: int):
    total = await db.count_users()
    rows = await db.get_users_page(offset, USERS_PAGE_SIZE)

    if not rows:
        return "Belum ada user yang terdaftar.", None

    lines = [f"👥 <b>Daftar User</b> ({offset + 1}-{offset + len(rows)} dari {total})\n"]
    for r in rows:
        badge = " 🔵" if r["is_verified"] else ""
        vip = " 💎VIP" if r["is_vip"] else ""
        status = "✅ lengkap" if r["profile_complete"] else "⏳ belum selesai"
        username = f"@{r['username']}" if r["username"] else "-"
        age_str = f", {r['age']}" if r["age"] else ""
        lines.append(
            f"• <code>{r['user_id']}</code> — {r['name'] or '(tanpa nama)'}"
            f"{age_str}{badge}{vip}\n"
            f"   {username} | {r['location'] or '-'} | {status} | "
            f"daftar {r['created_at'].strftime('%d %b %Y')}"
        )
    text = "\n".join(lines)
    text += "\n\n📷 Lihat foto atau 🗑 hapus user lewat tombol ID di bawah:"

    b = InlineKeyboardBuilder()
    for r in rows:
        b.button(text=f"📷 {r['user_id']}", callback_data=f"adminviewphoto_{r['user_id']}")
        b.button(text=f"🗑 {r['user_id']}", callback_data=f"admindelask_{r['user_id']}")
    b.adjust(2)

    nav = InlineKeyboardBuilder()
    if offset > 0:
        nav.button(text="⬅️ Sebelumnya", callback_data=f"adminusers_{max(offset - USERS_PAGE_SIZE, 0)}")
    if offset + USERS_PAGE_SIZE < total:
        nav.button(text="➡️ Berikutnya", callback_data=f"adminusers_{offset + USERS_PAGE_SIZE}")
    nav.adjust(2)

    b.attach(nav)
    return text, b.as_markup()


@router.message(Command("users"))
async def cmd_list_users(message: Message):
    if not _is_admin_context(message):
        return  # diam-diam abaikan biar user biasa tidak tahu command ini ada
    text, markup = await _render_users_page(0)
    await message.answer(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("adminusers_"))
async def paginate_users(callback: CallbackQuery):
    is_group = ADMIN_GROUP_ID and callback.message.chat.id == ADMIN_GROUP_ID
    if not (is_group or _is_admin(callback.from_user.id)):
        await callback.answer()
        return
    offset = int(callback.data.replace("adminusers_", ""))
    text, markup = await _render_users_page(offset)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adminviewphoto_"))
async def view_user_photo(callback: CallbackQuery, bot: Bot):
    is_group = ADMIN_GROUP_ID and callback.message.chat.id == ADMIN_GROUP_ID
    if not (is_group or _is_admin(callback.from_user.id)):
        await callback.answer()
        return
    target_id = int(callback.data.replace("adminviewphoto_", ""))
    user = await db.get_user(target_id)
    if not user:
        await callback.answer("User tidak ditemukan.", show_alert=True)
        return

    badge = " 🔵" if user["is_verified"] else ""
    vip = " 💎VIP" if user["is_vip"] else ""
    caption = (
        f"<b>{user['name'] or '(tanpa nama)'}, {user['age'] or '-'}</b>{badge}{vip}\n"
        f"📍 {user['location'] or '-'}\n"
        f"ID: <code>{user['user_id']}</code>\n\n"
        f"{user['bio'] or ''}"
    )
    await callback.answer()
    if user["photo_id"]:
        await bot.send_photo(callback.message.chat.id, user["photo_id"], caption=caption, parse_mode="HTML")
    else:
        await bot.send_message(callback.message.chat.id, caption + "\n\n(User ini belum upload foto)", parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not _is_admin_context(message):
        return
    total = await db.count_users()
    complete = await db.count_users(only_complete=True)
    vip = await db.count_vip_users()
    await message.answer(
        f"📊 <b>Statistik Bot</b>\n\n"
        f"Total daftar: {total}\n"
        f"Profil lengkap: {complete}\n"
        f"VIP aktif: {vip}\n\n"
        f"Ketik /users untuk lihat daftar lengkapnya.",
        parse_mode="HTML",
    )


# ---------- HAPUS USER (permanen, wajib konfirmasi dulu) ----------

def _delete_confirm_kb(target_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ya, hapus permanen", callback_data=f"admindelconfirm_{target_id}")
    b.button(text="↩️ Batal", callback_data="admindelcancel")
    b.adjust(1)
    return b.as_markup()


async def _ask_delete_confirmation(chat_id: int, target_id: int, bot: Bot):
    user = await db.get_user(target_id)
    if not user:
        await bot.send_message(chat_id, f"User dengan ID <code>{target_id}</code> tidak ditemukan.", parse_mode="HTML")
        return
    text = (
        f"⚠️ <b>Konfirmasi Hapus User</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Nama: {user['name'] or '(tanpa nama)'}\n"
        f"Username: @{user['username'] or '-'}\n\n"
        f"Semua data user ini (profil, riwayat suka/match, verifikasi, pembayaran) akan "
        f"<b>dihapus permanen</b> dan tidak bisa dikembalikan.\n\n"
        f"Yakin mau lanjut?"
    )
    await bot.send_message(chat_id, text, reply_markup=_delete_confirm_kb(target_id), parse_mode="HTML")


@router.message(Command("hapususer"))
async def cmd_hapus_user(message: Message, command: CommandObject):
    if not _is_admin_context(message):
        return
    target_id = _parse_id_arg(command)
    if target_id is None:
        await message.answer("Format: /hapususer <user_id>\nContoh: /hapususer 80802754")
        return
    await _ask_delete_confirmation(message.chat.id, target_id, message.bot)


@router.callback_query(F.data.startswith("admindelask_"))
async def ask_delete_from_list(callback: CallbackQuery, bot: Bot):
    is_group = ADMIN_GROUP_ID and callback.message.chat.id == ADMIN_GROUP_ID
    if not (is_group or _is_admin(callback.from_user.id)):
        await callback.answer()
        return
    target_id = int(callback.data.replace("admindelask_", ""))
    await callback.answer()
    await _ask_delete_confirmation(callback.message.chat.id, target_id, bot)


@router.callback_query(F.data.startswith("admindelconfirm_"))
async def confirm_delete_user(callback: CallbackQuery, bot: Bot):
    is_group = ADMIN_GROUP_ID and callback.message.chat.id == ADMIN_GROUP_ID
    if not (is_group or _is_admin(callback.from_user.id)):
        await callback.answer()
        return
    target_id = int(callback.data.replace("admindelconfirm_", ""))
    deleted = await db.delete_user(target_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    if deleted:
        await callback.message.edit_text(
            f"🗑 User <code>{target_id}</code> berhasil dihapus permanen oleh {callback.from_user.full_name}.",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(f"User <code>{target_id}</code> sudah tidak ada / sudah terhapus.", parse_mode="HTML")
    await callback.answer("Dihapus." if deleted else "Sudah tidak ada.")


@router.callback_query(F.data == "admindelcancel")
async def cancel_delete_user(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text("Dibatalkan, user tidak jadi dihapus.")
    await callback.answer("Dibatalkan.")


# ---------- VERIFIKASI AKUN (approve/reject) ----------

async def _approve_verification_core(request_id: int, admin_name: str, bot: Bot) -> str:
    req = await db.get_verification_request(request_id)
    if not req or req["status"] != "pending":
        return "⚠️ Request verifikasi ini sudah diproses sebelumnya (atau ID tidak ditemukan)."

    await db.set_verification_status(request_id, "approved")
    await db.update_user_field(req["user_id"], "is_verified", True)

    try:
        await bot.send_message(
            req["user_id"],
            "🎉 Selamat! Akun kamu sudah terverifikasi 🔵. Kamu sekarang mendapat badge centang biru di profil.",
        )
    except Exception:
        pass
    return f"✅ Verifikasi #{request_id} disetujui oleh {admin_name}."


async def _reject_verification_core(request_id: int, admin_name: str, bot: Bot) -> str:
    req = await db.get_verification_request(request_id)
    if not req or req["status"] != "pending":
        return "⚠️ Request verifikasi ini sudah diproses sebelumnya (atau ID tidak ditemukan)."

    await db.set_verification_status(request_id, "rejected")
    try:
        await bot.send_message(
            req["user_id"],
            "Maaf, verifikasi video kamu ditolak (kemungkinan pose/ucapan tidak sesuai syarat). "
            "Ketik /swipe lagi untuk mengirim ulang video verifikasi.",
        )
    except Exception:
        pass
    return f"❌ Verifikasi #{request_id} ditolak oleh {admin_name}."


@router.callback_query(F.data.startswith("verify_ok_"))
async def approve_verification(callback: CallbackQuery, bot: Bot):
    if not _is_admin_chat(callback):
        await callback.answer("Hanya bisa dilakukan di grup admin.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[-1])
    result = await _approve_verification_core(request_id, callback.from_user.full_name, bot)
    if result.startswith("⚠️"):
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.reply(result)
    await callback.answer("Disetujui.")


@router.callback_query(F.data.startswith("verify_no_"))
async def reject_verification(callback: CallbackQuery, bot: Bot):
    if not _is_admin_chat(callback):
        await callback.answer("Hanya bisa dilakukan di grup admin.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[-1])
    result = await _reject_verification_core(request_id, callback.from_user.full_name, bot)
    if result.startswith("⚠️"):
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.reply(result)
    await callback.answer("Ditolak.")


# ---------- PEMBAYARAN VIP (approve/reject) ----------

async def _approve_payment_core(request_id: int, admin_name: str, bot: Bot) -> str:
    req = await db.get_payment_request(request_id)
    if not req or req["status"] != "pending":
        return "⚠️ Request pembayaran ini sudah diproses sebelumnya (atau ID tidak ditemukan)."

    await db.set_payment_status(request_id, "approved")
    days = PACKAGE_DAYS.get(req["package"], 7)
    await db.grant_vip_days(req["user_id"], days)
    if req["package"] == "promo":
        await db.update_user_field(req["user_id"], "has_used_promo", True)

    try:
        await bot.send_message(
            req["user_id"],
            f"🎉 Pembayaran dikonfirmasi! VIP kamu sudah aktif selama {days} hari. Nikmati fitur unlimited swipe, rewind, dan lainnya!",
        )
    except Exception:
        pass
    return f"✅ Pembayaran #{request_id} — VIP diaktifkan oleh {admin_name}."


async def _reject_payment_core(request_id: int, admin_name: str, bot: Bot) -> str:
    req = await db.get_payment_request(request_id)
    if not req or req["status"] != "pending":
        return "⚠️ Request pembayaran ini sudah diproses sebelumnya (atau ID tidak ditemukan)."

    await db.set_payment_status(request_id, "rejected")
    try:
        await bot.send_message(
            req["user_id"],
            "Maaf, bukti pembayaran kamu tidak dapat diverifikasi. Silakan hubungi admin atau coba lagi via /vip",
        )
    except Exception:
        pass
    return f"❌ Pembayaran #{request_id} ditolak oleh {admin_name}."


@router.callback_query(F.data.startswith("pay_ok_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    if not _is_admin_chat(callback):
        await callback.answer("Hanya bisa dilakukan di grup admin.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[-1])
    result = await _approve_payment_core(request_id, callback.from_user.full_name, bot)
    if result.startswith("⚠️"):
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.reply(result)
    await callback.answer("VIP diaktifkan.")


@router.callback_query(F.data.startswith("pay_no_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    if not _is_admin_chat(callback):
        await callback.answer("Hanya bisa dilakukan di grup admin.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[-1])
    result = await _reject_payment_core(request_id, callback.from_user.full_name, bot)
    if result.startswith("⚠️"):
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.reply(result)
    await callback.answer("Ditolak.")


# ---------- FALLBACK MANUAL (jaga-jaga kalau tombol Approve/Reject error/nyangkut) ----------
# Dipakai dengan format: /accbayar <id>, /tolakbayar <id>, /accverif <id>, /tolakverif <id>
# ID-nya sama dengan ID yang tertulis di pesan permintaan (mis. "Permintaan aktivasi VIP #7").

def _parse_id_arg(command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        return None
    return int(command.args.strip())


@router.message(Command("accbayar"))
async def cmd_acc_bayar(message: Message, command: CommandObject, bot: Bot):
    if not _is_admin_context(message):
        return
    request_id = _parse_id_arg(command)
    if request_id is None:
        await message.answer("Format: /accbayar <id_request>\nContoh: /accbayar 7")
        return
    result = await _approve_payment_core(request_id, message.from_user.full_name, bot)
    await message.answer(result)


@router.message(Command("tolakbayar"))
async def cmd_tolak_bayar(message: Message, command: CommandObject, bot: Bot):
    if not _is_admin_context(message):
        return
    request_id = _parse_id_arg(command)
    if request_id is None:
        await message.answer("Format: /tolakbayar <id_request>\nContoh: /tolakbayar 7")
        return
    result = await _reject_payment_core(request_id, message.from_user.full_name, bot)
    await message.answer(result)


@router.message(Command("accverif"))
async def cmd_acc_verif(message: Message, command: CommandObject, bot: Bot):
    if not _is_admin_context(message):
        return
    request_id = _parse_id_arg(command)
    if request_id is None:
        await message.answer("Format: /accverif <id_request>\nContoh: /accverif 7")
        return
    result = await _approve_verification_core(request_id, message.from_user.full_name, bot)
    await message.answer(result)


@router.message(Command("tolakverif"))
async def cmd_tolak_verif(message: Message, command: CommandObject, bot: Bot):
    if not _is_admin_context(message):
        return
    request_id = _parse_id_arg(command)
    if request_id is None:
        await message.answer("Format: /tolakverif <id_request>\nContoh: /tolakverif 7")
        return
    result = await _reject_verification_core(request_id, message.from_user.full_name, bot)
    await message.answer(result)
