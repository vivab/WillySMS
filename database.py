import sqlite3
from config import DB_NAME


def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admins (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            phone TEXT,
            admin_id INTEGER,
            code TEXT,
            status TEXT DEFAULT 'queued',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            taken_at TEXT,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            total_earned REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            external_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            paid_at TEXT
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            action TEXT NOT NULL,
            request_id INTEGER,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Включаем WAL-режим, чтобы читатели и писатели меньше блокировали друг друга,
        # и увеличиваем таймаут ожидания снятия блокировки.
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA busy_timeout=5000;")


def log_action(actor_id, action, request_id=None, details=""):
    with connect() as c:
        c.execute(
            "INSERT INTO logs(actor_id, action, request_id, details) VALUES (?,?,?,?)",
            (actor_id, action, request_id, details)
        )


def add_service(name: str, price: float) -> int:
    with connect() as c:
        cur = c.execute("INSERT INTO services(name, price) VALUES (?,?)", (name, price))
        return cur.lastrowid


def list_services():
    with connect() as c:
        return c.execute("SELECT * FROM services WHERE is_active=1 ORDER BY id").fetchall()


def delete_service(service_id: int) -> bool:
    with connect() as c:
        return c.execute(
            "UPDATE services SET is_active=0 WHERE id=? AND is_active=1", (service_id,)
        ).rowcount > 0


def get_service(service_id: int):
    with connect() as c:
        return c.execute(
            "SELECT * FROM services WHERE id=? AND is_active=1", (service_id,)
        ).fetchone()


def add_admin(tg_id: int, username: str = ""):
    with connect() as c:
        c.execute(
            """INSERT INTO admins(tg_id, username, is_active) VALUES (?,?,1)
               ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, is_active=1""",
            (tg_id, username)
        )


def remove_admin(tg_id: int):
    with connect() as c:
        c.execute("UPDATE admins SET is_active=0 WHERE tg_id=?", (tg_id,))


def is_admin(tg_id: int) -> bool:
    with connect() as c:
        return c.execute(
            "SELECT 1 FROM admins WHERE tg_id=? AND is_active=1", (tg_id,)
        ).fetchone() is not None


def list_admins():
    with connect() as c:
        return c.execute("SELECT tg_id, username FROM admins WHERE is_active=1").fetchall()


def create_requests(user_id: int, service_ids: list[int], phone: str) -> list[int]:
    ids = []
    with connect() as c:
        for sid in service_ids:
            cur = c.execute(
                "INSERT INTO requests(user_id, service_id, phone, status) VALUES (?,?,?,'queued')",
                (user_id, sid, phone)
            )
            ids.append(cur.lastrowid)
    return ids


def get_request(request_id: int):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name AS service_name, s.price AS service_price
            FROM requests r
            JOIN services s ON s.id = r.service_id
            WHERE r.id = ?
        """, (request_id,)).fetchone()


def user_active_requests(user_id: int):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name AS service_name, s.price AS service_price
            FROM requests r
            JOIN services s ON s.id = r.service_id
            WHERE r.user_id = ? AND r.status IN ('queued', 'taken', 'pending_review')
            ORDER BY r.id DESC
        """, (user_id,)).fetchall()


def queued_for_service(service_id: int):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name AS service_name, s.price AS service_price
            FROM requests r
            JOIN services s ON s.id = r.service_id
            WHERE r.service_id = ? AND r.status = 'queued'
            ORDER BY r.id
        """, (service_id,)).fetchall()


def take_request(request_id: int, admin_id: int) -> bool:
    # ВАЖНО: log_action открывает СВОЁ отдельное соединение с БД.
    # Если вызвать её внутри ещё не завершённого блока `with connect() as c:`,
    # второе соединение натыкается на блокировку первого -> "database is locked".
    # Поэтому сначала полностью завершаем (и коммитим) обновление, закрываем
    # соединение, и только потом логируем действие отдельным вызовом.
    with connect() as c:
        cur = c.execute("""
            UPDATE requests
            SET status = 'taken', admin_id = ?, taken_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'queued'
        """, (admin_id, request_id))
        success = cur.rowcount == 1

    if not success:
        return False

    log_action(admin_id, "take_request", request_id)
    return True


def submit_code(request_id: int, user_id: int, code: str) -> bool:
    with connect() as c:
        cur = c.execute("""
            UPDATE requests
            SET code = ?, status = 'pending_review'
            WHERE id = ? AND user_id = ? AND status = 'taken'
        """, (code, request_id, user_id))
        return cur.rowcount == 1


def get_pending_reviews():
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name AS service_name, s.price AS service_price
            FROM requests r
            JOIN services s ON s.id = r.service_id
            WHERE r.status = 'pending_review'
            ORDER BY r.id
        """).fetchall()


def review_request(request_id: int, admin_id: int, approve: bool):
    # Та же логика, что и в take_request: сначала завершаем транзакцию
    # с обновлением статуса/баланса, закрываем соединение, и только
    # потом отдельно логируем действие через log_action.
    with connect() as c:
        row = c.execute("""
            SELECT r.*, s.price
            FROM requests r
            JOIN services s ON s.id = r.service_id
            WHERE r.id = ?
        """, (request_id,)).fetchone()

        if not row or row["status"] != "pending_review":
            return None

        new_status = "approved" if approve else "rejected"
        c.execute(
            "UPDATE requests SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, request_id)
        )

        if approve:
            c.execute("""
                INSERT INTO balances(user_id, balance, total_earned)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    balance = balance + excluded.balance,
                    total_earned = total_earned + excluded.total_earned
            """, (row["user_id"], row["price"], row["price"]))

        result = dict(row)

    log_action(admin_id, new_status, request_id, row["code"] or "")
    return result


def get_balance(user_id: int) -> tuple[float, float]:
    with connect() as c:
        row = c.execute("SELECT balance, total_earned FROM balances WHERE user_id = ?", (user_id,)).fetchone()
        return (row["balance"], row["total_earned"]) if row else (0.0, 0.0)


def reserve_withdrawal(user_id: int, amount: float) -> int | None:
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO balances(user_id) VALUES (?)", (user_id,))
        cur = c.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (amount, user_id, amount)
        )
        if cur.rowcount != 1:
            return None
        cur = c.execute(
            "INSERT INTO withdrawals(user_id, amount) VALUES (?, ?)", (user_id, amount)
        )
        return cur.lastrowid


def get_pending_withdrawals():
    with connect() as c:
        return c.execute(
            "SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY id"
        ).fetchall()


def process_withdrawal(withdrawal_id: int, success: bool) -> bool:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM withdrawals WHERE id = ? AND status = 'pending'", (withdrawal_id,)
        ).fetchone()
        if not row:
            return False
        new_status = "paid" if success else "failed"
        c.execute(
            "UPDATE withdrawals SET status = ?, paid_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, withdrawal_id)
        )
        if not success:
            c.execute(
                "UPDATE balances SET balance = balance + ? WHERE user_id = ?",
                (row["amount"], row["user_id"])
            )
        return True


def get_stats():
    with connect() as c:
        total_requests = c.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        queued = c.execute("SELECT COUNT(*) FROM requests WHERE status='queued'").fetchone()[0]
        taken = c.execute("SELECT COUNT(*) FROM requests WHERE status='taken'").fetchone()[0]
        pending = c.execute("SELECT COUNT(*) FROM requests WHERE status='pending_review'").fetchone()[0]
        approved = c.execute("SELECT COUNT(*) FROM requests WHERE status='approved'").fetchone()[0]
        rejected = c.execute("SELECT COUNT(*) FROM requests WHERE status='rejected'").fetchone()[0]
        total_earned = c.execute("SELECT COALESCE(SUM(total_earned), 0) FROM balances").fetchone()[0]
        total_balance = c.execute("SELECT COALESCE(SUM(balance), 0) FROM balances").fetchone()[0]
        pending_wd = c.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM withdrawals WHERE status='pending'").fetchone()
        paid_wd = c.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM withdrawals WHERE status='paid'").fetchone()
        users = c.execute("SELECT COUNT(DISTINCT user_id) FROM requests").fetchone()[0]
        services = c.execute("SELECT COUNT(*) FROM services WHERE is_active=1").fetchone()[0]
        admins = c.execute("SELECT COUNT(*) FROM admins WHERE is_active=1").fetchone()[0]

        top_services = c.execute("""
            SELECT s.name, COUNT(r.id) as cnt,
                   COALESCE(SUM(CASE WHEN r.status='approved' THEN s.price ELSE 0 END), 0) as earned
            FROM services s
            LEFT JOIN requests r ON r.service_id = s.id
            WHERE s.is_active = 1
            GROUP BY s.id
            ORDER BY cnt DESC
            LIMIT 5
        """).fetchall()

        return {
            "total_requests": total_requests,
            "queued": queued,
            "taken": taken,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "total_earned": total_earned,
            "total_balance": total_balance,
            "pending_wd_count": pending_wd[0],
            "pending_wd_sum": pending_wd[1],
            "paid_wd_count": paid_wd[0],
            "paid_wd_sum": paid_wd[1],
            "users": users,
            "services": services,
            "admins": admins,
            "top_services": top_services,
        }
