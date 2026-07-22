import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import BOT_TOKEN, ADMIN_GROUP_ID
import database as db
import webhook
from handlers import onboarding, matching, admin, vip, profile, verification

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN belum diset di environment variable / file .env")

    await db.init_pool()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Command untuk user biasa (ditampilkan di semua chat, kecuali grup admin)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🏠 Menu utama"),
            BotCommand(command="swipe", description="🔍 Cari & lihat profil baru"),
            BotCommand(command="profil", description="👤 Lihat & ubah profil kamu"),
            BotCommand(command="vip", description="💎 Upgrade VIP"),
            BotCommand(command="referral", description="🔗 Ajak teman, dapat VIP gratis"),
            BotCommand(command="pause", description="⏸ Sembunyikan/aktifkan profil"),
        ],
        scope=BotCommandScopeDefault(),
    )

    # Command khusus grup admin: bot di grup ini TIDAK berperan sebagai bot dating biasa,
    # jadi command yang tampil di grup pun hanya command admin.
    if ADMIN_GROUP_ID:
        await bot.set_my_commands(
            [
                BotCommand(command="stats", description="📊 Statistik pendaftar"),
                BotCommand(command="users", description="👥 Daftar user terdaftar"),
                BotCommand(command="accbayar", description="✅ ACC pembayaran VIP (fallback jika tombol error)"),
                BotCommand(command="tolakbayar", description="❌ Tolak pembayaran VIP (fallback jika tombol error)"),
                BotCommand(command="accverif", description="✅ ACC verifikasi akun (fallback jika tombol error)"),
                BotCommand(command="tolakverif", description="❌ Tolak verifikasi akun (fallback jika tombol error)"),
                BotCommand(command="hapususer", description="🗑 Hapus user dari bot (permanen)"),
            ],
            scope=BotCommandScopeChat(chat_id=ADMIN_GROUP_ID),
        )

    # Urutan penting: admin duluan supaya command/callback admin selalu diproses.
    # Router selain admin di-filter supaya TIDAK aktif di dalam grup admin —
    # grup itu khusus untuk approve/reject VIP & verifikasi, bukan alur bot untuk user biasa.
    if ADMIN_GROUP_ID:
        not_admin_group = F.chat.id != ADMIN_GROUP_ID
        for r in (onboarding.router, verification.router, vip.router, profile.router, matching.router):
            r.message.filter(not_admin_group)
            r.callback_query.filter(F.message.chat.id != ADMIN_GROUP_ID)

    dp.include_router(admin.router)
    dp.include_router(onboarding.router)
    dp.include_router(verification.router)
    dp.include_router(vip.router)
    dp.include_router(profile.router)
    dp.include_router(matching.router)

    runner = await webhook.run_webhook_server(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
