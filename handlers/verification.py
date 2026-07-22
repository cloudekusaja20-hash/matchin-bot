from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
import keyboards as kb
from states import Verification
from config import ADMIN_GROUP_ID, VERIFICATION_PHRASE

router = Router()

VERIFICATION_PROMPT = (
    "🔒 Waktunya verifikasi akun!\n\n"
    "Supaya bisa lanjut melihat profil lain, verifikasi dulu akunmu.\n\n"
    "Kirim VIDEO NOTE (pesan video bulat, bukan video biasa), sambil:\n"
    "1️⃣ Tunjukkan pose dua jari ✌️\n"
    f"2️⃣ Bilang: \"{VERIFICATION_PHRASE}\"\n\n"
    "Rekam langsung dari kamera Telegram ya (bukan pilih dari galeri)."
)


async def request_verification(chat_id: int, state: FSMContext, bot: Bot):
    """Dipanggil dari matching.py begitu user mencapai batas aksi swipe tanpa verifikasi."""
    await state.set_state(Verification.uploading_video_note)
    await bot.send_message(chat_id, VERIFICATION_PROMPT)


@router.message(Verification.uploading_video_note, F.video_note)
async def receive_video_note(message: Message, state: FSMContext, bot: Bot):
    video_note_id = message.video_note.file_id
    request_id = await db.create_verification_request(message.from_user.id, video_note_id)
    user = await db.get_user(message.from_user.id)

    await state.clear()

    await message.answer(
        "Terima kasih! Video verifikasi kamu sedang direview oleh admin. "
        "Kamu akan diberi tahu begitu selesai, mohon tunggu sebentar ya 🙏"
    )

    if ADMIN_GROUP_ID:
        caption = (
            f"🆕 Permintaan verifikasi #{request_id}\n\n"
            f"Nama: {user['name']}\nUmur: {user['age']}\nKota: {user['location']}\n"
            f"User ID: {user['user_id']}\nUsername: @{message.from_user.username or '-'}\n\n"
            f"Cek pose ✌️ dan ucapan pada video note di atas.\n\n"
            f"Kalau tombol di bawah error, ketik manual: /accverif {request_id} atau /tolakverif {request_id}"
        )
        await bot.send_video_note(ADMIN_GROUP_ID, video_note_id)
        admin_msg = await bot.send_message(
            ADMIN_GROUP_ID, caption, reply_markup=kb.verification_admin_kb(request_id)
        )
        await db.set_verification_admin_msg(request_id, admin_msg.message_id)


@router.message(Verification.uploading_video_note)
async def wrong_video_note(message: Message):
    await message.answer(
        "Mohon kirim VIDEO NOTE (pesan video bulat ⭕) langsung dari kamera Telegram, bukan video/file biasa."
    )
