from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(admin=False, superadmin=False):
    rows = [
        [InlineKeyboardButton("📋 Сервисы", callback_data="services")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("📊 Моя заявка", callback_data="my_request")],
    ]
    if admin:
        rows.append([InlineKeyboardButton("🛠 Админка", callback_data="admin")])
    return InlineKeyboardMarkup(rows)

def services_keyboard(services):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"{r['name']} — ${r['price']:.2f}", callback_data=f"service:{r['id']}")] for r in services]
    )

def admin_services_keyboard(services):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"📥 {r['name']} — ${r['price']:.2f}", callback_data=f"queue:{r['id']}")] for r in services]
        + [[InlineKeyboardButton("📨 Проверка кодов", callback_data="reviews")]]
    )

def review_keyboard(request_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Засчитать", callback_data=f"approve:{request_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{request_id}")
    ]])
