from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main_menu(admin=False, superadmin=False):
    rows = [
        [
            InlineKeyboardButton(
                "📋 Сервисы",
                callback_data="services"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Баланс",
                callback_data="balance"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Мои заявки",
                callback_data="my_requests"
            )
        ],
    ]

    if admin:
        rows.append([
            InlineKeyboardButton(
                "🛠 Админка",
                callback_data="admin"
            )
        ])

    if superadmin:
        rows.append([
            InlineKeyboardButton(
                "👑 Панель владельца",
                callback_data="owner"
            )
        ])

    return InlineKeyboardMarkup(rows)


# =========================
# СЕРВИСЫ
# =========================

def services_keyboard(services):
    rows = []

    for service in services:
        rows.append([
            InlineKeyboardButton(
                f"{service['name']} — ${service['price']:.2f}",
                callback_data=f"service:{service['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data="back_main"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================
# АДМИНКА
# =========================

def admin_services_keyboard(services):
    rows = []

    for service in services:
        rows.append([
            InlineKeyboardButton(
                f"📥 {service['name']}",
                callback_data=f"queue:{service['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "📨 Проверка заявок",
            callback_data="reviews"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🗑 Очистить очередь",
            callback_data="clear_queue_confirm"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data="back_main"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================
# КНОПКА ВЗЯТЬ ЗАЯВКУ
# =========================

def take_request_keyboard(request_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📥 Взять заявку",
                callback_data=f"take:{request_id}"
            )
        ]
    ])


# =========================
# ПОДТВЕРЖДЕНИЕ ЗАЯВКИ
# =========================

def review_keyboard(request_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"approve:{request_id}"
            ),
            InlineKeyboardButton(
                "❌ Отклонить",
                callback_data=f"reject:{request_id}"
            )
        ]
    ])


# =========================
# ПОДТВЕРЖДЕНИЕ ОЧИСТКИ
# =========================

def clear_queue_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ Да, очистить",
                callback_data="clear_queue"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Отмена",
                callback_data="admin"
            )
        ]
    ])


# =========================
# ПАНЕЛЬ ВЛАДЕЛЬЦА
# =========================

def owner_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 Статистика",
                callback_data="statistics"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 Сервисы",
                callback_data="owner_services"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Администраторы",
                callback_data="owner_admins"
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Номера",
                callback_data="owner_numbers"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Очистить очередь",
                callback_data="clear_queue_confirm"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="back_main"
            )
        ]
    ])


# =========================
# УПРАВЛЕНИЕ СЕРВИСАМИ
# =========================

def owner_services_keyboard(services):
    rows = []

    for service in services:
        rows.append([
            InlineKeyboardButton(
                f"⚙️ {service['name']} — ${service['price']:.2f}",
                callback_data=f"edit_service:{service['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "➕ Добавить сервис",
            callback_data="add_service"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data="owner"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================
# ДЕЙСТВИЯ С СЕРВИСОМ
# =========================

def service_manage_keyboard(service_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✏️ Изменить цену",
                callback_data=f"price:{service_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Удалить сервис",
                callback_data=f"delete_service:{service_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="owner_services"
            )
        ]
    ])


# =========================
# АДМИНИСТРАТОРЫ ВЛАДЕЛЬЦА
# =========================

def owner_admins_keyboard(admins):
    rows = []

    for admin in admins:
        username = admin["username"] or str(admin["tg_id"])

        rows.append([
            InlineKeyboardButton(
                f"👤 {username}",
                callback_data=f"remove_admin:{admin['tg_id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "➕ Добавить администратора",
            callback_data="add_admin"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data="owner"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================
# НОМЕРА
# =========================

def owner_numbers_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Добавить номер",
                callback_data="add_number"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 Список номеров",
                callback_data="numbers_list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="owner"
            )
        ]
    ])


# =========================
# НАЗАД
# =========================

def back_keyboard(callback="back_main"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data=callback
            )
        ]
    ])
