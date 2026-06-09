from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from database import get_db

api_key_header = APIKeyHeader(name="X-API-Key", description="Your API key for MKOV AI")

def verify_api_key(key: str = Security(api_key_header)) -> dict:
    """
    Verify that the provided API key is valid and active.
    
    Usage in a route:
        @app.post("/chat")
        def chat(req: ChatRequest, caller=Depends(verify_api_key)):
            # caller is now {"key": "...", "name": "..."}
    """
    conn = get_db()
    row = conn.execute(
        "SELECT name FROM api_keys WHERE key = ? AND active = 1",
        (key,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key. Contact MKOV for access."
        )

    return {"key": key, "name": row[0]}
