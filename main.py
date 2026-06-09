"""
MKOV Arya Travel AI — FastAPI Application
v1.0.0 — Full inquiry + transactional system
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import os

from database import init_db
from ai_engine import chat
from actions import actions
from memory import clear_history, get_session_summary
from auth import verify_api_key
from config import ALLOWED_ORIGINS

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

app = FastAPI(
    title="MKOV Arya Travel AI",
    description="AI-powered travel assistant + transactional booking system for Uniglobe MKOV",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the embeddable widget files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Enums & Schemas ───────────────────────────────────────────────────────────

class ActionType(str, Enum):
    GET_CONFIRMATION = "get_confirmation"
    HOLD_BOOKING     = "hold_booking"
    CANCEL_BOOKING   = "cancel_booking"
    ADD_ANCILLARY    = "add_ancillary"
    PAYMENT_LINK     = "payment_link"
    CUSTOM_REQUEST   = "custom_request"


class ChatRequest(BaseModel):
    message:    str       = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class ActionRequest(BaseModel):
    action:     ActionType
    session_id: str
    booking_id: str | None  = None
    details:    dict | None = None


class ChatResponse(BaseModel):
    reply:             str
    session_id:        str
    suggested_actions: list = []
    lead_progress:     dict = {}


class ActionResponse(BaseModel):
    status:  str
    action:  str
    message: str
    data:    dict | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status":   "online",
        "service":  "MKOV Arya Travel AI v2.0",
        "features": ["Chat", "Lead Extraction", "Hold", "Cancel", "Ancillaries", "Payment"],
    }


@app.get("/widget")
def serve_widget():
    """
    Serves widget.html — visit yourapp.onrender.com/widget to test the UI directly.
    This is also the URL you put in the WordPress iframe src.
    """
    widget_path = os.path.join(STATIC_DIR, "widget.html")
    if os.path.exists(widget_path):
        return FileResponse(widget_path, media_type="text/html")
    return {"error": "widget.html not found. Make sure static/widget.html exists in your project."}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ROUTES — No API key required.
# These are called by widget.html running in the visitor's browser.
# Using /widget/ prefix to cleanly separate from protected server-side routes.
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/widget/chat", response_model=ChatResponse)
def widget_chat_public(req: ChatRequest):
    """
    Public chat endpoint — called by the browser widget on any website.
    No API key required because this runs in a visitor's browser; 
    there is no safe way to hide a key in frontend JS.
    """
    session = req.session_id or str(uuid.uuid4())
    result  = chat(session, req.message)
    suggested = _suggest_actions(result.get("extracted_data", {}), result.get("is_complete", False))
    progress  = _lead_progress(result.get("extracted_data", {}))
    return ChatResponse(
        reply=result["reply"],
        session_id=session,
        suggested_actions=suggested,
        lead_progress=progress,
    )


@app.post("/widget/action", response_model=ActionResponse)
def widget_action_public(req: ActionRequest):
    """
    Public action endpoint — called by the browser widget.
    No API key required for same reason as /widget/chat.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# PROTECTED ROUTES — API key required (X-API-Key header).
# Use these for server-to-server calls, internal tools, or the /docs UI.
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, caller=Depends(verify_api_key)):
    """
    Protected chat endpoint — requires X-API-Key header.
    Use this from your server or the /docs test UI, not from the browser widget.
    """
    session = req.session_id or str(uuid.uuid4())
    result  = chat(session, req.message)
    suggested = _suggest_actions(result.get("extracted_data", {}), result.get("is_complete", False))
    progress  = _lead_progress(result.get("extracted_data", {}))
    return ChatResponse(
        reply=result["reply"],
        session_id=session,
        suggested_actions=suggested,
        lead_progress=progress,
    )


@app.post("/menu/{session_id}")
def show_menu(session_id: str, caller=Depends(verify_api_key)):
    """Return the quick-action menu (inspired by Ask Riya)."""
    return {
        "session_id": session_id,
        "greeting":   "Welcome Travel Partner! 👋",
        "quick_actions": [
            {"id": "get_confirmation", "label": "📋 Get Booking Confirmation", "action": ActionType.GET_CONFIRMATION, "description": "View your booking details and confirmation"},
            {"id": "hold_booking",     "label": "🔒 Hold / Reserve Package",   "action": ActionType.HOLD_BOOKING,     "description": "Reserve a package for 24 hours — no payment needed"},
            {"id": "cancel_booking",   "label": "❌ Cancel Booking",            "action": ActionType.CANCEL_BOOKING,   "description": "Cancel a booking and check your refund"},
            {"id": "add_ancillary",    "label": "✨ Add Extras",                "action": ActionType.ADD_ANCILLARY,    "description": "Insurance, visa, hotel upgrades, transfers"},
            {"id": "payment_link",     "label": "💳 Get Payment Link",          "action": ActionType.PAYMENT_LINK,     "description": "Complete your booking with a secure payment link"},
            {"id": "custom_request",   "label": "💬 Custom Request",            "action": ActionType.CUSTOM_REQUEST,   "description": "Anything else — our specialists are here"},
        ],
        "text_prompt": "Or just type your question below...",
    }


@app.post("/action", response_model=ActionResponse)
def execute_action(req: ActionRequest, caller=Depends(verify_api_key)):
    """Execute a specific transaction action."""
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
            bid    = req.booking_id or (req.details or {}).get("booking_id")
            atype  = (req.details or {}).get("type")
            dets   = (req.details or {}).get("details")
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
    """Clear all messages for a session."""
    clear_history(session_id)
    return {"message": "Conversation cleared", "session_id": session_id}


@app.get("/chat/{session_id}/summary")
def get_summary(session_id: str, caller=Depends(verify_api_key)):
    """Return conversation summary — useful for human agent handoff."""
    return get_session_summary(session_id)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mkov-arya-v1.0.0"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _suggest_actions(data: dict, is_complete: bool) -> list:
    """Suggest contextually relevant next actions based on lead state."""
    suggestions = []
    if is_complete:
        suggestions += [
            {"action": "hold_booking",  "label": "🔒 Hold This Package",   "description": "Reserve for 24 hrs, no payment"},
            {"action": "payment_link",  "label": "💳 Proceed to Payment",  "description": "Complete the booking now"},
        ]
    if data.get("destination"):
        suggestions.append(
            {"action": "add_ancillary", "label": "✨ Add Travel Insurance", "description": "Protect your trip"}
        )
    suggestions.append(
        {"action": "custom_request", "label": "💬 Talk to an Agent", "description": "Connect with a specialist"}
    )
    return suggestions


def _lead_progress(data: dict) -> dict:
    """Return a progress indicator for the lead qualification funnel."""
    required = ["destination", "travel_dates", "budget", "group_size"]
    filled   = [f for f in required if data.get(f)]
    pct      = int(len(filled) / len(required) * 100)
    return {
        "filled":   filled,
        "missing":  [f for f in required if not data.get(f)],
        "percent":  pct,
        "complete": pct == 100,
    }
