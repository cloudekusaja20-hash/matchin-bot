from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from states import EditProfile, ReportUser
from config import REFERRAL_TARGET, REFERRAL_REWARD_DAYS

router = Router()


async def show_home_menu(chat_id: int, user_id: int, bot):
    """Kartu profil sendiri (foto + caption) + menu utama dengan ikon khas kita.
    Dipanggil setelah onboarding selesai dan setiap kali user buka /start lagi."""
    from handlers.matching import format_profile_caption  # import lokal, hindari circular import

    user = await db.get_user(user_id)
    caption = (
        "🏠 <b>Menu Utama</b>\n\n" + format_profile_caption(user) +
        "\n\nPilih menu di bawah untuk lanjut 👇"
    )
    if user["photo_id"]:
        await bot.send_photo(
            chat_id, user["photo_id"], caption=caption,
            reply_markup=kb.home_menu_kb(), parse_mode="HTML",
        )
    else:
        await bot.send_message(
            chat_id, caption, reply_markup=kb.home_menu_kb(), parse_mode="HTML"
        )


@router.callback_query(F.data == "menu_view_profile")
async def menu_view_profile(callback: CallbackQuery, bot):
    await callback.answer()
    await show_home_menu(callback.message.chat.id, callback.from_user.id, bot)


@router.callback_query(F.data == "menu_edit_text")
async def menu_edit_text(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(edit_field_text(), reply_markup=edit_field_kb())


@router.callback_query(F.data == "menu_edit_photo")
async def menu_edit_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(EditProfile.uploading_photo)
    await callback.message.answer("Kirim foto profil baru:")


@router.callback_query(F.data == "menu_referral")
async def menu_referral_cb(callback: CallbackQuery, bot):
    await callback.answer()
    await show_referral(callback.message.chat.id, callback.from_user.id, bot)

# Daftar field yang bisa diedit, ditampilkan sebagai menu bernomor (mirip 1️⃣ Nama, 2️⃣ Umur, dst)
EDIT_FIELDS = [
    ("name", "Nama"),
    ("age", "Umur"),
    ("location", "Kota"),
    ("bio", "Bio"),
    ("photo", "Foto"),
    ("target_preference", "Preferensi Pasangan"),
]


def edit_field_text() -> str:
    lines = [f"{kb.NUMBER_EMOJIS[i]} {label}" for i, (_, label) in enumerate(EDIT_FIELDS)]
    return "👤 <b>Edit Profil</b>\n\nPilih yang mau diubah:\n\n" + "\n".join(lines)


def edit_field_kb():
    return kb.numbered_kb("editn", len(EDIT_FIELDS), columns=3)


@router.message(F.text.in_({"/editprofile", "/profil"}))
async def cmd_edit_profile(message: Message):
    await message.answer(edit_field_text(), reply_markup=edit_field_kb())


@router.callback_query(F.data.startswith("editn_"))
async def choose_edit_field(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.replace("editn_", "")) - 1
    await callback.answer()
    if idx < 0 or idx >= len(EDIT_FIELDS):
        return
    field, _label = EDIT_FIELDS[idx]

    if field == "photo":
        await state.set_state(EditProfile.uploading_photo)
        await callback.message.answer("Kirim foto profil baru:")
        return
    if field == "target_preference":
        await callback.message.answer("Pilih preferensi pasangan baru:", reply_markup=kb.gender_kb("pref"))
        return
    await state.set_state(EditProfile.entering_value)
    await state.update_data(field=field)
    prompts = {
        "name": "Masukkan nama baru:",
        "age": "Masukkan umur baru (angka):",
        "location": "Masukkan kota baru:",
        "bio": "Masukkan bio baru:",
    }
    await callback.message.answer(prompts.get(field, "Masukkan nilai baru:"))


@router.message(EditProfile.entering_value, F.text)
async def save_edited_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    value = message.text.strip()

    if field == "age":
        if not value.isdigit() or not (17 <= int(value) <= 99):
            await message.answer("Umur tidak valid, masukkan angka 17-99.")
            return
        value = int(value)
    elif field == "location":
        value = value.title()[:50]
    elif field == "name":
        value = value[:50]
    elif field == "bio":
        value = value[:300]

    await db.update_user_field(message.from_user.id, field, value)
    await state.clear()
    await message.answer("Profil berhasil diperbarui! ✅")


@router.message(EditProfile.uploading_photo, F.photo)
async def save_edited_photo(message: Message, state: FSMContext):
    await db.update_user_field(message.from_user.id, "photo_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer("Foto profil berhasil diperbarui! ✅")


@router.message(F.text == "/pause")
async def cmd_pause(message: Message):
    user = await db.get_user(message.from_user.id)
    new_status = not user["is_paused"]
    await db.update_user_field(message.from_user.id, "is_paused", new_status)
    if new_status:
        await message.answer("Profil kamu disembunyikan sementara. Ketik /pause lagi untuk mengaktifkan kembali.")
    else:
        await message.answer("Profil kamu aktif kembali dan bisa dilihat pengguna lain. 🎉")


@router.message(F.text == "/referral")
async def cmd_referral(message: Message):
    await show_referral(message.chat.id, message.from_user.id, message.bot)


async def show_referral(chat_id: int, user_id: int, bot):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    count = await db.count_referrals(user_id)
    remaining = max(REFERRAL_TARGET - (count % REFERRAL_TARGET), 0)
    await bot.send_message(
        chat_id,
        f"🔗 Link referral kamu:\n{link}\n\n"
        f"Total teman diundang: {count}\n"
        f"Undang {REFERRAL_TARGET} teman baru (daftar + verifikasi) untuk mendapat "
        f"{REFERRAL_REWARD_DAYS} hari VIP gratis!",
    )


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Gunakan format: /report <user_id yang ingin dilaporkan>")
        return
    reported_id = int(command.args.strip())
    await state.set_state(ReportUser.waiting_reason)
    await state.update_data(reported_id=reported_id)
    await message.answer("Jelaskan alasan laporanmu:")


@router.message(ReportUser.waiting_reason, F.text)
async def save_report(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.create_report(message.from_user.id, data["reported_id"], message.text.strip())
    await state.clear()
    await message.answer("Laporan kamu sudah diteruskan ke admin. Terima kasih sudah menjaga komunitas ini aman. 🙏")
