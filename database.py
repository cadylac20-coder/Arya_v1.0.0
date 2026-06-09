import sqlite3
from config import DB_PATH, DEFAULT_API_KEY

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table 1: Store conversation history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table 2: API Keys for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT UNIQUE NOT NULL,
            name        TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            active      INTEGER DEFAULT 1
        )
    """)

    # Table 3: Capture lead info from conversations
    # This gives MKOV actionable business data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    TEXT UNIQUE NOT NULL,
        destination   TEXT,
        travel_dates  TEXT,
        budget        INTEGER,
        group_size    INTEGER,
        trip_type     TEXT,
        contact_name  TEXT,
        contact_phone TEXT,
        is_complete   INTEGER DEFAULT 0,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")


    cursor.execute("""
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

    cursor.execute("""
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

    cursor.execute("""
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id    TEXT UNIQUE NOT NULL,
        session_id   TEXT NOT NULL,
        request_text TEXT NOT NULL,
        status       TEXT DEFAULT 'open',
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")

    # Seed default API key
    cursor.execute(
        "INSERT OR IGNORE INTO api_keys (key, name) VALUES (?, ?)",
        (DEFAULT_API_KEY, "Development Key")
    )

    conn.commit()
    conn.close()
    print(f"✓ Database initialised at {DB_PATH}")

def get_db():
    """Return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
