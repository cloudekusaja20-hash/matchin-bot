import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
ADMIN_USER_IDS = [
    int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
]

BOT_NAME = "MatchIn — Dating & Meetup ⭕️"
BOT_USERNAME = "MatchInIdBot"
VERIFICATION_PHRASE = "verif dong"  # kalimat yang harus diucapkan user di video note verifikasi

FREE_DAILY_LIKES = 30

# Verifikasi tidak lagi wajib di awal pendaftaran. User boleh mulai swipe dulu,
# lalu setelah jumlah aksi (suka/lewati) mencapai angka ini, verifikasi menjadi wajib
# sebelum bisa lanjut melihat profil berikutnya.
SWIPE_VERIFICATION_THRESHOLD = 15
REFERRAL_TARGET = 3
REFERRAL_REWARD_DAYS = 3

# Harga (dalam Rupiah, hanya untuk teks tampilan)
PROMO_PRICE = "Rp10.000 / Minggu"
PRICE_WEEK = "Rp20.000"
PRICE_MONTH = "Rp45.000"
PRICE_LIFETIME = "Rp99.000"

QRIS_INFO_TEXT = (
    "Silakan scan QRIS berikut lalu upload bukti pembayaran (foto/screenshot) di chat ini.\n\n"
    "(Ganti teks ini dengan gambar QRIS kamu sendiri menggunakan admin command atau hardcode file_id foto QRIS)"
)

# Jumlah hari VIP per paket & nominal (angka, dalam Rupiah) yang dikirim ke Tripay.
# Nominal HARUS angka bulat (integer), tanpa "Rp" / titik / koma.
PACKAGE_DAYS = {
    "promo": 7,
    "week": 7,
    "month": 30,
    "lifetime": 36500,  # dianggap "seumur hidup" (100 tahun)
}
PACKAGE_AMOUNT = {
    "promo": 10000,
    "week": 20000,
    "month": 45000,
    "lifetime": 99000,
}

# ---------- SAKLAR PAYMENT GATEWAY ----------
# Pilih provider yang aktif: "duitku" atau "tripay". Tinggal ganti env var ini +
# isi kredensial provider terkait untuk pindah gateway, tanpa ubah kode.
PAYMENT_GATEWAY = os.getenv("PAYMENT_GATEWAY", "duitku")

# ---------- TRIPAY ----------
# Dapatkan dari dashboard Tripay: https://tripay.co.id/member (mode Production)
# atau menu API & Integrasi > Simulator, untuk mode Sandbox
TRIPAY_MODE = os.getenv("TRIPAY_MODE", "sandbox")  # "sandbox" atau "production"
TRIPAY_MERCHANT_CODE = os.getenv("TRIPAY_MERCHANT_CODE", "")
TRIPAY_API_KEY = os.getenv("TRIPAY_API_KEY", "")
TRIPAY_PRIVATE_KEY = os.getenv("TRIPAY_PRIVATE_KEY", "")

TRIPAY_BASE_URL = (
    "https://tripay.co.id/api-sandbox"
    if TRIPAY_MODE == "sandbox"
    else "https://tripay.co.id/api"
)

# Channel pembayaran Tripay yang dipakai (QRIS statis/dinamis via Tripay).
TRIPAY_PAYMENT_METHOD = os.getenv("TRIPAY_PAYMENT_METHOD", "QRIS")

# ---------- DUITKU ----------
# Dapatkan dari https://passport.duitku.com/merchant/Project (buat project baru,
# pilih environment sandbox/production, lalu copy Merchant Code & API Key)
DUITKU_MODE = os.getenv("DUITKU_MODE", "sandbox")  # "sandbox" atau "production"
DUITKU_MERCHANT_CODE = os.getenv("DUITKU_MERCHANT_CODE", "")
DUITKU_API_KEY = os.getenv("DUITKU_API_KEY", "")

DUITKU_BASE_URL = (
    "https://sandbox.duitku.com/webapi"
    if DUITKU_MODE == "sandbox"
    else "https://passport.duitku.com/webapi"
)
# CATATAN: sebelum pindah ke DUITKU_MODE=production, cek dulu base URL production
# yang benar di dashboard/dokumentasi resmi Duitku (docs.duitku.com) — Duitku
# punya beberapa versi API (v2 "webapi" classic vs API baru), pastikan endpoint
# di atas cocok dengan versi API yang project kamu pakai.

# Port HTTP untuk menerima callback/webhook (dipakai saat deploy sebagai Web Service)
PORT = int(os.getenv("PORT", "8000"))
# Base URL publik bot kamu di Koyeb, contoh: https://nama-app-kamu.koyeb.app
# Dipakai untuk membentuk URL callback yang didaftarkan di dashboard Tripay:
# {PUBLIC_BASE_URL}/tripay/callback
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
