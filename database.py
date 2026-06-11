import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "mkov_shaina.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Conversations ─────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── API Keys ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            key        TEXT UNIQUE NOT NULL,
            name       TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            active     INTEGER DEFAULT 1
        )
    """)

    # ── Leads — stores name + phone captured at start of conversation ─────────
    # This is the master list accessible from Render logs / admin
    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT UNIQUE NOT NULL,
            contact_name  TEXT,
            contact_phone TEXT,
            destination   TEXT,
            travel_dates  TEXT,
            group_size    INTEGER,
            trip_type     TEXT,
            is_complete   INTEGER DEFAULT 0,
            identity_given INTEGER DEFAULT 0,  -- 1 once name+phone collected
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Bookings ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id     TEXT UNIQUE NOT NULL,
            session_id     TEXT NOT NULL,
            reference_code TEXT NOT NULL,
            destination    TEXT,
            travel_dates   TEXT,
            group_size     INTEGER,
            total_price    INTEGER,
            email          TEXT,
            status         TEXT DEFAULT 'confirmed',
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            cancelled_at   DATETIME
        )
    """)

    # ── Holds ─────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS holds (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            hold_id      TEXT UNIQUE NOT NULL,
            destination  TEXT,
            travel_dates TEXT,
            hours        INTEGER DEFAULT 24,
            status       TEXT DEFAULT 'active',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Ancillaries ───────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS ancillaries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id   TEXT NOT NULL,
            ancillary_id TEXT UNIQUE NOT NULL,
            type         TEXT NOT NULL,
            price        INTEGER NOT NULL,
            details      TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Support tickets ───────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id    TEXT UNIQUE NOT NULL,
            session_id   TEXT NOT NULL,
            request_text TEXT NOT NULL,
            status       TEXT DEFAULT 'open',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Seed default API key ──────────────────────────────────────────────────
    from config import DEFAULT_API_KEY
    c.execute(
        "INSERT OR IGNORE INTO api_keys (key, name) VALUES (?, ?)",
        (DEFAULT_API_KEY, "Development Key")
    )

    conn.commit()
    conn.close()
    print(f"✓ Database initialised at {DB_PATH}")
