-- Jalankan seluruh isi file ini di Supabase -> SQL Editor -> New Query -> Run

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    language TEXT DEFAULT 'id',
    gender TEXT,
    target_preference TEXT,
    location TEXT,
    name TEXT,
    age INTEGER,
    bio TEXT,
    photo_id TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_vip BOOLEAN DEFAULT FALSE,
    vip_expiration TIMESTAMP,
    has_used_promo BOOLEAN DEFAULT FALSE,
    referred_by BIGINT,
    is_paused BOOLEAN DEFAULT FALSE,
    hide_username BOOLEAN DEFAULT FALSE,
    profile_complete BOOLEAN DEFAULT FALSE,
    swipe_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Jika tabel users sudah pernah dibuat sebelumnya, jalankan baris ini juga
-- supaya kolom baru ditambahkan tanpa menghapus data yang sudah ada:
ALTER TABLE users ADD COLUMN IF NOT EXISTS swipe_count INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT,
    referred_id BIGINT UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_limits (
    user_id BIGINT PRIMARY KEY,
    daily_likes_left INTEGER DEFAULT 30,
    last_reset TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS swipes (
    id SERIAL PRIMARY KEY,
    swiper_id BIGINT,
    target_id BIGINT,
    action TEXT, -- 'like', 'pass', 'like_message'
    message_type TEXT,
    message_content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(swiper_id, target_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    user1_id BIGINT,
    user2_id BIGINT,
    matched_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pending_verifications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    video_note_id TEXT,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    admin_group_message_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pending_payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    package TEXT,
    proof_photo_id TEXT,
    status TEXT DEFAULT 'pending', -- pending, paid, approved, rejected, failed, expired
    admin_group_message_id BIGINT,
    -- Kolom untuk transaksi otomatis via Tripay (boleh NULL untuk transaksi manual QRIS lama)
    merchant_ref TEXT UNIQUE,
    tripay_reference TEXT,
    amount INTEGER,
    checkout_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pending_payments_merchant_ref ON pending_payments (merchant_ref);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    reporter_id BIGINT,
    reported_id BIGINT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_swipes_swiper ON swipes(swiper_id);
CREATE INDEX IF NOT EXISTS idx_swipes_target ON swipes(target_id);
CREATE INDEX IF NOT EXISTS idx_users_matching ON users(gender, target_preference, location, is_paused);
