from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from states import Onboarding
from config import BOT_NAME

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    referred_by = None
    if command.args and command.args.startswith("ref_"):
        try:
            referred_by = int(command.args.replace("ref_", ""))
            if referred_by == message.from_user.id:
                referred_by = None
        except ValueError:
            referred_by = None

    is_new = await db.create_user_if_not_exists(
        message.from_user.id, message.from_user.username, referred_by
    )
    user = await db.get_user(message.from_user.id)

    if user["profile_complete"]:
        from handlers.profile import show_home_menu  # import lokal, hindari circular import

        await message.answer("Selamat datang kembali! 👋")
        await show_home_menu(message.chat.id, message.from_user.id, message.bot)
        return

    await state.set_state(Onboarding.choosing_language)
    await message.answer(
        f"Selamat datang di {BOT_NAME}! 💕\n\nSilakan pilih bahasa / please choose language:",
        reply_markup=kb.language_kb(),
    )


@router.callback_query(Onboarding.choosing_language, F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await db.update_user_field(callback.from_user.id, "language", lang)
    await state.set_state(Onboarding.choosing_gender)
    await callback.message.edit_text(
        "Kamu seorang apa? (Gender kamu sendiri)",
        reply_markup=kb.gender_kb("gender"),
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_gender, F.data.startswith("gender_"))
async def set_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await db.update_user_field(callback.from_user.id, "gender", gender)
    await state.set_state(Onboarding.choosing_preference)
    await callback.message.edit_text(
        "Kamu mencari pasangan yang seperti apa?",
        reply_markup=kb.gender_kb("pref"),
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_preference, F.data.startswith("pref_"))
async def set_preference(callback: CallbackQuery, state: FSMContext):
    pref = callback.data.split("_")[1]
    await db.update_user_field(callback.from_user.id, "target_preference", pref)
    await state.set_state(Onboarding.entering_name)
    await callback.message.edit_text("Siapa nama panggilanmu?")
    await callback.answer()


@router.message(Onboarding.entering_name, F.text)
async def set_name(message: Message, state: FSMContext):
    await db.update_user_field(message.from_user.id, "name", message.text.strip()[:50])
    await state.set_state(Onboarding.entering_age)
    await message.answer("Berapa umurmu?", reply_markup=kb.age_kb())


@router.callback_query(Onboarding.entering_age, F.data.startswith("age_"))
async def set_age_button(callback: CallbackQuery, state: FSMContext):
    value = callback.data.replace("age_", "")
    await callback.answer()
    if value == "other":
        await callback.message.edit_text("Ketik umurmu (angka, contoh: 25):")
        return
    await db.update_user_field(callback.from_user.id, "age", int(value))
    await state.set_state(Onboarding.entering_location)
    await callback.message.edit_text(
        "Kamu tinggal di kota mana?", reply_markup=kb.location_kb()
    )


@router.message(Onboarding.entering_age, F.text)
async def set_age(message: Message, state: FSMContext):
    if not message.text.strip().isdigit() or not (17 <= int(message.text.strip()) <= 99):
        await message.answer("Masukkan umur yang valid (17-99).")
        return
    await db.update_user_field(message.from_user.id, "age", int(message.text.strip()))
    await state.set_state(Onboarding.entering_location)
    await message.answer("Kamu tinggal di kota mana?", reply_markup=kb.location_kb())


@router.callback_query(Onboarding.entering_location, F.data.startswith("loc_"))
async def set_location_button(callback: CallbackQuery, state: FSMContext):
    value = callback.data.replace("loc_", "")
    await callback.answer()
    if value == "other":
        await callback.message.edit_text("Ketik nama kotamu:")
        return
    await db.update_user_field(callback.from_user.id, "location", value)
    await state.set_state(Onboarding.entering_bio)
    await callback.message.edit_text(
        "Tulis bio singkat tentang dirimu, atau lewati saja:", reply_markup=kb.skip_bio_kb()
    )


@router.message(Onboarding.entering_location, F.text)
async def set_location(message: Message, state: FSMContext):
    await db.update_user_field(message.from_user.id, "location", message.text.strip().title()[:50])
    await state.set_state(Onboarding.entering_bio)
    await message.answer(
        "Tulis bio singkat tentang dirimu, atau lewati saja:", reply_markup=kb.skip_bio_kb()
    )


@router.callback_query(Onboarding.entering_bio, F.data == "bio_skip")
async def skip_bio(callback: CallbackQuery, state: FSMContext):
    await db.update_user_field(callback.from_user.id, "bio", "")
    await state.set_state(Onboarding.uploading_photo)
    await callback.answer()
    await callback.message.edit_text("Sekarang upload foto utama profil kamu:")


@router.message(Onboarding.entering_bio, F.text)
async def set_bio(message: Message, state: FSMContext):
    await db.update_user_field(message.from_user.id, "bio", message.text.strip()[:300])
    await state.set_state(Onboarding.uploading_photo)
    await message.answer("Sekarang upload foto utama profil kamu:")


@router.message(Onboarding.uploading_photo, F.photo)
async def set_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await db.update_user_field(message.from_user.id, "photo_id", photo_id)
    await db.update_user_field(message.from_user.id, "profile_complete", True)
    await state.clear()

    # Verifikasi TIDAK diminta di sini lagi. User bisa langsung mulai swipe;
    # verifikasi (video note) baru akan diminta otomatis setelah user melakukan
    # sejumlah aksi suka/lewati (lihat handlers/verification.py & matching.py).
    from handlers.profile import show_home_menu  # import lokal, hindari circular import

    await message.answer(
        "Profil kamu sudah lengkap! 🎉\n\n"
        "Kamu sudah bisa mulai menjelajah profil lain sekarang. Verifikasi akun akan "
        "diminta belakangan setelah kamu mulai aktif menyukai/melewati profil 😊"
    )
    await show_home_menu(message.chat.id, message.from_user.id, message.bot)


@router.message(Onboarding.uploading_photo)
async def wrong_photo(message: Message):
    await message.answer("Mohon kirim foto (bukan teks/dokumen) untuk foto profil.")
