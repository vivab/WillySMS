from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import *
from keyboards import *
from utils import has_admin_access, is_superadmin, parse_price, normalize_phone
from config import MIN_WITHDRAWAL, SUPERADMIN_IDS

WAITING_PHONE = 1
WAITING_WITHDRAW_AMOUNT = 2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Добро пожаловать в <b>Willy SMS 24/7</b>!\n\nВыберите действие:",
        reply_markup=main_menu(has_admin_access(uid), is_superadmin(uid)),
        parse_mode="HTML"
    )


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    context.user_data.clear()
    await q.message.edit_text(
        "👋 Добро пожаловать в <b>Willy SMS 24/7</b>!\n\nВыберите действие:",
        reply_markup=main_menu(has_admin_access(uid), is_superadmin(uid)),
        parse_mode="HTML"
    )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["selected"] = set()
    rows = list_services()
    if not rows:
        await q.message.edit_text("Пока нет доступных сервисов.", reply_markup=back_main_keyboard())
        return
    await q.message.edit_text(
        "📋 Выберите один или несколько сервисов:\n(нажмите чтобы отметить ✅)",
        reply_markup=services_select_keyboard(rows, set())
    )


async def toggle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    sid = int(q.data.split(":")[1])
    selected = context.user_data.setdefault("selected", set())
    if sid in selected:
        selected.remove(sid)
    else:
        selected.add(sid)
    rows = list_services()
    await q.message.edit_text(
        "📋 Выберите один или несколько сервисов:\n(нажмите чтобы отметить ✅)",
        reply_markup=services_select_keyboard(rows, selected)
    )


async def confirm_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    selected = context.user_data.get("selected", set())
    if not selected:
        await q.answer("Выберите хотя бы один сервис", show_alert=True)
        return
    context.user_data["pending_services"] = list(selected)
    await q.message.edit_text(
        "📱 Теперь отправьте номер телефона, на который будет приходить SMS.\n\n"
        "Примеры:\n<code>+79867345674</code>\n<code>+7 983 734 62 95</code>\n<code>89837346295</code>\n\n"
        "Просто напишите номер в чат:",
        reply_markup=back_main_keyboard(),
        parse_mode="HTML"
    )
    return WAITING_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text or "")
    if not phone:
        await update.message.reply_text(
            "❌ Некорректный номер. Попробуйте ещё раз.\nПример: <code>+79867345674</code>",
            parse_mode="HTML"
        )
        return WAITING_PHONE

    service_ids = context.user_data.get("pending_services", [])
    if not service_ids:
        await update.message.reply_text("Сессия устарела. Начните заново /start")
        return ConversationHandler.END

    active = user_active_requests(update.effective_user.id)
    if len(active) >= 10:
        await update.message.reply_text("❌ Слишком много активных заявок. Дождитесь обработки.")
        return ConversationHandler.END

    ids = create_requests(update.effective_user.id, service_ids, phone)
    log_action(update.effective_user.id, "create_requests", details=f"ids={ids}, phone={phone}")

    names = []
    total = 0.0
    for sid in service_ids:
        s = get_service(sid)
        if s:
            names.append(s["name"])
            total += s["price"]

    text = (
        f"✅ <b>Заявки успешно созданы!</b>\n\n"
        f"📱 Номер: <code>{phone}</code>\n"
        f"🏷 Сервисы: <b>{', '.join(names)}</b>\n"
        f"💰 Возможное вознаграждение: <b>${total:.2f}</b>\n\n"
        f"🔢 Номера заявок: {', '.join(f'#{i}' for i in ids)}\n\n"
        f"⏳ Ожидайте, пока администратор возьмёт ваш номер в работу."
    )
    context.user_data.clear()
    await update.message.reply_text(
        text,
        reply_markup=main_menu(
            has_admin_access(update.effective_user.id),
            is_superadmin(update.effective_user.id)
        ),
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    b, total = get_balance(q.from_user.id)
    await q.message.edit_text(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"Доступно: <b>${b:.2f}</b>\n"
        f"Всего заработано: <b>${total:.2f}</b>\n"
        f"Минимальный вывод: <b>${MIN_WITHDRAWAL:.2f}</b>",
        reply_markup=balance_keyboard(),
        parse_mode="HTML"
    )


async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    b, _ = get_balance(q.from_user.id)
    if b < MIN_WITHDRAWAL:
        await q.answer(f"Минимум для вывода ${MIN_WITHDRAWAL:.2f}", show_alert=True)
        return
    await q.message.edit_text(
        f"Введите сумму для вывода (от ${MIN_WITHDRAWAL:.2f} до ${b:.2f}):",
        reply_markup=back_main_keyboard()
    )
    return WAITING_WITHDRAW_AMOUNT


async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float((update.message.text or "").replace(",", ".").replace("$", "").strip())
    except ValueError:
        await update.message.reply_text("Введите число, например 5.5")
        return WAITING_WITHDRAW_AMOUNT

    if amount < MIN_WITHDRAWAL:
        await update.message.reply_text(f"Минимум ${MIN_WITHDRAWAL:.2f}")
        return WAITING_WITHDRAW_AMOUNT

    wd_id = reserve_withdrawal(update.effective_user.id, amount)
    if not wd_id:
        await update.message.reply_text("❌ Недостаточно средств или ошибка.")
        return ConversationHandler.END

    log_action(update.effective_user.id, "create_withdrawal", details=f"id={wd_id}, amount={amount}")

    for sa in SUPERADMIN_IDS:
        try:
            await context.bot.send_message(
                sa,
                f"💳 <b>Новая заявка на вывод #{wd_id}</b>\n"
                f"Пользователь: <code>{update.effective_user.id}</code>\n"
                f"Сумма: <b>${amount:.2f}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Заявка на вывод <b>#{wd_id}</b> создана.\n"
        f"Сумма <b>${amount:.2f}</b> зарезервирована.\n"
        f"Ожидайте обработки.",
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def my_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rows = user_active_requests(q.from_user.id)
    if not rows:
        await q.message.edit_text("📭 Активных заявок нет.", reply_markup=back_main_keyboard())
        return

    status_map = {
        "queued": "⏳ В очереди",
        "taken": "📩 Взят, ожидается код",
        "pending_review": "🔎 Код на проверке",
    }
    text = "📊 <b>Ваши активные заявки:</b>\n\n"
    for r in rows:
        text += (
            f"<b>#{r['id']}</b> | {r['service_name']}\n"
            f"Номер: <code>{r['phone']}</code>\n"
            f"Статус: {status_map.get(r['status'], r['status'])}\n"
            f"————————————\n"
        )
    await q.message.edit_text(text, reply_markup=back_main_keyboard(), parse_mode="HTML")


async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not (2 <= len(text) <= 10):
        return

    active = user_active_requests(update.effective_user.id)
    target = None
    for r in active:
        if r["status"] == "taken":
            target = r
            break

    if not target:
        return

    if not submit_code(target["id"], update.effective_user.id, text):
        await update.message.reply_text("❌ Не удалось сохранить код.")
        return

    log_action(update.effective_user.id, "send_code", target["id"], text)

    await update.message.reply_text(
        "✅ <b>Код принят!</b>\n\n"
        "Он отправлен администратору на проверку.\n"
        "Ожидайте результата ⏳",
        parse_mode="HTML"
    )

    notify_text = (
        f"📨 <b>Код по номеру {target['phone']} получен!</b>\n\n"
        f"🔹 Заявка: <b>#{target['id']}</b>\n"
        f"🔹 Сервис: <b>{target['service_name']}</b>\n"
        f"🔹 Код: <code>{text}</code>\n"
        f"🔹 Сумма: <b>${target['service_price']:.2f}</b>\n\n"
        f"Проверьте и зачислите или отклоните:"
    )
    markup = review_keyboard(target["id"])

    notified = set()
    if target["admin_id"]:
        try:
            await context.bot.send_message(target["admin_id"], notify_text, reply_markup=markup, parse_mode="HTML")
            notified.add(target["admin_id"])
        except Exception:
            pass

    for a in list_admins():
        if a["tg_id"] not in notified:
            try:
                await context.bot.send_message(a["tg_id"], notify_text, reply_markup=markup, parse_mode="HTML")
                notified.add(a["tg_id"])
            except Exception:
                pass
    for sa in SUPERADMIN_IDS:
        if sa not in notified:
            try:
                await context.bot.send_message(sa, notify_text, reply_markup=markup, parse_mode="HTML")
            except Exception:
                pass


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        await q.answer("Нет доступа", show_alert=True)
        return
    await q.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=admin_menu(), parse_mode="HTML")


async def admin_queues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        return
    services = list_services()
    if not services:
        await q.message.edit_text("Нет сервисов.", reply_markup=admin_menu())
        return
    await q.message.edit_text(
        "📥 Выберите сервис (отдельная очередь):",
        reply_markup=admin_queues_keyboard(services)
    )


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        return
    service_id = int(q.data.split(":")[1])
    service = get_service(service_id)
    rows = queued_for_service(service_id)

    if not rows:
        await q.message.edit_text(
            f"📭 Очередь «{service['name'] if service else '?'}» пуста.",
            reply_markup=admin_queues_keyboard(list_services())
        )
        return

    r = rows[0]
    text = (
        f"📥 <b>{r['service_name']}</b>\n\n"
        f"Заявка <b>#{r['id']}</b>\n"
        f"Пользователь: <code>{r['user_id']}</code>\n"
        f"Номер: <code>{r['phone']}</code>\n"
        f"Цена: <b>${r['service_price']:.2f}</b>\n"
        f"В очереди ещё: {len(rows) - 1}"
    )
    await q.message.edit_text(text, reply_markup=take_keyboard(r["id"]), parse_mode="HTML")


async def take_request_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        return

    rid = int(q.data.split(":")[1])
    if not take_request(rid, q.from_user.id):
        await q.answer("❌ Заявка уже взята другим администратором.", show_alert=True)
        return

    r = get_request(rid)
    await q.message.edit_text(
        f"✅ Вы взяли заявку <b>#{rid}</b>\n"
        f"Сервис: <b>{r['service_name']}</b>\n"
        f"Номер: <code>{r['phone']}</code>\n"
        f"Пользователь: <code>{r['user_id']}</code>\n\n"
        f"Ожидайте код от пользователя.",
        parse_mode="HTML"
    )

    try:
        await context.bot.send_message(
            r["user_id"],
            f"📨 <b>Ваш номер взят в работу!</b>\n\n"
            f"📱 Номер: <code>{r['phone']}</code>\n"
            f"🏷 Сервис: <b>{r['service_name']}</b>\n"
            f"🔢 Заявка: <b>#{rid}</b>\n\n"
            f"💻 Введите <b>ответом</b> на это сообщение код, который вам пришёл.\n"
            f"<i>(от 2 до 10 символов)</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        return
    rows = get_pending_reviews()
    if not rows:
        await q.message.edit_text("📭 Кодов на проверке нет.", reply_markup=admin_menu())
        return

    for r in rows:
        await q.message.reply_text(
            f"📨 <b>Заявка #{r['id']}</b>\n"
            f"Сервис: <b>{r['service_name']}</b>\n"
            f"Номер: <code>{r['phone']}</code>\n"
            f"Код: <code>{r['code']}</code>\n"
            f"Сумма: <b>${r['service_price']:.2f}</b>",
            reply_markup=review_keyboard(r["id"]),
            parse_mode="HTML"
        )


async def review_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not has_admin_access(q.from_user.id):
        return

    action, rid_str = q.data.split(":")
    rid = int(rid_str)
    result = review_request(rid, q.from_user.id, action == "approve")

    if not result:
        await q.answer("❌ Заявка уже обработана.", show_alert=True)
        return

    if action == "approve":
        await q.message.edit_text(f"✅ Заявка #{rid} подтверждена.\nНачислено: ${result['price']:.2f}")
        user_msg = (
            f"✅ <b>Код подтверждён!</b>\n\n"
            f"Заявка: <b>#{rid}</b>\n"
            f"💰 Начислено: <b>${result['price']:.2f}</b>\n\n"
            f"Спасибо за работу! 🎉"
        )
    else:
        await q.message.edit_text(f"❌ Заявка #{rid} отклонена.")
        user_msg = (
            f"❌ <b>Код отклонён</b>\n\n"
            f"Заявка: <b>#{rid}</b>\n"
            f"Начисление не произведено."
        )

    try:
        await context.bot.send_message(result["user_id"], user_msg, parse_mode="HTML")
    except Exception:
        pass


async def superadmin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_superadmin(q.from_user.id):
        await q.answer("Нет доступа", show_alert=True)
        return
    await q.message.edit_text("👑 <b>Супер-админ панель</b>", reply_markup=superadmin_menu(), parse_mode="HTML")


async def sa_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_superadmin(q.from_user.id):
        return
    s = get_stats()
    text = (
        f"📊 <b>Статистика Willy SMS 24/7</b>\n\n"
        f"👥 Пользователей: <b>{s['users']}</b>\n"
        f"🏷 Активных сервисов: <b>{s['services']}</b>\n"
        f"🛡 Админов: <b>{s['admins']}</b>\n\n"
        f"📥 Всего заявок: <b>{s['total_requests']}</b>\n"
        f"⏳ В очереди: <b>{s['queued']}</b>\n"
        f"📱 Взято: <b>{s['taken']}</b>\n"
        f"🔎 На проверке: <b>{s['pending']}</b>\n"
        f"✅ Подтверждено: <b>{s['approved']}</b>\n"
        f"❌ Отклонено: <b>{s['rejected']}</b>\n\n"
        f"💰 Всего заработано юзерами: <b>${s['total_earned']:.2f}</b>\n"
        f"💳 На балансах сейчас: <b>${s['total_balance']:.2f}</b>\n\n"
        f"💸 Выплаты в ожидании: <b>{s['pending_wd_count']}</b> на ${s['pending_wd_sum']:.2f}\n"
        f"✅ Выплачено: <b>{s['paid_wd_count']}</b> на ${s['paid_wd_sum']:.2f}\n"
    )
    if s["top_services"]:
        text += "\n🏆 <b>Топ сервисов:</b>\n"
        for name, cnt, earned in s["top_services"]:
            text += f"• {name}: {cnt} заявок (${earned:.2f})\n"
    await q.message.edit_text(text, reply_markup=superadmin_menu(), parse_mode="HTML")


async def sa_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_superadmin(q.from_user.id):
        return
    rows = list_services()
    text = "📋 <b>Сервисы:</b>\n\n"
    if not rows:
        text += "Пусто"
    else:
        for r in rows:
            text += f"#{r['id']} — {r['name']} — ${r['price']:.2f}\n"
    text += "\nКоманды:\n/add Название цена\n/del ID\n/list"
    await q.message.edit_text(text, reply_markup=superadmin_menu(), parse_mode="HTML")


async def sa_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_superadmin(q.from_user.id):
        return
    rows = list_admins()
    text = "👥 <b>Администраторы:</b>\n\n"
    if not rows:
        text += "Пусто\n"
    else:
        for r in rows:
            text += f"• <code>{r['tg_id']}</code> (@{r['username'] or '—'})\n"
    text += "\nКоманды:\n/addadmin ID\n/deladmin ID"
    await q.message.edit_text(text, reply_markup=superadmin_menu(), parse_mode="HTML")


async def sa_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_superadmin(q.from_user.id):
        return
    rows = get_pending_withdrawals()
    text = "💳 <b>Ожидающие выплаты:</b>\n\n"
    if not rows:
        text += "Нет"
    else:
        for r in rows:
            text += f"#{r['id']} | user <code>{r['user_id']}</code> | ${r['amount']:.2f}\n"
    text += "\nКоманды:\n/pay ID — выплатить\n/fail ID — отклонить и вернуть"
    await q.message.edit_text(text, reply_markup=superadmin_menu(), parse_mode="HTML")


async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /add Самокат 0.5")
        return
    name = " ".join(context.args[:-1])
    try:
        price = parse_price(context.args[-1])
        sid = add_service(name, price)
        log_action(update.effective_user.id, "add_service", details=f"{sid}:{name}:{price}")
        await update.message.reply_text(f"✅ Сервис добавлен: #{sid} {name} — ${price:.2f}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Использование: /del ID")
        return
    ok = delete_service(int(context.args[0]))
    await update.message.reply_text("✅ Удалён" if ok else "❌ Не найден")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    rows = list_services()
    text = "\n".join(f"#{r['id']} — {r['name']} — ${r['price']:.2f}" for r in rows) or "Пусто"
    await update.message.reply_text(text)


async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Использование: /addadmin TELEGRAM_ID")
        return
    add_admin(int(context.args[0]))
    log_action(update.effective_user.id, "add_admin", details=context.args[0])
    await update.message.reply_text("✅ Админ добавлен")


async def deladmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if not context.args:
        return
    remove_admin(int(context.args[0]))
    log_action(update.effective_user.id, "del_admin", details=context.args[0])
    await update.message.reply_text("✅ Админ удалён")


async def pay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Использование: /pay ID")
        return
    ok = process_withdrawal(int(context.args[0]), success=True)
    await update.message.reply_text("✅ Выплачено" if ok else "❌ Не найдено / уже обработано")


async def fail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superadmin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Использование: /fail ID")
        return
    ok = process_withdrawal(int(context.args[0]), success=False)
    await update.message.reply_text("✅ Отклонено, средства возвращены" if ok else "❌ Ошибка")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu(
        has_admin_access(update.effective_user.id),
        is_superadmin(update.effective_user.id)
    ))
    return ConversationHandler.END
