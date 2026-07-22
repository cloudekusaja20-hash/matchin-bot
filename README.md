# MatchIn — Dating & Meetup ⭕️ (@MatchInIdBot) — Panduan Setup dari 0

Bot ini dibuat dengan **Python 3 + aiogram 3** dan database **Supabase (PostgreSQL)**,
dijalankan gratis di **Render**. Sesuai spesifikasi: onboarding, verifikasi video note,
matching ala Tinder, kuota harian, referral, dan VIP dengan approval manual admin via QRIS.

---

## 0. Yang kamu butuhkan
- Akun Telegram (bot token sudah kamu punya ✅ — bot: **@MatchInIdBot**, nama tampilan: **MatchIn — Dating & Meetup ⭕️**)
- Akun GitHub (gratis) → https://github.com
- Akun Supabase (gratis) → https://supabase.com
- Akun Render (gratis) → https://render.com

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

## 4b. Payment Gateway Otomatis: Duitku (default) atau Tripay

Bot ini bisa mengaktifkan VIP **otomatis** (tanpa admin approve manual) lewat payment
gateway lokal (QRIS). Ada 2 pilihan yang sudah disiapkan kodenya — tinggal aktifkan salah
satu lewat env var `PAYMENT_GATEWAY`:

### Opsi A — Duitku (default, disarankan kalau Tripay lagi tutup pendaftaran)
1. Buka https://passport.duitku.com/merchant/Project → daftar/login → **buat project baru**.
2. Pilih environment **Sandbox** dulu untuk testing (instan, tanpa verifikasi lama).
3. Setelah project dibuat, akan muncul `Merchant Code` dan `API Key` — catat keduanya.
4. Set di environment variable: `PAYMENT_GATEWAY=duitku`, `DUITKU_MODE=sandbox`,
   `DUITKU_MERCHANT_CODE`, `DUITKU_API_KEY`.
5. Kalau sudah siap terima uang asli: buat project baru dengan environment **Production**
   (butuh verifikasi data usaha/pribadi), lalu ganti `DUITKU_MODE=production` + kredensial baru.

### Opsi B — Tripay (aktifkan lagi kalau pendaftaran mereka sudah dibuka)
1. Daftar di https://tripay.co.id, ambil kredensial sandbox di menu
   **API & Integrasi → Simulator → Merchant → Detail** (`Merchant Code`, `API Key`, `Private Key`).
   Aktifkan channel QRIS di menu yang sama.
2. Set di environment variable: `PAYMENT_GATEWAY=tripay`, `TRIPAY_MODE=sandbox`,
   `TRIPAY_MERCHANT_CODE`, `TRIPAY_API_KEY`, `TRIPAY_PRIVATE_KEY`.
3. Setelah akun disetujui mode Production: ambil kredensial production di
   **Merchant → Opsi → Edit**, aktifkan channel QRIS di **Merchant → Opsi → Atur Channel Pembayaran**,
   lalu ganti `TRIPAY_MODE=production` + kredensial baru.

**Kamu cukup isi kredensial untuk SATU provider** (sesuai `PAYMENT_GATEWAY` yang dipilih) —
kredensial provider yang tidak dipakai boleh dikosongkan.

### Webhook vs polling — kenapa perlu Web Service

Bot ini jalan dengan **polling** (bot yang aktif "nanya" ke Telegram terus-menerus, bukan
Telegram yang kirim ke bot). Itu cukup untuk chat Telegram, tapi **payment gateway (Duitku/Tripay)
perlu mengirim notifikasi (webhook/callback) ke sebuah URL HTTP publik** setiap kali status
pembayaran berubah — ini beda mekanisme dan butuh port terbuka.

Karena itu, `bot.py` sekarang menjalankan **dua hal sekaligus** dalam satu proses:
- polling ke Telegram (seperti biasa), dan
- server HTTP kecil (`webhook.py`) yang mendengarkan di endpoint callback — otomatis jadi
  `/duitku/callback` atau `/tripay/callback` tergantung `PAYMENT_GATEWAY` yang kamu pilih.

Konsekuensinya: saat deploy, service type di Render harus **Web Service** (bukan Background Worker),
supaya Render kasih port publik & domain (`https://nama-app-kamu.onrender.com`) untuk endpoint itu.

## 5. Deploy ke Render (Gratis, pengganti Koyeb)

> Koyeb sudah menutup pendaftaran free tier untuk user baru, jadi panduan ini pakai
> **Render** sebagai gantinya — alurnya paling mirip Koyeb (hubungkan GitHub lewat web UI,
> tanpa perlu install CLI apa pun).

1. Login ke https://dashboard.render.com (bisa daftar pakai akun GitHub langsung, tidak wajib kartu kredit) → **New +** → **Web Service**.
2. Pilih **Build and deploy from a Git repository** → hubungkan akun GitHub kamu → pilih repo `matchin-bot` (atau nama repo yang tadi kamu push).
3. Isi konfigurasi service:
   - **Name**: bebas, misal `matchin-bot`.
   - **Region**: pilih yang terdekat (Singapore).
   - **Branch**: `main`.
   - **Runtime**: `Python 3`.
   - **Build Command**: `pip install -r requirements.txt`.
   - **Start Command**: `python bot.py` (sama seperti isi `Procfile`).
4. **Instance Type**: pilih **Free**.
5. Di bagian **Environment Variables**, tambahkan satu-satu (klik **Add Environment Variable**):
   - `BOT_TOKEN` = token bot kamu
   - `DATABASE_URL` = connection string Supabase
   - `ADMIN_GROUP_ID` = id grup admin
   - `ADMIN_USER_IDS` = user id admin (pisah koma jika lebih dari satu)
   - `PAYMENT_GATEWAY` = `duitku` atau `tripay`
   - Kredensial provider yang kamu pilih (lihat bagian 4b): `DUITKU_MODE` + `DUITKU_MERCHANT_CODE` +
     `DUITKU_API_KEY`, ATAU `TRIPAY_MODE` + `TRIPAY_MERCHANT_CODE` + `TRIPAY_API_KEY` + `TRIPAY_PRIVATE_KEY`
   - `PORT` = `8000` (Render biasanya auto-set `PORT` sendiri, tapi aman untuk isi manual juga)
   - `PUBLIC_BASE_URL` = **isi setelah deploy pertama kali jadi & dapat URL Render** (lihat langkah 7)
6. Klik **Create Web Service**. Tunggu build & deploy selesai (~2-3 menit), status akan menjadi **Live**.
   Render akan kasih kamu URL publik, misalnya `https://matchin-bot-namakamu.onrender.com`.
7. **Set `PUBLIC_BASE_URL`**: buka tab **Environment**, edit `PUBLIC_BASE_URL` dengan URL di atas,
   simpan — Render otomatis redeploy.
8. **Daftarkan URL callback di dashboard provider yang kamu pakai**:
   - Duitku: menu project di https://passport.duitku.com/merchant/Project → isi kolom **Callback URL**
     dengan `https://matchin-bot-namakamu.onrender.com/duitku/callback`.
   - Tripay: menu **Merchant → Opsi** (production) atau **Simulator → Merchant → Detail** (sandbox) →
     isi kolom **URL Callback** dengan `https://matchin-bot-namakamu.onrender.com/tripay/callback`.
9. Cek log di tab **Logs** Render — kalau muncul log polling aktif + `Webhook server jalan di port 8000, path callback: ...` tanpa error, bot sudah online dan siap terima pembayaran otomatis.

### ⚠️ Catatan penting: free tier Render "tidur" kalau tidak ada traffic

Berbeda dari Koyeb, **Free Web Service di Render otomatis sleep setelah ~15 menit tanpa ada
request HTTP masuk**. Untuk bot yang jalan dengan polling (perlu terus aktif ngobrol ke Telegram),
ini masalah karena proses berhenti total saat sleep. Solusinya: pasang **keep-alive ping**
gratis yang mem-ping endpoint `/` (health check) tiap 5-10 menit, misalnya pakai:

- https://cron-job.org (gratis, tinggal daftar & isi URL `https://matchin-bot-namakamu.onrender.com/`, interval 5 menit), atau
- https://uptimerobot.com (gratis, monitor HTTP tiap 5 menit sekaligus dapat notifikasi kalau bot down).

Dengan ping rutin ini, service tidak akan pernah idle cukup lama untuk sleep, jadi bot tetap
online 24/7 walau di free tier.

**Alternatif tanpa perlu keep-alive** (kalau mau yang benar-benar tidak pernah sleep dan tidak
keberatan menghubungkan kartu untuk verifikasi, tanpa ditagih selama masih dalam batas gratis):
**Fly.io** — 3 VM kecil gratis, tidak ada sleep. Perlu install `flyctl` CLI dan jalankan
`fly launch` di folder project (auto-detect Python), lalu `fly secrets set BOT_TOKEN=... DATABASE_URL=... dst` untuk env var, dan `fly deploy`. Beri tahu saya kalau kamu mau panduan lengkap versi Fly.io ini.

---

## 6. Testing Alur Lengkap

1. **Onboarding**: `/start` di bot → pilih bahasa → gender → preferensi → isi nama/umur/kota/bio → upload foto → kirim video note verifikasi.
2. **Verifikasi admin**: video note otomatis terkirim ke grup admin dengan tombol ✅/❌. Klik salah satu untuk approve/reject.
3. **Swipe**: setelah profil complete, ketik `/swipe` atau tombol "🔍 Mulai Cari Pasangan" untuk melihat profil lain (butuh minimal 2 akun berbeda dengan lokasi & preferensi yang cocok untuk testing).
4. **Like/Match**: like dua akun satu sama lain → otomatis dapat notifikasi match + kontak.
5. **VIP (otomatis via Duitku/Tripay)**: `/vip` → pilih paket → bot kirim tombol "💳 Bayar Sekarang" →
   di mode **sandbox** kamu bisa "bayar" tanpa uang asli di halaman simulator provider → begitu callback
   `PAID` masuk, VIP aktif otomatis & user dapat notifikasi, tanpa admin perlu klik apa-apa.
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
├── Procfile                      # perintah run untuk Render (dan platform lain yang baca Procfile)
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

Selamat mencoba! Kalau ada error saat deploy, cek tab **Logs** di Render — biasanya karena environment variable belum lengkap atau format `DATABASE_URL` salah.
