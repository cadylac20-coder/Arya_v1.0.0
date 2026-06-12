"""
MKOV Shanaya Travel AI — FastAPI Backend v2.0
"""

import os
import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

from database import init_db, get_db
from ai_engine import chat
from actions import actions
from memory import clear_history, get_session_summary
from auth import verify_api_key
from config import ALLOWED_ORIGINS

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

app = FastAPI(
    title="MKOV Shanaya Travel AI",
    description="AI travel assistant for Uniglobe MKOV — Shanaya",
    version="2.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    GET_CONFIRMATION = "get_confirmation"
    HOLD_BOOKING     = "hold_booking"
    CANCEL_BOOKING   = "cancel_booking"
    ADD_ANCILLARY    = "add_ancillary"
    PAYMENT_LINK     = "payment_link"
    CUSTOM_REQUEST   = "custom_request"

class ChatRequest(BaseModel):
    message:    str            = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str]  = None

class ActionRequest(BaseModel):
    action:     ActionType
    session_id: str
    booking_id: Optional[str]  = None
    details:    Optional[dict] = None

class ChatResponse(BaseModel):
    reply:             str
    session_id:        str
    suggested_actions: list = []
    lead_progress:     dict = {}
    identity_given:    bool = False

class ActionResponse(BaseModel):
    status:  str
    action:  str
    message: str
    data:    Optional[dict] = None


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "service": "MKOV Shanaya v2.0", "chatbot": "Shanaya"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/widget")
def serve_widget():
    path = os.path.join(STATIC_DIR, "widget.html")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html")
    return {"error": "widget.html not found in static/"}


# ── PUBLIC routes — called by browser widget, no API key needed ───────────────

@app.post("/widget/chat", response_model=ChatResponse)
def widget_chat_public(req: ChatRequest):
    session = req.session_id or str(uuid.uuid4())
    result  = chat(session, req.message)
    suggested = _suggest_actions(result.get("extracted_data", {}), result.get("is_complete", False))
    progress  = _lead_progress(result.get("extracted_data", {}))
    return ChatResponse(
        reply=result["reply"],
        session_id=session,
        suggested_actions=suggested,
        lead_progress=progress,
        identity_given=result.get("identity_given", False),
    )

@app.post("/widget/action", response_model=ActionResponse)
def widget_action_public(req: ActionRequest):
    try:
        if req.action == ActionType.GET_CONFIRMATION:
            result = actions.get_booking_confirmation(req.session_id, req.booking_id)
        elif req.action == ActionType.HOLD_BOOKING:
            dest  = (req.details or {}).get("destination")
            dates = (req.details or {}).get("travel_dates")
            hrs   = (req.details or {}).get("duration_hours", 24)
            result = actions.hold_booking(req.session_id, dest, dates, hrs)
        elif req.action == ActionType.CANCEL_BOOKING:
            bid    = req.booking_id or (req.details or {}).get("booking_id")
            reason = (req.details or {}).get("reason")
            result = actions.cancel_booking(req.session_id, bid, reason)
        elif req.action == ActionType.ADD_ANCILLARY:
            bid   = req.booking_id or (req.details or {}).get("booking_id")
            atype = (req.details or {}).get("type")
            dets  = (req.details or {}).get("details")
            result = actions.add_ancillary(req.session_id, bid, atype, dets)
        elif req.action == ActionType.PAYMENT_LINK:
            bid = req.booking_id or (req.details or {}).get("booking_id")
            result = actions.generate_payment_link(req.session_id, bid)
        elif req.action == ActionType.CUSTOM_REQUEST:
            text = (req.details or {}).get("request_text", "No details provided")
            result = actions.process_custom_request(req.session_id, text)
        else:
            result = {"status": "error", "message": f"Unknown action: {req.action}"}
    except Exception as e:
        result = {"status": "error", "message": f"Action failed: {str(e)}"}
    return ActionResponse(
        status=result.get("status", "error"),
        action=req.action,
        message=result.get("message", ""),
        data={k: v for k, v in result.items() if k not in ("message", "status")},
    )


# ── PROTECTED routes — require X-API-Key header ───────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, caller=Depends(verify_api_key)):
    session = req.session_id or str(uuid.uuid4())
    result  = chat(session, req.message)
    suggested = _suggest_actions(result.get("extracted_data", {}), result.get("is_complete", False))
    progress  = _lead_progress(result.get("extracted_data", {}))
    return ChatResponse(
        reply=result["reply"],
        session_id=session,
        suggested_actions=suggested,
        lead_progress=progress,
        identity_given=result.get("identity_given", False),
    )

@app.get("/leads", response_model=None)
def get_all_leads(caller=Depends(verify_api_key)):
    """
    Admin endpoint — returns all captured leads (name + phone + trip details).
    Call with: GET /leads  header: X-API-Key: mkov-dev-key-2026
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT session_id, contact_name, contact_phone, destination,
                  travel_dates, group_size, trip_type, created_at, updated_at
           FROM leads
           WHERE identity_given = 1
           ORDER BY created_at DESC"""
    ).fetchall()
    conn.close()
    return {
        "total": len(rows),
        "leads": [dict(r) for r in rows]
    }

@app.post("/action", response_model=ActionResponse)
def execute_action(req: ActionRequest, caller=Depends(verify_api_key)):
    try:
        if req.action == ActionType.GET_CONFIRMATION:
            result = actions.get_booking_confirmation(req.session_id, req.booking_id)
        elif req.action == ActionType.HOLD_BOOKING:
            dest  = (req.details or {}).get("destination")
            dates = (req.details or {}).get("travel_dates")
            hrs   = (req.details or {}).get("duration_hours", 24)
            result = actions.hold_booking(req.session_id, dest, dates, hrs)
        elif req.action == ActionType.CANCEL_BOOKING:
            bid    = req.booking_id or (req.details or {}).get("booking_id")
            reason = (req.details or {}).get("reason")
            result = actions.cancel_booking(req.session_id, bid, reason)
        elif req.action == ActionType.ADD_ANCILLARY:
            bid   = req.booking_id or (req.details or {}).get("booking_id")
            atype = (req.details or {}).get("type")
            dets  = (req.details or {}).get("details")
            result = actions.add_ancillary(req.session_id, bid, atype, dets)
        elif req.action == ActionType.PAYMENT_LINK:
            bid = req.booking_id or (req.details or {}).get("booking_id")
            result = actions.generate_payment_link(req.session_id, bid)
        elif req.action == ActionType.CUSTOM_REQUEST:
            text = (req.details or {}).get("request_text", "No details provided")
            result = actions.process_custom_request(req.session_id, text)
        else:
            result = {"status": "error", "message": f"Unknown action: {req.action}"}
    except Exception as e:
        result = {"status": "error", "message": f"Action failed: {str(e)}"}
    return ActionResponse(
        status=result.get("status", "error"),
        action=req.action,
        message=result.get("message", ""),
        data={k: v for k, v in result.items() if k not in ("message", "status")},
    )

@app.delete("/chat/{session_id}")
def reset_conversation(session_id: str, caller=Depends(verify_api_key)):
    clear_history(session_id)
    return {"message": "Cleared", "session_id": session_id}

@app.get("/chat/{session_id}/summary")
def get_summary(session_id: str, caller=Depends(verify_api_key)):
    return get_session_summary(session_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _suggest_actions(data: dict, is_complete: bool) -> list:
    suggestions = []
    if data.get("destination"):
        suggestions.append({"action": "custom_request", "label": "💬 Talk to a Travel Expert", "description": "Connect with our specialist"})
    suggestions.append({"action": "custom_request", "label": "📞 Call Us", "description": "Speak to our team directly"})
    return suggestions

def _lead_progress(data: dict) -> dict:
    required = ["destination", "travel_dates", "group_size"]
    filled   = [f for f in required if data.get(f)]
    pct      = int(len(filled) / len(required) * 100)
    return {"filled": filled, "missing": [f for f in required if not data.get(f)], "percent": pct, "complete": pct == 100}
