from telegram import Update
from telegram.ext import ContextTypes

from database import *
from keyboards import *
from utils import has_admin_access, is_superadmin, parse_price
from config import MIN_WITHDRAWAL


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nВыберите действие:",
        reply_markup=main_menu(
            has_admin_access(uid),
            is_superadmin(uid)
        )
    )


# =========================
# SERVICES
# =========================

async def services(update, context):
    q = update.callback_query
    await q.answer()

    rows = list_services()

    if not rows:
        await q.message.edit_text(
            "📭 Сейчас доступных сервисов нет."
        )
        return

    await q.message.edit_text(
        "📋 Выберите сервис:",
        reply_markup=services_keyboard(rows)
    )


async def choose_service(update, context):
    q = update.callback_query
    await q.answer()

    service_id = int(q.data.split(":")[1])
    service = get_service(service_id)

    if not service:
        await q.message.edit_text(
            "❌ Сервис больше недоступен."
        )
        return

    context.user_data["creating_service"] = service_id

    await q.message.edit_text(
        f"🏪 {service['name']}\n"
        f"💰 Начисление: ${service['price']:.2f}\n\n"
        "📱 Отправьте номер для заявки."
    )


# =========================
# PHONE
# =========================

async def phone_input(update, context):
    service_id = context.user_data.get("creating_service")

    if not service_id:
        return

    phone = update.message.text.strip()

    if len(phone) < 5 or len(phone) > 32:
        await update.message.reply_text(
            "❌ Проверьте номер и отправьте его ещё раз."
        )
        return

    service = get_service(service_id)

    if not service:
        context.user_data.pop("creating_service", None)

        await update.message.reply_text(
            "❌ Сервис больше недоступен."
        )
        return

    active = user_active_requests(update.effective_user.id)

    if active:
        await update.message.reply_text(
            "⚠️ У вас уже есть активная заявка."
        )
        context.user_data.pop("creating_service", None)
        return

    rid = create_request(
        update.effective_user.id,
        service_id,
        phone
    )

    context.user_data.pop("creating_service", None)

    await update.message.reply_text(
        f"✅ Заявка #{rid} создана!\n\n"
        f"🏪 {service['name']}\n"
        f"📱 {phone}\n"
        f"💰 ${service['price']:.2f}\n\n"
        "⏳ Ожидайте администратора."
    )


# =========================
# BALANCE
# =========================

async def balance(update, context):
    q = update.callback_query
    await q.answer()

    b, total = get_balance(q.from_user.id)

    await q.message.edit_text(
        "💰 Баланс\n\n"
        f"Доступно: ${b:.2f}\n"
        f"Всего заработано: ${total:.2f}\n\n"
        f"Минимальный вывод: ${MIN_WITHDRAWAL:.2f}"
    )


# =========================
# MY REQUESTS
# =========================

async def my_request(update, context):
    q = update.callback_query
    await q.answer()

    rows = user_active_requests(q.from_user.id)

    if not rows:
        await q.message.edit_text(
            "📭 Активных заявок нет."
        )
        return

    names = {
        "queued": "⏳ В очереди",
        "taken": "🔄 В работе",
        "pending_review": "🔎 На проверке"
    }

    text = "📊 Ваши заявки:\n\n"

    for r in rows:
        text += (
            f"#{r['id']} — {r['service_name']}\n"
            f"📱 {r['phone']}\n"
            f"{names.get(r['status'], r['status'])}\n\n"
        )

    await q.message.edit_text(text)


# =========================
# ADMIN PANEL
# =========================

async def admin_panel(update, context):
    q = update.callback_query
    await q.answer()

    if not has_admin_access(q.from_user.id):
        await q.message.edit_text("❌ Доступ запрещён.")
        return

    rows = list_services()

    await q.message.edit_text(
        "🛠 Админка\n\n"
        "Выберите сервис:",
        reply_markup=admin_services_keyboard(rows)
    )


# =========================
# SERVICE QUEUE
# =========================

async def queue(update, context):
    q = update.callback_query
    await q.answer()

    if not has_admin_access(q.from_user.id):
        return

    service_id = int(q.data.split(":")[1])

    expire_old_requests()

    service = get_service(service_id)

    if not service:
        await q.message.edit_text("❌ Сервис не найден.")
        return

    rows = queued_for_service(service_id)

    if not rows:
        await q.message.edit_text(
            f"📭 Очередь «{service['name']}» пуста."
        )
        return

    await q.message.edit_text(
        f"📥 Очередь: {service['name']}\n\n"
        f"Заявок: {len(rows)}"
    )

    for r in rows:
        await q.message.reply_text(
            f"📥 Заявка #{r['id']}\n\n"
            f"👤 ID: {r['user_id']}\n"
            f"🏪 {r['service_name']}\n"
            f"📱 {r['phone']}\n"
            f"💰 ${r['service_price']:.2f}",
            reply_markup=take_request_keyboard(r["id"])
        )


# =========================
# TAKE
# =========================

async def take_callback(update, context):
    q = update.callback_query

    if not has_admin_access(q.from_user.id):
        await q.answer(
            "❌ Доступ запрещён.",
            show_alert=True
        )
        return

    await q.answer()

    rid = int(q.data.split(":")[1])

    if not take_request(rid, q.from_user.id):
        await q.answer(
            "❌ Заявка уже взята.",
            show_alert=True
        )
        return

    r = get_request(rid)

    if not r:
        return

    await q.message.edit_reply_markup(None)

    await q.message.reply_text(
        f"✅ Заявка #{rid} взята.\n\n"
        f"🏪 {r['service_name']}\n"
        f"📱 {r['phone']}"
    )

    try:
        await context.bot.send_message(
            r["user_id"],
            f"📱 Ваша заявка #{rid} взята администратором.\n\n"
            "Ожидайте дальнейших инструкций."
        )
    except Exception:
        pass


# =========================
# REVIEWS
# =========================

async def reviews(update, context):
    q = update.callback_query
    await q.answer()

    if not has_admin_access(q.from_user.id):
        return

    rows = get_pending_reviews()

    if not rows:
        await q.message.edit_text(
            "📭 Заявок на проверке нет."
        )
        return

    await q.message.edit_text(
        f"🔎 На проверке: {len(rows)}"
    )

    for r in rows:
        await q.message.reply_text(
            f"📨 Заявка #{r['id']}\n\n"
            f"👤 ID: {r['user_id']}\n"
            f"🏪 {r['service_name']}\n"
            f"📱 {r['phone']}\n"
            f"💰 ${r['price']:.2f}",
            reply_markup=review_keyboard(r["id"])
        )


# =========================
# REVIEW ACTION
# =========================

async def review(update, context):
    q = update.callback_query

    if not has_admin_access(q.from_user.id):
        await q.answer(
            "❌ Доступ запрещён.",
            show_alert=True
        )
        return

    await q.answer()

    action, rid = q.data.split(":")
    rid = int(rid)

    result = review_request(
        rid,
        q.from_user.id,
        action == "approve"
    )

    if not result:
        await q.message.edit_text(
            "❌ Заявка уже обработана."
        )
        return

    if action == "approve":
        await q.message.edit_text(
            f"✅ Заявка #{rid} подтверждена.\n\n"
            f"💰 Начислено: ${result['price']:.2f}"
        )

        text = (
            f"✅ Заявка #{rid} подтверждена!\n\n"
            f"💰 Начислено: ${result['price']:.2f}"
        )

    else:
        await q.message.edit_text(
            f"❌ Заявка #{rid} отклонена."
        )

        text = (
            f"❌ Заявка #{rid} отклонена.\n\n"
            "Начисление не произведено."
        )

    try:
        await context.bot.send_message(
            result["user_id"],
            text
        )
    except Exception:
        pass


# =========================
# CLEAR QUEUE
# =========================

async def clear_queue_confirm(update, context):
    q = update.callback_query
    await q.answer()

    if not has_admin_access(q.from_user.id):
        return

    await q.message.edit_text(
        "⚠️ Вы уверены?\n\n"
        "Все заявки во всех очередях будут отменены.",
        reply_markup=clear_queue_keyboard()
    )


async def clear_queue_callback(update, context):
    q = update.callback_query
    await q.answer()

    if not has_admin_access(q.from_user.id):
        return

    count = clear_queue()

    await q.message.edit_text(
        f"🗑 Очередь очищена.\n\n"
        f"Отменено заявок: {count}"
    )


# =========================
# OWNER
# =========================

async def owner_panel(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.edit_text(
            "❌ Только владелец."
        )
        return

    await q.message.edit_text(
        "👑 Панель владельца\n\n"
        "Выберите действие:",
        reply_markup=owner_panel_keyboard()
    )


async def statistics(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        return

    s = get_statistics()

    await q.message.edit_text(
        "📊 Статистика\n\n"
        f"👤 Пользователей: {s['users']}\n"
        f"📥 Всего заявок: {s['total']}\n"
        f"⏳ В очереди: {s['queued']}\n"
        f"🔄 В работе: {s['taken']}\n"
        f"🔎 На проверке: {s['pending']}\n"
        f"✅ Выполнено: {s['approved']}\n"
        f"❌ Отклонено: {s['rejected']}\n"
        f"⌛ Истекло: {s['expired']}\n\n"
        f"💰 Начислено: ${s['paid']:.2f}",
        reply_markup=back_keyboard("owner")
    )


# =========================
# OWNER SERVICES
# =========================

async def owner_services(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        return

    rows = list_services()

    await q.message.edit_text(
        "📋 Управление сервисами:",
        reply_markup=owner_services_keyboard(rows)
    )


async def add_service_start(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        return

    context.user_data["owner_action"] = "add_service_name"

    await q.message.edit_text(
        "➕ Введите название нового сервиса:"
    )


# =========================
# OWNER ADMINS
# =========================

async def owner_admins(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        return

    admins = list_admins()

    await q.message.edit_text(
        "👥 Администраторы:",
        reply_markup=owner_admins_keyboard(admins)
    )


async def add_admin_start(update, context):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        return

    context.user_data["owner_action"] = "add_admin"

    await q.message.edit_text(
        "➕ Отправьте Telegram ID нового администратора:"
    )


# =========================
# TEXT INPUT
# =========================

async def text_input(update, context):

    # Номер заявки
    if context.user_data.get("creating_service"):
        await phone_input(update, context)
        return

    action = context.user_data.get("owner_action")

    # Название сервиса
    if action == "add_service_name":
        name = update.message.text.strip()

        if not name:
            return

        context.user_data["new_service_name"] = name
        context.user_data["owner_action"] = "add_service_price"

        await update.message.reply_text(
            "💰 Отправьте цену сервиса.\n\n"
            "Например: 0.70"
        )
        return

    # Цена сервиса
    if action == "add_service_price":
        try:
            price = parse_price(
                update.message.text.strip()
            )
        except Exception:
            await update.message.reply_text(
                "❌ Неверная цена."
            )
            return

        name = context.user_data.get(
            "new_service_name"
        )

        try:
            sid = add_service(name, price)
        except Exception:
            await update.message.reply_text(
                "❌ Такой сервис уже существует."
            )
            return

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ Сервис добавлен!\n\n"
            f"#{sid} {name}\n"
            f"💰 ${price:.2f}"
        )
        return

    # Добавление администратора
    if action == "add_admin":
        try:
            tg_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Telegram ID должен быть числом."
            )
            return

        add_admin(tg_id)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Администратор добавлен."
        )
        return


# =========================
# COMMANDS
# =========================

async def add_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /add Название 0.70"
        )
        return

    name = " ".join(context.args[:-1])
    price = parse_price(context.args[-1])

    try:
        sid = add_service(name, price)
    except Exception:
        await update.message.reply_text(
            "❌ Такой сервис уже существует."
        )
        return

    await update.message.reply_text(
        f"✅ Сервис добавлен: #{sid} "
        f"{name} — ${price:.2f}"
    )


async def del_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        return

    if not context.args:
        return

    try:
        service_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID должен быть числом."
        )
        return

    ok = delete_service(service_id)

    await update.message.reply_text(
        "✅ Сервис удалён."
        if ok
        else
        "❌ Сервис не найден."
    )


async def list_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        return

    rows = list_services()

    if not rows:
        await update.message.reply_text(
            "📭 Сервисов нет."
        )
        return

    await update.message.reply_text(
        "\n".join(
            f"#{r['id']} — {r['name']} — ${r['price']:.2f}"
            for r in rows
        )
    )


async def addadmin_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        return

    if not context.args:
        return

    try:
        tg_id = int(context.args[0])
    except ValueError:
        return

    add_admin(
        tg_id,
        ""
    )

    await update.message.reply_text(
        "✅ Администратор добавлен."
    )


async def deladmin_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        return

    if not context.args:
        return

    try:
        tg_id = int(context.args[0])
    except ValueError:
        return

    remove_admin(tg_id)

    await update.message.reply_text(
        "✅ Администратор удалён."
    )


async def take_cmd(update, context):
    await update.message.reply_text(
        "📥 Используйте кнопку «Взять заявку» "
        "в очереди."
    )
