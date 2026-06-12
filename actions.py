from datetime import datetime
from database import get_db
import uuid


class MKOVActions:

    @staticmethod
    def get_booking_confirmation(session_id: str, booking_id: str = None) -> dict:
        conn = get_db()
        if not booking_id:
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            ).fetchone()
            booking_id = row["booking_id"] if row else None
        if not booking_id:
            conn.close()
            return {"status": "error", "message": "No active booking found. Have you made a booking with us before?"}
        booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        conn.close()
        if not booking:
            return {"status": "error", "message": f"Booking '{booking_id}' not found."}
        return {
            "status": "success", "action": "get_confirmation",
            "message": (
                f"✅ BOOKING CONFIRMED\n\n"
                f"Reference: {booking['reference_code']}\n"
                f"Destination: {booking['destination']}\n"
                f"Dates: {booking['travel_dates']}\n"
                f"Travellers: {booking['group_size']}\n"
                f"Total: ₹{booking['total_price']:,}\n\n"
                f"Your full itinerary will be shared within 24 hours."
            ),
        }

    @staticmethod
    def hold_booking(session_id, destination=None, travel_dates=None, duration_hours=24):
        if not destination or not travel_dates:
            conn = get_db()
            lead = conn.execute("SELECT destination, travel_dates FROM leads WHERE session_id=?", (session_id,)).fetchone()
            conn.close()
            if lead:
                destination  = destination  or lead["destination"]
                travel_dates = travel_dates or lead["travel_dates"]
        if not destination:
            return {"status": "error", "message": "Please share the destination and travel dates first."}
        hold_id = f"HOLD-{str(uuid.uuid4())[:8].upper()}"
        conn = get_db()
        conn.execute(
            "INSERT INTO holds (session_id, hold_id, destination, travel_dates, hours) VALUES (?,?,?,?,?)",
            (session_id, hold_id, destination, travel_dates, duration_hours)
        )
        conn.commit(); conn.close()
        return {
            "status": "success", "action": "hold_booking", "hold_id": hold_id,
            "message": (
                f"🔒 BOOKING HELD\n\nHold ID: {hold_id}\n"
                f"Destination: {destination}\nDates: {travel_dates}\n"
                f"Valid for: {duration_hours} hours — no payment needed yet.\n\n"
                f"To finalise, call our team or say 'Confirm booking'."
            ),
        }

    @staticmethod
    def cancel_booking(session_id, booking_id=None, reason=None):
        if not booking_id:
            conn = get_db()
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1", (session_id,)
            ).fetchone()
            conn.close()
            booking_id = row["booking_id"] if row else None
        if not booking_id:
            return {"status": "error", "message": "No booking found. Please provide your booking reference."}
        conn = get_db()
        booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        if not booking:
            conn.close()
            return {"status": "error", "message": f"Booking '{booking_id}' not found."}
        original = booking["total_price"] or 0
        refund_pct = 75
        refund = int(original * refund_pct / 100)
        conn.execute("UPDATE bookings SET status='cancelled', cancelled_at=? WHERE booking_id=?",
                     (datetime.now().isoformat(), booking_id))
        conn.commit(); conn.close()
        return {
            "status": "success", "action": "cancel_booking",
            "message": (
                f"❌ CANCELLATION PROCESSED\n\nRef: {booking['reference_code']}\n"
                f"Original: ₹{original:,}\nRefund: {refund_pct}% → ₹{refund:,}\n\n"
                f"Refund within 5-7 business days."
            ),
        }

    _ANCILLARIES = {
        "travel_insurance": {"label": "Travel Insurance",   "price": 2500},
        "visa_assistance":  {"label": "Visa Assistance",    "price": 1500},
        "hotel_upgrade":    {"label": "Hotel Upgrade",      "price": 5000},
        "airport_transfer": {"label": "Airport Transfer",   "price": 1200},
        "activity_package": {"label": "Activity Package",   "price": 3500},
        "meal_plan":        {"label": "Meal Plan",          "price": 2000},
        "travel_sim":       {"label": "International SIM",  "price": 800},
        "forex_card":       {"label": "Forex Card",         "price": 500},
    }

    @classmethod
    def add_ancillary(cls, session_id, booking_id=None, ancillary_type=None, details=None):
        if not ancillary_type or ancillary_type not in cls._ANCILLARIES:
            opts = "\n".join(f"• {v['label']} — ₹{v['price']:,}" for v in cls._ANCILLARIES.values())
            return {"status": "error", "message": f"Available add-ons:\n{opts}"}
        item   = cls._ANCILLARIES[ancillary_type]
        anc_id = f"ANC-{str(uuid.uuid4())[:8].upper()}"
        conn = get_db()
        conn.execute(
            "INSERT INTO ancillaries (booking_id, ancillary_id, type, price, details) VALUES (?,?,?,?,?)",
            (booking_id or "PENDING", anc_id, ancillary_type, item["price"], str(details or {}))
        )
        conn.commit(); conn.close()
        return {
            "status": "success", "action": "add_ancillary",
            "message": f"✨ {item['label']} added — ₹{item['price']:,}\nID: {anc_id}",
        }

    @staticmethod
    def generate_payment_link(session_id, booking_id=None):
        if not booking_id:
            conn = get_db()
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1", (session_id,)
            ).fetchone()
            conn.close()
            booking_id = row["booking_id"] if row else None
        if not booking_id:
            return {"status": "error", "message": "No booking found. Please provide your booking reference."}
        conn = get_db()
        booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        conn.close()
        if not booking:
            return {"status": "error", "message": f"Booking '{booking_id}' not found."}
        token = str(uuid.uuid4())[:12]
        link  = f"https://pay.uniglobemkov.in/{booking_id}?token={token}"
        return {
            "status": "success", "action": "payment_link",
            "message": (
                f"💳 PAYMENT LINK\n\nAmount: ₹{booking['total_price']:,}\n"
                f"Link: {link}\n\nAccepts UPI, Cards, Net Banking."
            ),
        }

    @staticmethod
    def process_custom_request(session_id, request_text):
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        conn = get_db()
        conn.execute(
            "INSERT INTO support_tickets (ticket_id, session_id, request_text) VALUES (?,?,?)",
            (ticket_id, session_id, request_text)
        )
        conn.commit(); conn.close()
        preview = request_text[:100] + ("..." if len(request_text) > 100 else "")
        return {
            "status": "success", "action": "custom_request", "ticket_id": ticket_id,
            "message": (
                f"📋 SUPPORT TICKET CREATED\n\nTicket: {ticket_id}\n\n"
                f"Request: \"{preview}\"\n\n"
                f"Our specialist will contact you within 2 hours."
            ),
        }


actions = MKOVActions()
