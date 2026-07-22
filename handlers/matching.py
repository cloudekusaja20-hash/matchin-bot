from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from states import SwipeMessage
from config import SWIPE_VERIFICATION_THRESHOLD
from handlers.verification import request_verification

router = Router()


def format_profile_caption(user) -> str:
    badge = " 🔵" if user["is_verified"] else ""
    return (
        f"<b>{user['name']}, {user['age']}</b>{badge}\n"
        f"📍 {user['location']}\n\n"
        f"{user['bio'] or ''}"
    )


async def send_next_profile(chat_id: int, viewer_id: int, bot: Bot, state: FSMContext):
    viewer = await db.get_user(viewer_id)
    if not viewer or not viewer["profile_complete"]:
        await bot.send_message(chat_id, "Selesaikan dulu profil kamu dengan /start")
        return

    # Verifikasi jadi wajib setelah user melakukan sejumlah aksi suka/lewati
    if not viewer["is_verified"] and viewer["swipe_count"] >= SWIPE_VERIFICATION_THRESHOLD:
        pending = await db.get_pending_verification(viewer_id)
        if pending:
            await bot.send_message(
                chat_id,
                "⏳ Video verifikasi kamu sedang direview admin. Mohon tunggu ya, kamu bisa "
                "lanjut swipe lagi setelah disetujui.",
            )
            return
        await request_verification(chat_id, state, bot)
        return

    if not viewer["is_vip"]:
        left = await db.get_likes_left(viewer_id)
        if left <= 0:
            await bot.send_message(
                chat_id,
                "Kuota suka harian kamu sudah habis 😢 Kuota akan reset otomatis dalam 24 jam, "
                "atau upgrade ke VIP untuk unlimited swipe! Ketik /vip",
            )
            return

    candidate = await db.get_next_profile(
        viewer_id, viewer["gender"], viewer["target_preference"], viewer["location"]
    )
    if not candidate:
        await bot.send_message(
            chat_id, "Belum ada profil baru untuk kamu saat ini. Coba lagi nanti ya! 🙏"
        )
        return

    caption = format_profile_caption(candidate)
    if candidate["photo_id"]:
        await bot.send_photo(
            chat_id, candidate["photo_id"], caption=caption,
            reply_markup=kb.swipe_kb(candidate["user_id"]), parse_mode="HTML",
        )
    else:
        await bot.send_message(
            chat_id, caption, reply_markup=kb.swipe_kb(candidate["user_id"]), parse_mode="HTML"
        )


@router.callback_query(F.data == "start_swiping")
async def start_swiping(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    await send_next_profile(callback.message.chat.id, callback.from_user.id, bot, state)


@router.message(F.text == "/swipe")
async def cmd_swipe(message: Message, bot: Bot, state: FSMContext):
    await send_next_profile(message.chat.id, message.from_user.id, bot, state)


async def _handle_like(callback: CallbackQuery, bot: Bot, state: FSMContext, with_message: bool, target_id: int, message_type=None, message_content=None):
    swiper_id = callback.from_user.id

    viewer = await db.get_user(swiper_id)
    if not viewer["is_vip"]:
        left = await db.get_likes_left(swiper_id)
        if left <= 0:
            await callback.answer("Kuota suka harian habis. Upgrade VIP untuk unlimited!", show_alert=True)
            return
        await db.decrement_likes(swiper_id)

    action = "like_message" if with_message else "like"
    await db.record_swipe(swiper_id, target_id, action, message_type, message_content)

    mutual = await db.check_mutual_like(swiper_id, target_id)
    if mutual:
        await db.create_match(swiper_id, target_id)
        target_user = await db.get_user(target_id)
        swiper_user = await db.get_user(swiper_id)

        swiper_contact = (
            f"@{swiper_user['username']}" if swiper_user["username"] and not swiper_user["hide_username"]
            else f"tg://user?id={swiper_user['user_id']}"
        )
        target_contact = (
            f"@{target_user['username']}" if target_user["username"] and not target_user["hide_username"]
            else f"tg://user?id={target_user['user_id']}"
        )

        await bot.send_message(
            swiper_id,
            f"🎉 IT'S A MATCH! Kamu dan {target_user['name']} saling menyukai!\nKontak: {target_contact}",
        )
        await bot.send_message(
            target_id,
            f"🎉 IT'S A MATCH! Kamu dan {swiper_user['name']} saling menyukai!\nKontak: {swiper_contact}",
        )
    else:
        target_user = await db.get_user(target_id)
        if with_message:
            await bot.send_message(
                target_id,
                f"💌 Seseorang menyukai profilmu dan mengirim pesan!\n\n"
                f"Ketik /swipe untuk melihat siapa yang menyukaimu (fitur VIP), "
                f"atau upgrade VIP untuk melihat semua yang menyukaimu.",
            )

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Tersimpan!")
    await send_next_profile(callback.message.chat.id, swiper_id, bot, state)


@router.callback_query(F.data.startswith("swipe_like_"))
async def swipe_like(callback: CallbackQuery, bot: Bot, state: FSMContext):
    target_id = int(callback.data.split("_")[-1])
    await _handle_like(callback, bot, state, with_message=False, target_id=target_id)


@router.callback_query(F.data.startswith("swipe_pass_"))
async def swipe_pass(callback: CallbackQuery, bot: Bot, state: FSMContext):
    swiper_id = callback.from_user.id
    target_id = int(callback.data.split("_")[-1])
    await db.record_swipe(swiper_id, target_id, "pass")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await send_next_profile(callback.message.chat.id, swiper_id, bot, state)


@router.callback_query(F.data.startswith("swipe_likemsg_"))
async def swipe_like_with_message(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[-1])
    await state.set_state(SwipeMessage.waiting_message)
    await state.update_data(target_id=target_id)
    await callback.answer()
    await callback.message.answer("Tulis pesan (teks/foto/video) yang ingin kamu kirimkan bersama suka-mu:")


@router.message(SwipeMessage.waiting_message)
async def receive_swipe_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_id = data["target_id"]
    await state.clear()

    if message.text:
        msg_type, msg_content = "text", message.text
    elif message.photo:
        msg_type, msg_content = "photo", message.photo[-1].file_id
    elif message.video:
        msg_type, msg_content = "video", message.video.file_id
    else:
        await message.answer("Format tidak didukung, coba kirim teks, foto, atau video.")
        return

    class FakeCallback:
        pass

    # Reuse _handle_like logic directly
    swiper_id = message.from_user.id
    viewer = await db.get_user(swiper_id)
    if not viewer["is_vip"]:
        left = await db.get_likes_left(swiper_id)
        if left <= 0:
            await message.answer("Kuota suka harian habis. Upgrade VIP untuk unlimited!")
            return
        await db.decrement_likes(swiper_id)

    await db.record_swipe(swiper_id, target_id, "like_message", msg_type, msg_content)
    mutual = await db.check_mutual_like(swiper_id, target_id)

    if mutual:
        await db.create_match(swiper_id, target_id)
        target_user = await db.get_user(target_id)
        swiper_user = await db.get_user(swiper_id)
        swiper_contact = (
            f"@{swiper_user['username']}" if swiper_user["username"] and not swiper_user["hide_username"]
            else f"tg://user?id={swiper_user['user_id']}"
        )
        target_contact = (
            f"@{target_user['username']}" if target_user["username"] and not target_user["hide_username"]
            else f"tg://user?id={target_user['user_id']}"
        )
        await message.answer(f"🎉 IT'S A MATCH! Kontak: {target_contact}")
        await bot.send_message(target_id, f"🎉 IT'S A MATCH! Kontak: {swiper_contact}")
    else:
        await message.answer("Suka + pesan terkirim! 💌")
        await bot.send_message(
            target_id,
            f"💌 Seseorang menyukai profilmu dan mengirim pesan! Ketik /swipe untuk cek.",
            reply_markup=kb.like_back_kb(swiper_id),
        )

    await send_next_profile(message.chat.id, swiper_id, bot, state)


@router.callback_query(F.data == "swipe_rewind")
async def swipe_rewind(callback: CallbackQuery, bot: Bot):
    viewer = await db.get_user(callback.from_user.id)
    if not viewer["is_vip"]:
        await callback.answer("Fitur Rewind khusus untuk pengguna VIP. Ketik /vip untuk upgrade.", show_alert=True)
        return
    last = await db.get_last_swipe_target(callback.from_user.id)
    if not last:
        await callback.answer("Tidak ada profil sebelumnya untuk di-rewind.", show_alert=True)
        return
    await db.undo_swipe(callback.from_user.id, last["target_id"])
    await callback.answer("Rewind berhasil!")
    candidate = await db.get_user(last["target_id"])
    caption = format_profile_caption(candidate)
    if candidate["photo_id"]:
        await bot.send_photo(
            callback.message.chat.id, candidate["photo_id"], caption=caption,
            reply_markup=kb.swipe_kb(candidate["user_id"]), parse_mode="HTML",
        )
    else:
        await bot.send_message(
            callback.message.chat.id, caption, reply_markup=kb.swipe_kb(candidate["user_id"]), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("likeback_"))
async def like_back(callback: CallbackQuery, bot: Bot, state: FSMContext):
    from_user_id = int(callback.data.split("_")[-1])
    await _handle_like(callback, bot, state, with_message=False, target_id=from_user_id)
