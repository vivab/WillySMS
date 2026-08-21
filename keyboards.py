from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(admin: bool = False, superadmin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📋 Сервисы", callback_data="services")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("📊 Мои заявки", callback_data="my_requests")],
    ]
    if admin or superadmin:
        rows.append([InlineKeyboardButton("🛠 Админка", callback_data="admin")])
    if superadmin:
        rows.append([InlineKeyboardButton("👑 Супер-админ", callback_data="superadmin")])
    return InlineKeyboardMarkup(rows)


def services_select_keyboard(services: list, selected: set) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        mark = "✅" if s["id"] in selected else "⬜"
        rows.append([
            InlineKeyboardButton(
                f"{mark} {s['name']} — ${s['price']:.2f}",
                callback_data=f"toggle:{s['id']}"
            )
        ])
    if selected:
        rows.append([InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_services")])
    rows.append([InlineKeyboardButton("❌ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Очереди по сервисам", callback_data="admin_queues")],
        [InlineKeyboardButton("📨 Коды на проверке", callback_data="reviews")],
        [InlineKeyboardButton("❌ Назад", callback_data="back_main")],
    ])


def admin_queues_keyboard(services: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"📥 {s['name']}", callback_data=f"queue:{s['id']}")]
        for s in services
    ]
    rows.append([InlineKeyboardButton("❌ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def take_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Взять заявку", callback_data=f"take:{request_id}")],
        [InlineKeyboardButton("❌ Назад", callback_data="admin_queues")],
    ])


def review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{request_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{request_id}")
    ]])


def balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton("❌ Назад", callback_data="back_main")],
    ])


def superadmin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="sa_stats")],
        [InlineKeyboardButton("📋 Сервисы", callback_data="sa_services")],
        [InlineKeyboardButton("👥 Админы", callback_data="sa_admins")],
        [InlineKeyboardButton("💳 Выплаты", callback_data="sa_withdrawals")],
        [InlineKeyboardButton("❌ Назад", callback_data="back_main")],
    ])


def back_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Назад", callback_data="back_main")]
    ])
