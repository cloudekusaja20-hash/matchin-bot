import asyncpg
from datetime import datetime, timedelta
from config import DATABASE_URL, FREE_DAILY_LIKES

pool: asyncpg.Pool | None = None


async def init_pool():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return pool


async def close_pool():
    if pool:
        await pool.close()


# ---------- USERS ----------

async def get_user(user_id: int):
    async with pool.acquire() as con:
        return await con.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)


async def create_user_if_not_exists(user_id: int, username: str | None, referred_by: int | None = None):
    async with pool.acquire() as con:
        existing = await con.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if existing:
            return False
        await con.execute(
            """INSERT INTO users (user_id, username, referred_by) VALUES ($1, $2, $3)""",
            user_id, username, referred_by,
        )
        await con.execute(
            """INSERT INTO user_limits (user_id, daily_likes_left, last_reset)
               VALUES ($1, $2, NOW())""",
            user_id, FREE_DAILY_LIKES,
        )
        if referred_by:
            await con.execute(
                """INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)
                   ON CONFLICT (referred_id) DO NOTHING""",
                referred_by, user_id,
            )
        return True


async def update_user_field(user_id: int, field: str, value):
    allowed = {
        "language", "gender", "target_preference", "location", "name", "age",
        "bio", "photo_id", "is_verified", "is_vip", "vip_expiration",
        "has_used_promo", "is_paused", "hide_username", "profile_complete", "username", "swipe_count",
    }
    if field not in allowed:
        raise ValueError(f"Field {field} tidak diizinkan untuk diupdate")
    async with pool.acquire() as con:
        await con.execute(f"UPDATE users SET {field}=$1 WHERE user_id=$2", value, user_id)


async def count_users(only_complete: bool = False) -> int:
    async with pool.acquire() as con:
        if only_complete:
            return await con.fetchval("SELECT COUNT(*) FROM users WHERE profile_complete=TRUE")
        return await con.fetchval("SELECT COUNT(*) FROM users")


async def count_vip_users() -> int:
    async with pool.acquire() as con:
        return await con.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_vip=TRUE AND (vip_expiration IS NULL OR vip_expiration > NOW())"
        )


async def get_users_page(offset: int = 0, limit: int = 10):
    """Daftar user terbaru dulu (baru daftar di atas), untuk ditampilkan ke admin."""
    async with pool.acquire() as con:
        return await con.fetch(
            """SELECT user_id, username, name, age, location, is_vip, is_verified,
                      profile_complete, created_at
               FROM users ORDER BY created_at DESC OFFSET $1 LIMIT $2""",
            offset, limit,
        )


async def delete_user(user_id: int) -> bool:
    """Hapus user beserta semua data terkait (swipe, match, referral, dsb).
    Permanen, tidak bisa di-undo. Return True kalau user memang ada & dihapus."""
    async with pool.acquire() as con:
        async with con.transaction():
            existing = await con.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
            if not existing:
                return False
            await con.execute("DELETE FROM swipes WHERE swiper_id=$1 OR target_id=$1", user_id)
            await con.execute("DELETE FROM matches WHERE user1_id=$1 OR user2_id=$1", user_id)
            await con.execute("DELETE FROM referrals WHERE referrer_id=$1 OR referred_id=$1", user_id)
            await con.execute("DELETE FROM user_limits WHERE user_id=$1", user_id)
            await con.execute("DELETE FROM pending_verifications WHERE user_id=$1", user_id)
            await con.execute("DELETE FROM pending_payments WHERE user_id=$1", user_id)
            await con.execute("DELETE FROM reports WHERE reporter_id=$1 OR reported_id=$1", user_id)
            await con.execute("UPDATE users SET referred_by=NULL WHERE referred_by=$1", user_id)
            await con.execute("DELETE FROM users WHERE user_id=$1", user_id)
            return True


# ---------- QUOTA ----------

async def reset_quota_if_needed(user_id: int):
    async with pool.acquire() as con:
        row = await con.fetchrow("SELECT * FROM user_limits WHERE user_id=$1", user_id)
        if row is None:
            await con.execute(
                "INSERT INTO user_limits (user_id, daily_likes_left, last_reset) VALUES ($1,$2,NOW())",
                user_id, FREE_DAILY_LIKES,
            )
            return
        if datetime.utcnow() - row["last_reset"] >= timedelta(hours=24):
            await con.execute(
                "UPDATE user_limits SET daily_likes_left=$1, last_reset=NOW() WHERE user_id=$2",
                FREE_DAILY_LIKES, user_id,
            )


async def get_likes_left(user_id: int) -> int:
    await reset_quota_if_needed(user_id)
    async with pool.acquire() as con:
        row = await con.fetchrow("SELECT daily_likes_left FROM user_limits WHERE user_id=$1", user_id)
        return row["daily_likes_left"] if row else FREE_DAILY_LIKES


async def decrement_likes(user_id: int):
    async with pool.acquire() as con:
        await con.execute(
            "UPDATE user_limits SET daily_likes_left = GREATEST(daily_likes_left - 1, 0) WHERE user_id=$1",
            user_id,
        )


# ---------- MATCHING ----------

async def get_next_profile(user_id: int, gender: str, target_preference: str, location: str):
    """Ambil satu kandidat profil yang belum pernah di-swipe oleh user_id."""
    async with pool.acquire() as con:
        gender_filter = ""
        params = [user_id, location]
        if target_preference != "both":
            gender_filter = "AND u.gender = $3"
            params.append(target_preference)

        query = f"""
            SELECT u.* FROM users u
            WHERE u.user_id != $1
              AND u.is_paused = FALSE
              AND u.profile_complete = TRUE
              AND u.location = $2
              AND (u.target_preference = $%d OR u.target_preference = 'both')
              {gender_filter}
              AND NOT EXISTS (
                  SELECT 1 FROM swipes s WHERE s.swiper_id = $1 AND s.target_id = u.user_id
              )
            ORDER BY RANDOM()
            LIMIT 1
        """ % (len(params) + 1)
        params.append(gender)
        return await con.fetchrow(query, *params)


async def record_swipe(swiper_id: int, target_id: int, action: str, message_type=None, message_content=None):
    async with pool.acquire() as con:
        async with con.transaction():
            row = await con.fetchrow(
                """INSERT INTO swipes (swiper_id, target_id, action, message_type, message_content)
                   VALUES ($1,$2,$3,$4,$5)
                   ON CONFLICT (swiper_id, target_id) DO UPDATE
                   SET action=$3, message_type=$4, message_content=$5, created_at=NOW()
                   RETURNING (xmax = 0) AS inserted""",
                swiper_id, target_id, action, message_type, message_content,
            )
            # Hanya hitung sebagai aksi baru kalau baris ini benar-benar baru (bukan swipe yang diedit ulang)
            if row and row["inserted"]:
                await con.execute(
                    "UPDATE users SET swipe_count = swipe_count + 1 WHERE user_id=$1",
                    swiper_id,
                )


async def check_mutual_like(user_a: int, user_b: int) -> bool:
    """True jika user_b sudah like/like_message ke user_a sebelumnya."""
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """SELECT 1 FROM swipes WHERE swiper_id=$1 AND target_id=$2
               AND action IN ('like','like_message')""",
            user_b, user_a,
        )
        return row is not None


async def create_match(user1: int, user2: int):
    async with pool.acquire() as con:
        existing = await con.fetchrow(
            """SELECT 1 FROM matches WHERE (user1_id=$1 AND user2_id=$2) OR (user1_id=$2 AND user2_id=$1)""",
            user1, user2,
        )
        if existing:
            return
        await con.execute("INSERT INTO matches (user1_id, user2_id) VALUES ($1,$2)", user1, user2)


async def get_last_swipe_target(user_id: int):
    """Untuk fitur rewind: ambil profil terakhir yang di-pass user ini."""
    async with pool.acquire() as con:
        return await con.fetchrow(
            """SELECT * FROM swipes WHERE swiper_id=$1 AND action='pass'
               ORDER BY created_at DESC LIMIT 1""",
            user_id,
        )


async def undo_swipe(swiper_id: int, target_id: int):
    async with pool.acquire() as con:
        async with con.transaction():
            result = await con.execute(
                "DELETE FROM swipes WHERE swiper_id=$1 AND target_id=$2", swiper_id, target_id
            )
            if result and result.endswith(" 1"):
                await con.execute(
                    "UPDATE users SET swipe_count = GREATEST(swipe_count - 1, 0) WHERE user_id=$1",
                    swiper_id,
                )


# ---------- REFERRAL ----------

async def count_referrals(user_id: int) -> int:
    async with pool.acquire() as con:
        row = await con.fetchrow("SELECT COUNT(*) c FROM referrals WHERE referrer_id=$1", user_id)
        return row["c"]


async def grant_vip_days(user_id: int, days: int):
    async with pool.acquire() as con:
        row = await con.fetchrow("SELECT vip_expiration FROM users WHERE user_id=$1", user_id)
        base = row["vip_expiration"] if row and row["vip_expiration"] and row["vip_expiration"] > datetime.utcnow() else datetime.utcnow()
        new_exp = base + timedelta(days=days)
        await con.execute(
            "UPDATE users SET is_vip=TRUE, vip_expiration=$1 WHERE user_id=$2", new_exp, user_id
        )


# ---------- VERIFICATION ----------

async def create_verification_request(user_id: int, video_note_id: str):
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO pending_verifications (user_id, video_note_id) VALUES ($1,$2)
               RETURNING id""",
            user_id, video_note_id,
        )
        return row["id"]


async def set_verification_admin_msg(request_id: int, message_id: int):
    async with pool.acquire() as con:
        await con.execute(
            "UPDATE pending_verifications SET admin_group_message_id=$1 WHERE id=$2",
            message_id, request_id,
        )


async def get_verification_request(request_id: int):
    async with pool.acquire() as con:
        return await con.fetchrow("SELECT * FROM pending_verifications WHERE id=$1", request_id)


async def get_pending_verification(user_id: int):
    """Ambil request verifikasi user yang masih berstatus 'pending' (kalau ada)."""
    async with pool.acquire() as con:
        return await con.fetchrow(
            """SELECT * FROM pending_verifications
               WHERE user_id=$1 AND status='pending'
               ORDER BY created_at DESC LIMIT 1""",
            user_id,
        )


async def set_verification_status(request_id: int, status: str):
    async with pool.acquire() as con:
        await con.execute("UPDATE pending_verifications SET status=$1 WHERE id=$2", status, request_id)


# ---------- PAYMENTS ----------

async def create_payment_request(user_id: int, package: str, proof_photo_id: str):
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO pending_payments (user_id, package, proof_photo_id) VALUES ($1,$2,$3)
               RETURNING id""",
            user_id, package, proof_photo_id,
        )
        return row["id"]


async def set_payment_admin_msg(request_id: int, message_id: int):
    async with pool.acquire() as con:
        await con.execute(
            "UPDATE pending_payments SET admin_group_message_id=$1 WHERE id=$2",
            message_id, request_id,
        )


async def get_payment_request(request_id: int):
    async with pool.acquire() as con:
        return await con.fetchrow("SELECT * FROM pending_payments WHERE id=$1", request_id)


async def set_payment_status(request_id: int, status: str):
    async with pool.acquire() as con:
        await con.execute("UPDATE pending_payments SET status=$1 WHERE id=$2", status, request_id)


# ---------- TRIPAY (pembayaran otomatis) ----------

async def create_tripay_payment_request(
    user_id: int, package: str, merchant_ref: str, amount: int,
    tripay_reference: str, checkout_url: str,
):
    """Simpan transaksi Tripay yang baru dibuat, status awal 'pending'."""
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO pending_payments
                   (user_id, package, status, merchant_ref, tripay_reference, amount, checkout_url)
               VALUES ($1,$2,'pending',$3,$4,$5,$6)
               RETURNING id""",
            user_id, package, merchant_ref, tripay_reference, amount, checkout_url,
        )
        return row["id"]


async def get_payment_by_merchant_ref(merchant_ref: str):
    async with pool.acquire() as con:
        return await con.fetchrow(
            "SELECT * FROM pending_payments WHERE merchant_ref=$1", merchant_ref
        )


async def mark_payment_paid(request_id: int):
    """Tandai transaksi sudah dibayar (dari callback Tripay), sebelum VIP di-grant."""
    async with pool.acquire() as con:
        await con.execute(
            "UPDATE pending_payments SET status='paid' WHERE id=$1 AND status='pending'",
            request_id,
        )


# ---------- REPORTS ----------

async def create_report(reporter_id: int, reported_id: int, reason: str):
    async with pool.acquire() as con:
        await con.execute(
            "INSERT INTO reports (reporter_id, reported_id, reason) VALUES ($1,$2,$3)",
            reporter_id, reported_id, reason,
        )
