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
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'ready',
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
            number_id INTEGER,
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

def add_service(name, price):
    with connect() as c:
        cur = c.execute("INSERT INTO services(name,price) VALUES(?,?)", (name, price))
        return cur.lastrowid

def list_services():
    with connect() as c:
        return c.execute("SELECT * FROM services WHERE is_active=1 ORDER BY id").fetchall()

def delete_service(service_id):
    with connect() as c:
        return c.execute("UPDATE services SET is_active=0 WHERE id=? AND is_active=1", (service_id,)).rowcount > 0

def get_service(service_id):
    with connect() as c:
        return c.execute("SELECT * FROM services WHERE id=? AND is_active=1", (service_id,)).fetchone()

def add_number(phone):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO numbers(phone,status) VALUES(?, 'ready')", (phone,))

def list_numbers():
    with connect() as c:
        return c.execute("SELECT * FROM numbers ORDER BY id").fetchall()

def create_request(user_id, service_id):
    with connect() as c:
        cur = c.execute("INSERT INTO requests(user_id,service_id) VALUES(?,?)", (user_id, service_id))
        return cur.lastrowid

def get_request(request_id):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name service_name, s.price service_price
            FROM requests r JOIN services s ON s.id=r.service_id
            WHERE r.id=?
        """, (request_id,)).fetchone()

def user_active_request(user_id):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name service_name, s.price service_price
            FROM requests r JOIN services s ON s.id=r.service_id
            WHERE r.user_id=? AND r.status IN ('queued','taken','pending_review')
            ORDER BY r.id DESC LIMIT 1
        """, (user_id,)).fetchone()

def queued_for_service(service_id):
    with connect() as c:
        return c.execute("""
            SELECT r.*, s.name service_name, s.price service_price
            FROM requests r JOIN services s ON s.id=r.service_id
            WHERE r.service_id=? AND r.status='queued'
            ORDER BY r.id
        """, (service_id,)).fetchall()

def take_request(request_id, admin_id):
    with connect() as c:
        # Atomic claim: only one admin can win.
        cur = c.execute("""
            UPDATE requests
            SET status='taken', admin_id=?, taken_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='queued'
        """, (admin_id, request_id))
        if cur.rowcount != 1:
            return False
        c.execute("INSERT INTO logs(actor_id,action,request_id) VALUES(?,?,?)",
                  (admin_id, "take_request", request_id))
        return True

def assign_ready_number(request_id):
    with connect() as c:
        row = c.execute("SELECT id,phone FROM numbers WHERE status='ready' ORDER BY id LIMIT 1").fetchone()
        if not row:
            return None
        cur = c.execute("UPDATE numbers SET status='busy' WHERE id=? AND status='ready'", (row["id"],))
        if cur.rowcount != 1:
            return None
        c.execute("UPDATE requests SET number_id=?, phone=? WHERE id=? AND status='taken'",
                  (row["id"], row["phone"], request_id))
        return row["phone"]

def submit_code(request_id, user_id, code):
    with connect() as c:
        cur = c.execute("""
            UPDATE requests SET code=?, status='pending_review'
            WHERE id=? AND user_id=? AND status='taken'
        """, (code, request_id, user_id))
        return cur.rowcount == 1

def review_request(request_id, admin_id, approve):
    with connect() as c:
        row = c.execute("""
            SELECT r.*, s.price FROM requests r JOIN services s ON s.id=r.service_id
            WHERE r.id=?
        """, (request_id,)).fetchone()
        if not row or row["status"] != "pending_review":
            return None
        new_status = "approved" if approve else "rejected"
        c.execute("UPDATE requests SET status=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
                  (new_status, request_id))
        if row["number_id"]:
            c.execute("UPDATE numbers SET status='ready' WHERE id=?", (row["number_id"],))
        if approve:
            c.execute("""
                INSERT INTO balances(user_id,balance,total_earned) VALUES(?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                balance=balance+excluded.balance,
                total_earned=total_earned+excluded.total_earned
            """, (row["user_id"], row["price"], row["price"]))
        c.execute("INSERT INTO logs(actor_id,action,request_id,details) VALUES(?,?,?,?)",
                  (admin_id, new_status, request_id, row["code"]))
        return dict(row)

def get_balance(user_id):
    with connect() as c:
        row = c.execute("SELECT * FROM balances WHERE user_id=?", (user_id,)).fetchone()
        return (row["balance"], row["total_earned"]) if row else (0.0, 0.0)

def reserve_withdrawal(user_id, amount):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO balances(user_id) VALUES(?)", (user_id,))
        cur = c.execute("UPDATE balances SET balance=balance-? WHERE user_id=? AND balance>=?",
                        (amount, user_id, amount))
        if cur.rowcount != 1:
            return None
        cur = c.execute("INSERT INTO withdrawals(user_id,amount) VALUES(?,?)", (user_id, amount))
        return cur.lastrowid

def add_admin(tg_id, username=""):
    with connect() as c:
        c.execute("INSERT INTO admins(tg_id,username,is_active) VALUES(?,?,1) ON CONFLICT(tg_id) DO UPDATE SET username=?,is_active=1",
                  (tg_id, username, username))

def remove_admin(tg_id):
    with connect() as c:
        c.execute("UPDATE admins SET is_active=0 WHERE tg_id=?", (tg_id,))

def is_admin(tg_id):
    with connect() as c:
        return c.execute("SELECT 1 FROM admins WHERE tg_id=? AND is_active=1", (tg_id,)).fetchone() is not None
