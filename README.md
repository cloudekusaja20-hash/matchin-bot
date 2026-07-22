# MatchIn — Dating & Meetup ⭕️ (@MatchInIdBot) — Panduan Setup dari 0

Bot ini dibuat dengan **Python 3 + aiogram 3** dan database **Supabase (PostgreSQL)**,
dijalankan gratis di **Koyeb**. Sesuai spesifikasi: onboarding, verifikasi video note,
matching ala Tinder, kuota harian, referral, dan VIP dengan approval manual admin via QRIS.

---

## 0. Yang kamu butuhkan
- Akun Telegram (bot token sudah kamu punya ✅ — bot: **@MatchInIdBot**, nama tampilan: **MatchIn — Dating & Meetup ⭕️**)
- Akun GitHub (gratis) → https://github.com
- Akun Supabase (gratis) → https://supabase.com
- Akun Koyeb (gratis) → https://www.koyeb.com

---

## 1. Buat Database di Supabase

1. Login ke https://supabase.com/dashboard → **New Project**.
2. Isi nama project & password database (**catat password ini baik-baik**), pilih region terdekat (Singapore).
3. Setelah project selesai dibuat, buka menu **SQL Editor** di sidebar kiri.
4. Klik **New query**, lalu copy-paste seluruh isi file `schema.sql` (ada di folder project ini), klik **Run**.
   Ini akan membuat semua tabel yang dibutuhkan (`users`, `swipes`, `matches`, dll).
5. Buka menu **Project Settings → Database → Connection string → URI**.
   Copy connection string-nya, formatnya seperti:
   ```
   postgresql://postgres:[PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
   ```
   Ganti `[PASSWORD]` dengan password yang kamu buat di langkah 2. Simpan ini — akan dipakai sebagai `DATABASE_URL`.

---

## 2. Siapkan Grup Admin di Telegram

1. Buat grup Telegram baru khusus untuk kamu & tim admin (untuk review verifikasi video & bukti bayar).
2. Tambahkan bot kamu ke grup ini.
3. Untuk mendapatkan **Group ID**:
   - Kirim pesan apa saja di grup tersebut.
   - Buka `https://api.telegram.org/bot<TOKEN_BOT_KAMU>/getUpdates` di browser (ganti `<TOKEN_BOT_KAMU>` dengan token bot).
   - Cari `"chat":{"id":-100xxxxxxxxxx` — angka itu (termasuk tanda minus) adalah Group ID kamu.
4. Untuk mendapatkan **User ID** kamu sendiri (dipakai sebagai admin), chat bot **@userinfobot** di Telegram, dia akan membalas ID kamu.

---

## 3. Setup Project di Lokal (opsional, untuk testing)

```bash
git clone <repo-github-kamu>
cd dating-bot
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit file `.env` dan isi:
```
BOT_TOKEN=token_bot_kamu
DATABASE_URL=connection_string_supabase_dari_langkah_1
ADMIN_GROUP_ID=-100xxxxxxxxxx
ADMIN_USER_IDS=123456789
```

Jalankan bot untuk tes:
```bash
python bot.py
```

Buka bot kamu di Telegram, ketik `/start`, coba jalani seluruh alur onboarding.

---

## 4. Push ke GitHub

```bash
git init
git add .
git commit -m "Initial commit: dating bot"
git branch -M main
git remote add origin https://github.com/USERNAME_KAMU/NAMA_REPO.git
git push -u origin main
```

**PENTING:** file `.env` sudah otomatis di-ignore lewat `.gitignore` — jangan pernah upload token bot/database ke GitHub publik.

---

## 4b. Daftar Akun Tripay & Aktifkan Pembayaran Otomatis

Bot ini sekarang bisa mengaktifkan VIP **otomatis** (tanpa admin approve manual) lewat
Tripay (payment gateway lokal, QRIS). Cara daftar:

1. Buka https://tripay.co.id → **Daftar** (butuh KTP/data usaha untuk verifikasi mode Production —
   proses review biasanya 1-3 hari kerja).
2. Sambil menunggu verifikasi, kamu **sudah bisa langsung coding & testing** pakai mode
   **Sandbox** (uang tidak asli, instan tanpa perlu verifikasi):
   - Login ke dashboard Tripay → menu **API & Integrasi → Simulator → Merchant → Detail**.
   - Di situ ada `Merchant Code`, `API Key`, `Private Key` khusus sandbox.
   - Set `TRIPAY_MODE=sandbox` di `.env` / environment variable Koyeb, isi 3 kredensial itu.
   - Aktifkan channel QRIS di menu **API & Integrasi → Simulator → Merchant → Channel Pembayaran**.
3. Setelah akun disetujui (mode Production):
   - Menu **Merchant → Opsi → Edit** untuk lihat `Merchant Code`, `API Key`, `Private Key` asli.
   - Aktifkan channel QRIS di menu **Merchant → Opsi → Atur Channel Pembayaran**.
   - Ganti `TRIPAY_MODE=production` dan isi ulang 3 kredensial dengan yang versi production.

### Webhook vs polling — kenapa perlu Web Service

Bot ini jalan dengan **polling** (bot yang aktif "nanya" ke Telegram terus-menerus, bukan
Telegram yang kirim ke bot). Itu cukup untuk chat Telegram, tapi **Tripay perlu mengirim
notifikasi (webhook/callback) ke sebuah URL HTTP publik** setiap kali status pembayaran
berubah — ini beda mekanisme dan butuh port terbuka.

Karena itu, `bot.py` sekarang menjalankan **dua hal sekaligus** dalam satu proses:
- polling ke Telegram (seperti biasa), dan
- server HTTP kecil (`webhook.py`) yang mendengarkan di endpoint `/tripay/callback`.

Konsekuensinya: saat deploy, service type di Koyeb harus **Web Service** (bukan Worker),
supaya Koyeb kasih port publik & domain (`https://nama-app-kamu.koyeb.app`) untuk endpoint itu.

## 5. Deploy ke Koyeb (Gratis, 24/7, tanpa cold start)

1. Login ke https://app.koyeb.com → **Create Service**.
2. Pilih source **GitHub**, hubungkan akun GitHub kamu, pilih repo yang tadi di-push.
3. Pilih **Instance type: Free (Nano)**.
4. Di bagian **Service type**, pilih **Web Service** (bukan Worker) — karena sekarang bot juga
   perlu menerima webhook callback dari Tripay lewat HTTP.
   - Set **Port** ke `8000` (harus sama dengan env var `PORT`, defaultnya sudah 8000).
   - Health check path bisa dibiarkan `/` (sudah disediakan endpoint health check sederhana).
5. Di bagian **Environment variables**, tambahkan satu-satu:
   - `BOT_TOKEN` = token bot kamu
   - `DATABASE_URL` = connection string Supabase
   - `ADMIN_GROUP_ID` = id grup admin
   - `ADMIN_USER_IDS` = user id admin (pisah koma jika lebih dari satu)
   - `TRIPAY_MODE` = `sandbox` (untuk testing) atau `production`
   - `TRIPAY_MERCHANT_CODE`, `TRIPAY_API_KEY`, `TRIPAY_PRIVATE_KEY` = dari dashboard Tripay
   - `PUBLIC_BASE_URL` = **isi setelah deploy pertama kali jadi & dapat URL Koyeb**, contoh
     `https://nama-app-kamu.koyeb.app` (lihat langkah 8)
6. Build command otomatis akan menjalankan `pip install -r requirements.txt`, dan run command mengikuti `Procfile` (`web: python bot.py`).
7. Klik **Deploy**. Tunggu build selesai (~1-2 menit), status akan menjadi **Healthy**.
   Koyeb akan kasih kamu URL publik, misalnya `https://matchin-bot-namakamu.koyeb.app`.
8. **Set `PUBLIC_BASE_URL`**: edit environment variable `PUBLIC_BASE_URL` dengan URL di atas,
   lalu redeploy (Koyeb akan restart otomatis).
9. **Daftarkan URL callback di Tripay**: login dashboard Tripay → menu **Merchant → Opsi**
   (production) atau **Simulator → Merchant → Detail** (sandbox) → isi kolom **URL Callback**
   dengan `https://nama-app-kamu.koyeb.app/tripay/callback` → simpan.
10. Cek log di tab **Logs** Koyeb — kalau muncul log polling aktif + `Webhook server Tripay jalan di port 8000` tanpa error, bot sudah online 24/7 dan siap terima pembayaran otomatis.

---

## 6. Testing Alur Lengkap

1. **Onboarding**: `/start` di bot → pilih bahasa → gender → preferensi → isi nama/umur/kota/bio → upload foto → kirim video note verifikasi.
2. **Verifikasi admin**: video note otomatis terkirim ke grup admin dengan tombol ✅/❌. Klik salah satu untuk approve/reject.
3. **Swipe**: setelah profil complete, ketik `/swipe` atau tombol "🔍 Mulai Cari Pasangan" untuk melihat profil lain (butuh minimal 2 akun berbeda dengan lokasi & preferensi yang cocok untuk testing).
4. **Like/Match**: like dua akun satu sama lain → otomatis dapat notifikasi match + kontak.
5. **VIP (otomatis via Tripay)**: `/vip` → pilih paket → bot kirim QR code + tombol "💳 Bayar Sekarang" →
   di mode **sandbox** kamu bisa "bayar" tanpa uang asli lewat halaman simulator Tripay → begitu Tripay
   kirim callback `PAID`, VIP aktif otomatis & user dapat notifikasi, tanpa admin perlu klik apa-apa.
   Kalau webhook belum kamu-set (`PUBLIC_BASE_URL` kosong) atau lagi error, fallback manual masih ada:
   ketik `/bayarmanual`, upload screenshot, admin klik "✅ Aktifkan VIP" di grup admin.
6. **Referral**: `/referral` untuk dapat link unik; user baru yang daftar lewat link ini otomatis tercatat sebagai referral.
7. **Pause**: `/pause` untuk sembunyikan profil sementara.
8. **Report**: `/report <user_id>` lalu tulis alasan.

---

## 7. Struktur File

```
dating-bot/
├── bot.py                  # entry point, jalankan ini
├── config.py                # baca environment variables
├── database.py               # semua query ke Supabase Postgres
├── states.py                  # FSM states (alur percakapan)
├── keyboards.py                # tombol-tombol inline
├── schema.sql                   # SQL untuk setup tabel di Supabase
├── requirements.txt
├── Procfile                      # perintah run untuk Koyeb
├── .env.example
└── handlers/
    ├── onboarding.py    # /start, isi profil, verifikasi video
    ├── matching.py         # swipe, like, pass, rewind, match
    ├── admin.py               # approve/reject di grup admin
    ├── vip.py                   # paket VIP & upload bukti bayar
    └── profile.py               # edit profil, pause, referral, report
```

---

## 8. Catatan & Hal yang Bisa Kamu Kembangkan Lanjut

- **Tripay**: pembayaran VIP kini otomatis lewat Tripay (QRIS) — lihat bagian 4b & 5 di atas untuk daftar akun dan setup webhook. `QRIS_INFO_TEXT` di `config.py` sekarang hanya dipakai untuk fallback manual (`/bayarmanual`).
- **Ganti nominal/hari paket**: edit `PACKAGE_AMOUNT` dan `PACKAGE_DAYS` di `config.py` (satu tempat, dipakai bareng oleh alur otomatis Tripay maupun approve manual admin).
- **Auto-expire VIP**: saat ini VIP tidak otomatis nonaktif walau `vip_expiration` sudah lewat — tambahkan job terjadwal (misal pakai `apscheduler`) yang cek & set `is_vip=False` bila `vip_expiration < NOW()`.
- **Reward referral otomatis**: skema saat ini mencatat referral, tapi pemberian 3 hari VIP setiap 3 referral belum otomatis dieksekusi — tambahkan pengecekan di `create_user_if_not_exists` atau setelah verifikasi disetujui, lalu panggil `db.grant_vip_days()`.
- **"Lihat siapa yang menyukaiku"**: bisa dibuat dengan query ke tabel `swipes` mencari `action IN ('like','like_message')` dengan `target_id = user_id` yang belum kamu balas.
- Untuk keamanan produksi, sebaiknya batasi command admin (`/report` review, dsb.) hanya bisa dipakai oleh `ADMIN_USER_IDS`.

Selamat mencoba! Kalau ada error saat deploy, cek tab **Logs** di Koyeb — biasanya karena environment variable belum lengkap atau format `DATABASE_URL` salah.
