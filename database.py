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
            phone TEXT NOT NULL,

            admin_id INTEGER,
            verification_value TEXT,

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


# =========================
# СЕРВИСЫ
# =========================

def add_service(name, price):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO services(name, price) VALUES(?, ?)",
            (name, price)
        )
        return cur.lastrowid


def list_services():
    with connect() as c:
        return c.execute("""
            SELECT *
            FROM services
            WHERE is_active=1
            ORDER BY id
        """).fetchall()


def get_service(service_id):
    with connect() as c:
        return c.execute("""
            SELECT *
            FROM services
            WHERE id=? AND is_active=1
        """, (service_id,)).fetchone()


def delete_service(service_id):
    with connect() as c:
        cur = c.execute("""
            UPDATE services
            SET is_active=0
            WHERE id=? AND is_active=1
        """, (service_id,))

        return cur.rowcount > 0


def update_service_price(service_id, price):
    with connect() as c:
        cur = c.execute("""
            UPDATE services
            SET price=?
            WHERE id=? AND is_active=1
        """, (price, service_id))

        return cur.rowcount > 0


# =========================
# ЗАЯВКИ
# =========================

def create_request(user_id, service_id, phone):
    with connect() as c:
        cur = c.execute("""
            INSERT INTO requests(
                user_id,
                service_id,
                phone,
                status
            )
            VALUES (?, ?, ?, 'queued')
        """, (user_id, service_id, phone))

        return cur.lastrowid


def get_request(request_id):
    with connect() as c:
        return c.execute("""
            SELECT
                r.*,
                s.name AS service_name,
                s.price AS service_price
            FROM requests r
            JOIN services s ON s.id=r.service_id
            WHERE r.id=?
        """, (request_id,)).fetchone()


def user_active_request(user_id):
    with connect() as c:
        return c.execute("""
            SELECT
                r.*,
                s.name AS service_name,
                s.price AS service_price
            FROM requests r
            JOIN services s ON s.id=r.service_id
            WHERE r.user_id=?
              AND r.status IN (
                  'queued',
                  'taken',
                  'pending_review'
              )
            ORDER BY r.id DESC
            LIMIT 1
        """, (user_id,)).fetchone()


def user_active_requests(user_id):
    with connect() as c:
        return c.execute("""
            SELECT
                r.*,
                s.name AS service_name,
                s.price AS service_price
            FROM requests r
            JOIN services s ON s.id=r.service_id
            WHERE r.user_id=?
              AND r.status IN (
                  'queued',
                  'taken',
                  'pending_review'
              )
            ORDER BY r.id DESC
        """, (user_id,)).fetchall()


def queued_for_service(service_id):
    with connect() as c:
        return c.execute("""
            SELECT
                r.*,
                s.name AS service_name,
                s.price AS service_price
            FROM requests r
            JOIN services s ON s.id=r.service_id
            WHERE r.service_id=?
              AND r.status='queued'
            ORDER BY r.id
        """, (service_id,)).fetchall()


# =========================
# ВЗЯТИЕ ЗАЯВКИ
# =========================

def take_request(request_id, admin_id):
    with connect() as c:
        cur = c.execute("""
            UPDATE requests
            SET
                status='taken',
                admin_id=?,
                taken_at=CURRENT_TIMESTAMP
            WHERE id=?
              AND status='queued'
        """, (admin_id, request_id))

        if cur.rowcount != 1:
            return False

        c.execute("""
            INSERT INTO logs(
                actor_id,
                action,
                request_id
            )
            VALUES (?, ?, ?)
        """, (
            admin_id,
            "take_request",
            request_id
        ))

        return True


# =========================
# ЗНАЧЕНИЕ ПОДТВЕРЖДЕНИЯ
# =========================

def submit_verification_value(request_id, user_id, value):
    with connect() as c:
        cur = c.execute("""
            UPDATE requests
            SET
                verification_value=?,
                status='pending_review'
            WHERE id=?
              AND user_id=?
              AND status='taken'
        """, (
            value,
            request_id,
            user_id
        ))

        return cur.rowcount == 1


# =========================
# ПРОВЕРКА ЗАЯВКИ
# =========================

def review_request(request_id, admin_id, approve):
    with connect() as c:
        row = c.execute("""
            SELECT
                r.*,
                s.price
            FROM requests r
            JOIN services s ON s.id=r.service_id
            WHERE r.id=?
        """, (request_id,)).fetchone()

        if not row:
            return None

        if row["status"] != "pending_review":
            return None

        new_status = "approved" if approve else "rejected"

        c.execute("""
            UPDATE requests
            SET
                status=?,
                completed_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            new_status,
            request_id
        ))

        if approve:
            c.execute("""
                INSERT INTO balances(
                    user_id,
                    balance,
                    total_earned
                )
                VALUES (?, ?, ?)

                ON CONFLICT(user_id)
                DO UPDATE SET
                    balance=balance + excluded.balance,
                    total_earned=total_earned + excluded.total_earned
            """, (
                row["user_id"],
                row["price"],
                row["price"]
            ))

        c.execute("""
            INSERT INTO logs(
                actor_id,
                action,
                request_id,
                details
            )
            VALUES (?, ?, ?, ?)
        """, (
            admin_id,
            new_status,
            request_id,
            row["verification_value"]
        ))

        return dict(row)


# =========================
# БАЛАНС
# =========================

def get_balance(user_id):
    with connect() as c:
        row = c.execute("""
            SELECT *
            FROM balances
            WHERE user_id=?
        """, (user_id,)).fetchone()

        if not row:
            return 0.0, 0.0

        return row["balance"], row["total_earned"]


def add_balance(user_id, amount):
    with connect() as c:
        c.execute("""
            INSERT INTO balances(
                user_id,
                balance,
                total_earned
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                balance=balance + excluded.balance,
                total_earned=total_earned + excluded.total_earned
        """, (
            user_id,
            amount,
            amount
        ))


# =========================
# ВЫВОД
# =========================

def reserve_withdrawal(user_id, amount):
    with connect() as c:
        c.execute("""
            INSERT OR IGNORE INTO balances(user_id)
            VALUES (?)
        """, (user_id,))

        cur = c.execute("""
            UPDATE balances
            SET balance=balance-?
            WHERE user_id=?
              AND balance>=?
        """, (
            amount,
            user_id,
            amount
        ))

        if cur.rowcount != 1:
            return None

        cur = c.execute("""
            INSERT INTO withdrawals(
                user_id,
                amount
            )
            VALUES (?, ?)
        """, (
            user_id,
            amount
        ))

        return cur.lastrowid


# =========================
# АВТООЧИСТКА ОЧЕРЕДИ
# =========================

def expire_old_requests():
    with connect() as c:
        cur = c.execute("""
            UPDATE requests
            SET
                status='expired',
                completed_at=CURRENT_TIMESTAMP
            WHERE status='queued'
              AND datetime(created_at)
                  <= datetime('now', '-90 minutes')
        """)

        return cur.rowcount


# =========================
# ОЧИСТИТЬ ОЧЕРЕДЬ
# =========================

def clear_queue(service_id=None):
    with connect() as c:

        if service_id is None:
            cur = c.execute("""
                UPDATE requests
                SET
                    status='cancelled',
                    completed_at=CURRENT_TIMESTAMP
                WHERE status='queued'
            """)
        else:
            cur = c.execute("""
                UPDATE requests
                SET
                    status='cancelled',
                    completed_at=CURRENT_TIMESTAMP
                WHERE status='queued'
                  AND service_id=?
            """, (service_id,))

        return cur.rowcount


# =========================
# АДМИНИСТРАТОРЫ
# =========================

def add_admin(tg_id, username=""):
    with connect() as c:
        c.execute("""
            INSERT INTO admins(
                tg_id,
                username,
                is_active
            )
            VALUES (?, ?, 1)

            ON CONFLICT(tg_id)
            DO UPDATE SET
                username=?,
                is_active=1
        """, (
            tg_id,
            username,
            username
        ))


def remove_admin(tg_id):
    with connect() as c:
        c.execute("""
            UPDATE admins
            SET is_active=0
            WHERE tg_id=?
        """, (tg_id,))


def is_admin(tg_id):
    with connect() as c:
        return c.execute("""
            SELECT 1
            FROM admins
            WHERE tg_id=?
              AND is_active=1
        """, (tg_id,)).fetchone() is not None


def list_admins():
    with connect() as c:
        return c.execute("""
            SELECT *
            FROM admins
            WHERE is_active=1
            ORDER BY tg_id
        """).fetchall()


# =========================
# СТАТИСТИКА
# =========================

def get_statistics():
    with connect() as c:
        users = c.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM requests
        """).fetchone()[0]

        total = c.execute("""
            SELECT COUNT(*)
            FROM requests
        """).fetchone()[0]

        queued = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='queued'
        """).fetchone()[0]

        taken = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='taken'
        """).fetchone()[0]

        pending = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='pending_review'
        """).fetchone()[0]

        approved = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='approved'
        """).fetchone()[0]

        rejected = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='rejected'
        """).fetchone()[0]

        expired = c.execute("""
            SELECT COUNT(*)
            FROM requests
            WHERE status='expired'
        """).fetchone()[0]

        paid = c.execute("""
            SELECT COALESCE(SUM(total_earned), 0)
            FROM balances
        """).fetchone()[0]

        return {
            "users": users,
            "total": total,
            "queued": queued,
            "taken": taken,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "expired": expired,
            "paid": paid
        }


def get_service_statistics(service_id):
    with connect() as c:
        row = c.execute("""
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN status='queued'
                        THEN 1 ELSE 0
                    END
                ) AS queued,

                SUM(
                    CASE
                        WHEN status='taken'
                        THEN 1 ELSE 0
                    END
                ) AS taken,

                SUM(
                    CASE
                        WHEN status='pending_review'
                        THEN 1 ELSE 0
                    END
                ) AS pending,

                SUM(
                    CASE
                        WHEN status='approved'
                        THEN 1 ELSE 0
                    END
                ) AS approved,

                SUM(
                    CASE
                        WHEN status='rejected'
                        THEN 1 ELSE 0
                    END
                ) AS rejected
            FROM requests
            WHERE service_id=?
        """, (service_id,)).fetchone()

        return dict(row)
