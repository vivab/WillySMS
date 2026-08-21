from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from config import BOT_TOKEN
from database import init_db
from handlers import *

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in environment")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(confirm_services, pattern=r"^confirm_services$"),
            CallbackQueryHandler(withdraw_start, pattern=r"^withdraw$"),
        ],
        states={
            WAITING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            WAITING_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_main, pattern=r"^back_main$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("del", del_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("deladmin", deladmin_cmd))
    app.add_handler(CommandHandler("pay", pay_cmd))
    app.add_handler(CommandHandler("fail", fail_cmd))
    app.add_handler(CommandHandler("topup", topup_cmd))


    app.add_handler(CallbackQueryHandler(back_main, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(services, pattern=r"^services$"))
    app.add_handler(CallbackQueryHandler(toggle_service, pattern=r"^toggle:\d+$"))
    app.add_handler(CallbackQueryHandler(balance, pattern=r"^balance$"))
    app.add_handler(CallbackQueryHandler(my_requests, pattern=r"^my_requests$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern=r"^admin$"))
    app.add_handler(CallbackQueryHandler(admin_queues, pattern=r"^admin_queues$"))
    app.add_handler(CallbackQueryHandler(show_queue, pattern=r"^queue:\d+$"))
    app.add_handler(CallbackQueryHandler(take_request_cb, pattern=r"^take:\d+$"))
    app.add_handler(CallbackQueryHandler(reviews, pattern=r"^reviews$"))
    app.add_handler(CallbackQueryHandler(review_cb, pattern=r"^(approve|reject):\d+$"))
    app.add_handler(CallbackQueryHandler(superadmin_panel, pattern=r"^superadmin$"))
    app.add_handler(CallbackQueryHandler(sa_stats, pattern=r"^sa_stats$"))
    app.add_handler(CallbackQueryHandler(sa_services, pattern=r"^sa_services$"))
    app.add_handler(CallbackQueryHandler(sa_admins, pattern=r"^sa_admins$"))
    app.add_handler(CallbackQueryHandler(sa_withdrawals, pattern=r"^sa_withdrawals$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

    print("Willy SMS 24/7 bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
