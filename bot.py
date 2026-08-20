from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config import BOT_TOKEN
from database import init_db
from handlers import *


def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =========================
    # КОМАНДЫ
    # =========================

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("take", take_cmd)
    )

    app.add_handler(
        CommandHandler("add", add_cmd)
    )

    app.add_handler(
        CommandHandler("del", del_cmd)
    )

    app.add_handler(
        CommandHandler("list", list_cmd)
    )

    app.add_handler(
        CommandHandler("addadmin", addadmin_cmd)
    )

    app.add_handler(
        CommandHandler("deladmin", deladmin_cmd)
    )


    # =========================
    # ПОЛЬЗОВАТЕЛЬ
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            services,
            pattern=r"^services$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            choose_service,
            pattern=r"^service:\d+$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            balance,
            pattern=r"^balance$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            my_request,
            pattern=r"^my_requests$"
        )
    )


    # =========================
    # АДМИНКА
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            admin_panel,
            pattern=r"^admin$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            queue,
            pattern=r"^queue:\d+$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            take_callback,
            pattern=r"^take:\d+$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            reviews,
            pattern=r"^reviews$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            review,
            pattern=r"^(approve|reject):\d+$"
        )
    )


    # =========================
    # ОЧИСТКА ОЧЕРЕДИ
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            clear_queue_confirm,
            pattern=r"^clear_queue_confirm$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            clear_queue_callback,
            pattern=r"^clear_queue$"
        )
    )


    # =========================
    # ПАНЕЛЬ ВЛАДЕЛЬЦА
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            owner_panel,
            pattern=r"^owner$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            statistics,
            pattern=r"^statistics$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_services,
            pattern=r"^owner_services$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            add_service_start,
            pattern=r"^add_service$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_admins,
            pattern=r"^owner_admins$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            add_admin_start,
            pattern=r"^add_admin$"
        )
    )


    # =========================
    # НАЗАД
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            admin_panel,
            pattern=r"^back_main$"
        )
    )


    # =========================
    # ТЕКСТ
    # =========================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_input
        )
    )


    print("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()
