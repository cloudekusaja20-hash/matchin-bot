from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

# Emoji keycap dipakai untuk menu bergaya list bernomor (mis. edit profil, pilih paket VIP)
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def numbered_kb(callback_prefix: str, count: int, columns: int = 1) -> InlineKeyboardMarkup:
    """Bikin keyboard tombol angka 1️⃣.. sebanyak `count`, callback_data = '{prefix}_{n}'."""
    b = InlineKeyboardBuilder()
    for i in range(count):
        b.button(text=NUMBER_EMOJIS[i], callback_data=f"{callback_prefix}_{i + 1}")
    b.adjust(columns)
    return b.as_markup()


def language_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇮🇩 Bahasa Indonesia", callback_data="lang_id")
    b.button(text="🇬🇧 English", callback_data="lang_en")
    b.adjust(2)
    return b.as_markup()


def gender_kb(prefix: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👨 Pria", callback_data=f"{prefix}_male")
    b.button(text="👩 Wanita", callback_data=f"{prefix}_female")
    if prefix == "pref":
        b.button(text="🌈 Keduanya", callback_data=f"{prefix}_both")
        b.adjust(2, 1)
    else:
        b.adjust(2)
    return b.as_markup()


def verification_admin_kb(request_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Setujui", callback_data=f"verify_ok_{request_id}")
    b.button(text="❌ Tolak", callback_data=f"verify_no_{request_id}")
    b.adjust(2)
    return b.as_markup()


def payment_admin_kb(request_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Aktifkan VIP", callback_data=f"pay_ok_{request_id}")
    b.button(text="❌ Tolak", callback_data=f"pay_no_{request_id}")
    b.adjust(2)
    return b.as_markup()


def swipe_kb(target_id: int) -> InlineKeyboardMarkup:
    """Baris reaksi cepat: murni emoji, satu baris, tanpa label teks."""
    b = InlineKeyboardBuilder()
    b.button(text="👎", callback_data=f"swipe_pass_{target_id}")
    b.button(text="❤️", callback_data=f"swipe_like_{target_id}")
    b.button(text="💌", callback_data=f"swipe_likemsg_{target_id}")
    b.button(text="↩️", callback_data="swipe_rewind")
    b.adjust(4)
    return b.as_markup()


def like_back_kb(from_user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❤️ Suka Balik & Dapatkan Kontak", callback_data=f"likeback_{from_user_id}")
    return b.as_markup()


def location_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    cities = ["Jakarta", "Surabaya", "Bandung", "Medan", "Malang", "Semarang", "Yogyakarta", "Bali"]
    for city in cities:
        b.button(text=city, callback_data=f"loc_{city}")
    b.button(text="✏️ Ketik kota lain", callback_data="loc_other")
    b.adjust(2)
    return b.as_markup()


def skip_bio_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Lewati (tanpa bio)", callback_data="bio_skip")
    return b.as_markup()


def age_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for age in [18, 20, 22, 25, 28, 30, 35, 40]:
        b.button(text=str(age), callback_data=f"age_{age}")
    b.button(text="✏️ Umur lain", callback_data="age_other")
    b.adjust(4)
    return b.as_markup()


def main_menu_kb() -> InlineKeyboardMarkup:
    """CTA utama setelah profil selesai. Fitur lain diakses lewat tombol Menu (native) di pojok kiri bawah."""
    b = InlineKeyboardBuilder()
    b.button(text="🚀 Mulai Cari Pasangan", callback_data="start_swiping")
    b.adjust(1)
    return b.as_markup()


# Ikon khas bot kita untuk kartu menu utama (bukan angka polos seperti kompetitor).
def home_menu_kb() -> InlineKeyboardMarkup:
    """Kartu profil sendiri + menu utama, tampil dengan foto seperti swipe card."""
    b = InlineKeyboardBuilder()
    b.button(text="🚀 Cari Pasangan", callback_data="start_swiping")
    b.button(text="🪞 Lihat Profilku", callback_data="menu_view_profile")
    b.button(text="✏️ Ubah Teks Profil", callback_data="menu_edit_text")
    b.button(text="📸 Ganti Foto", callback_data="menu_edit_photo")
    b.button(text="💎 Aktifkan VIP", callback_data="menu_vip")
    b.button(text="🔗 Ajak Teman", callback_data="menu_referral")
    b.adjust(2, 2, 2)
    return b.as_markup()
