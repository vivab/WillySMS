from telegram import Update
from telegram.ext import ContextTypes
from database import *
from keyboards import *
from utils import has_admin_access, is_superadmin, parse_price
from config import MIN_WITHDRAWAL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("👋 Добро пожаловать!\n\nВыберите действие:", reply_markup=main_menu(has_admin_access(uid), is_superadmin(uid)))

async def services(update, context):
    q = update.callback_query; await q.answer()
    rows = list_services()
    await q.message.edit_text("📋 Выберите сервис:", reply_markup=services_keyboard(rows) if rows else None)

async def choose_service(update, context):
    q = update.callback_query; await q.answer()
    service_id = int(q.data.split(":")[1])
    if user_active_request(q.from_user.id):
        await q.message.reply_text("❌ У вас уже есть активная заявка.")
        return
    rid = create_request(q.from_user.id, service_id)
    s = get_service(service_id)
    await q.message.reply_text(f"✅ Заявка #{rid} создана.\n\nСервис: {s['name']}\nОплата: ${s['price']:.2f}\n\n⏳ Ожидайте администратора.")

async def balance(update, context):
    q = update.callback_query; await q.answer()
    b, total = get_balance(q.from_user.id)
    await q.message.edit_text(f"💰 Баланс\n\nДоступно: ${b:.2f}\nВсего заработано: ${total:.2f}\n\nМинимальный вывод: ${MIN_WITHDRAWAL:.2f}")

async def my_request(update, context):
    q = update.callback_query; await q.answer()
    r = user_active_request(q.from_user.id)
    if not r:
        await q.message.edit_text("📭 Активных заявок нет.")
        return
    status = {"queued":"⏳ В очереди","taken":"📩 Номер выдан, ожидается код","pending_review":"🔎 Код проверяется"}.get(r["status"], r["status"])
    text = f"📊 Заявка #{r['id']}\nСервис: {r['service_name']}\nСтатус: {status}"
    if r["phone"]:
        text += f"\nНомер: {r['phone']}"
    await q.message.edit_text(text)

async def text_input(update, context):
    r = user_active_request(update.effective_user.id)
    if not r or r["status"] != "taken":
        return
    code = update.message.text.strip()
    if not 1 <= len(code) <= 32:
        await update.message.reply_text("❌ Код должен содержать от 1 до 32 символов.")
        return
    if submit_code(r["id"], update.effective_user.id, code):
        await update.message.reply_text("✅ Код получен и отправлен администратору на проверку.")
    else:
        await update.message.reply_text("❌ Не удалось сохранить код.")

async def admin_panel(update, context):
    q = update.callback_query; await q.answer()
    if not has_admin_access(q.from_user.id):
        await q.message.reply_text("❌ Доступ запрещён.")
        return
    await q.message.edit_text("🛠 Админка", reply_markup=admin_services_keyboard(list_services()))

async def queue(update, context):
    q = update.callback_query; await q.answer()
    if not has_admin_access(q.from_user.id): return
    service_id = int(q.data.split(":")[1])
    rows = queued_for_service(service_id)
    if not rows:
        await q.message.edit_text("📭 Очередь пуста.")
        return
    for r in rows:
        await q.message.reply_text(f"📥 Заявка #{r['id']}\nПользователь: {r['user_id']}\nСервис: {r['service_name']}\nЦена: ${r['service_price']:.2f}\n\nВзять: /take {r['id']}")

async def take_cmd(update, context):
    if not has_admin_access(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещён."); return
    if not context.args:
        await update.message.reply_text("Использование: /take ID"); return
    rid = int(context.args[0])
    if not take_request(rid, update.effective_user.id):
        await update.message.reply_text("❌ Заявка уже взята или недоступна."); return
    phone = assign_ready_number(rid)
    if not phone:
        await update.message.reply_text("⚠️ Заявка взята, но свободных номеров нет.")
        return
    r = get_request(rid)
    await update.message.reply_text(f"✅ Заявка #{rid} взята.\nНомер: {phone}")
    try:
        await context.bot.send_message(r["user_id"], f"📨 Ваша заявка #{rid} взята!\n\nСервис: {r['service_name']}\nНомер: {phone}\n\n📩 Когда получите SMS, отправьте код сюда.")
    except Exception:
        pass

async def reviews(update, context):
    q = update.callback_query; await q.answer()
    if not has_admin_access(q.from_user.id): return
    with connect() as c:
        rows = c.execute("SELECT r.*,s.name service_name,s.price FROM requests r JOIN services s ON s.id=r.service_id WHERE r.status='pending_review' ORDER BY r.id").fetchall()
    if not rows:
        await q.message.edit_text("📭 Кодов на проверке нет."); return
    for r in rows:
        await q.message.reply_text(f"📨 Заявка #{r['id']}\nСервис: {r['service_name']}\nНомер: {r['phone']}\nКод: {r['code']}\nСумма: ${r['price']:.2f}", reply_markup=review_keyboard(r["id"]))

async def review(update, context):
    q = update.callback_query; await q.answer()
    if not has_admin_access(q.from_user.id): return
    action, rid = q.data.split(":"); rid = int(rid)
    result = review_request(rid, q.from_user.id, action == "approve")
    if not result:
        await q.message.edit_text("❌ Заявка уже обработана или не найдена."); return
    if action == "approve":
        await q.message.edit_text(f"✅ Заявка #{rid} подтверждена. Начислено ${result['price']:.2f}.")
        msg = f"✅ Код подтверждён!\n\nЗаявка #{rid}\nНачислено: ${result['price']:.2f}"
    else:
        await q.message.edit_text(f"❌ Заявка #{rid} отклонена.")
        msg = f"❌ Код по заявке #{rid} отклонён. Начисление не произведено."
    try: await context.bot.send_message(result["user_id"], msg)
    except Exception: pass

async def add_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        await update.message.reply_text("❌ Только супер-админ."); return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /add Самокат 0.5$"); return
    name = " ".join(context.args[:-1]); price = parse_price(context.args[-1])
    try: sid = add_service(name, price)
    except Exception:
        await update.message.reply_text("❌ Такой сервис уже существует."); return
    await update.message.reply_text(f"✅ Сервис добавлен: #{sid} {name} — ${price:.2f}")

async def del_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        await update.message.reply_text("❌ Только супер-админ."); return
    if not context.args:
        await update.message.reply_text("Использование: /del ID"); return
    await update.message.reply_text("✅ Сервис удалён." if delete_service(int(context.args[0])) else "❌ Сервис не найден.")

async def list_cmd(update, context):
    if not is_superadmin(update.effective_user.id):
        await update.message.reply_text("❌ Только супер-админ."); return
    rows = list_services()
    await update.message.reply_text("\n".join(f"#{r['id']} — {r['name']} — ${r['price']:.2f}" for r in rows) or "Сервисов нет.")

async def addadmin_cmd(update, context):
    if not is_superadmin(update.effective_user.id): return
    if not context.args: return
    add_admin(int(context.args[0]), "")
    await update.message.reply_text("✅ Администратор добавлен.")

async def deladmin_cmd(update, context):
    if not is_superadmin(update.effective_user.id): return
    if not context.args: return
    remove_admin(int(context.args[0]))
    await update.message.reply_text("✅ Администратор удалён.")

async def addnumber_cmd(update, context):
    if not is_superadmin(update.effective_user.id): return
    if not context.args: return
    add_number(context.args[0])
    await update.message.reply_text("✅ Номер добавлен в пул.")
