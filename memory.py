from database import get_db
from config import MAX_HISTORY

def get_history(session_id: str) -> list:
    """
    Retrieve conversation history for a session.
    Returns list of {"role": "user/assistant", "content": "..."}
    """
    conn = get_db()
    rows = conn.execute(
        """
        SELECT role, content FROM conversations 
        WHERE session_id = ? 
        ORDER BY id DESC 
        LIMIT ?
        """,
        (session_id, MAX_HISTORY)
    ).fetchall()
    conn.close()

    # Reverse to get chronological order (oldest first)
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def save_message(session_id: str, role: str, content: str):
    """Save a single message to conversation history."""
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def clear_history(session_id: str):
    """Clear all messages for a session (start fresh)."""
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_session_summary(session_id: str) -> dict:
    """
    Get a quick summary of what was discussed in this session.
    Useful for handing off to a human agent.
    """
    conn = get_db()
    messages = conn.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id",
        (session_id,)
    ).fetchall()
    conn.close()

    summary = {
        "session_id": session_id,
        "message_count": len(messages),
        "first_message": messages[0][1] if messages else None,
        "last_message": messages[-1][1] if messages else None,
    }
    return summary