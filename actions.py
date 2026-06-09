"""
Action handlers for specific MKOV operations.
Each method processes a real transactional request and persists results to the DB.
"""

from datetime import datetime
from database import get_db
import uuid


class MKOVActions:
    """Handles all transactional operations."""

    # ── Gets Booking Confirmation ─────────────────────────────────────────────
    @staticmethod
    def get_booking_confirmation(session_id: str, booking_id: str = None) -> dict:
        conn = get_db()

        # Auto-discovers booking from session if not provided
        if not booking_id:
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            booking_id = row["booking_id"] if row else None

        if not booking_id:
            conn.close()
            return {
                "status": "error",
                "message": "No active booking found for your session. Have you made a booking with us before?",
            }

        booking = conn.execute(
            "SELECT * FROM bookings WHERE booking_id=?", (booking_id,)
        ).fetchone()
        conn.close()

        if not booking:
            return {"status": "error", "message": f"Booking '{booking_id}' not found in our system."}

        return {
            "status":               "success",
            "action":               "get_confirmation",
            "booking_id":           booking["booking_id"],
            "destination":          booking["destination"],
            "travel_dates":         booking["travel_dates"],
            "total_price":          booking["total_price"],
            "booking_reference":    booking["reference_code"],
            "message": (
                f"✅ BOOKING CONFIRMED\n\n"
                f"Reference: {booking['reference_code']}\n"
                f"Destination: {booking['destination']}\n"
                f"Dates: {booking['travel_dates']}\n"
                f"Travellers: {booking['group_size']}\n"
                f"Total: ₹{booking['total_price']:,}\n\n"
                f"Confirmation was sent to: {booking['email']}\n"
                f"Your full itinerary will be shared within 24 hours."
            ),
        }

    # ── Holds Booking ─────────────────────────────────────────────────────────
    @staticmethod
    def hold_booking(
        session_id: str,
        destination: str = None,
        travel_dates: str = None,
        duration_hours: int = 24,
    ) -> dict:
        # Falls back to lead data in DB if args not provided
        if not destination or not travel_dates:
            conn = get_db()
            lead = conn.execute(
                "SELECT destination, travel_dates FROM leads WHERE session_id=?",
                (session_id,),
            ).fetchone()
            conn.close()
            if lead:
                destination   = destination   or lead["destination"]
                travel_dates  = travel_dates  or lead["travel_dates"]

        if not destination:
            return {
                "status": "error",
                "message": "Please share the destination and travel dates before holding a booking.",
            }

        hold_id = f"HOLD-{str(uuid.uuid4())[:8].upper()}"

        conn = get_db()
        conn.execute(
            """INSERT INTO holds (session_id, hold_id, destination, travel_dates, hours)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, hold_id, destination, travel_dates, duration_hours),
        )
        conn.commit()
        conn.close()

        return {
            "status":            "success",
            "action":            "hold_booking",
            "hold_id":           hold_id,
            "hold_expiry_hours": duration_hours,
            "destination":       destination,
            "travel_dates":      travel_dates,
            "message": (
                f"🔒 BOOKING HELD\n\n"
                f"Hold ID: {hold_id}\n"
                f"Destination: {destination}\n"
                f"Travel Dates: {travel_dates}\n"
                f"Valid For: {duration_hours} hours — no payment needed yet.\n\n"
                f"Complete your booking any time within {duration_hours} hours.\n"
                f"Say 'Confirm booking' when you're ready to proceed."
            ),
        }

    # ── Cancelling Booking ───────────────────────────────────────────────────────
    @staticmethod
    def cancel_booking(session_id: str, booking_id: str = None, reason: str = None) -> dict:
        if not booking_id:
            conn = get_db()
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            conn.close()
            booking_id = row["booking_id"] if row else None

        if not booking_id:
            return {
                "status": "error",
                "message": "No booking found to cancel. Please provide your booking reference.",
            }

        conn = get_db()
        booking = conn.execute(
            "SELECT * FROM bookings WHERE booking_id=?", (booking_id,)
        ).fetchone()

        if not booking:
            conn.close()
            return {"status": "error", "message": f"Booking '{booking_id}' not found."}

        # Simplified refund policy (production: calculate from actual travel date)
        days_before = 10  # placeholder — replace with real date calculation
        original_price = booking["total_price"] or 0
        if days_before > 30:
            refund_pct = 100
        elif days_before > 14:
            refund_pct = 75
        else:
            refund_pct = 50
        refund_amount = int(original_price * refund_pct / 100)

        conn.execute(
            "UPDATE bookings SET status='cancelled', cancelled_at=? WHERE booking_id=?",
            (datetime.now().isoformat(), booking_id),
        )
        conn.commit()
        conn.close()

        return {
            "status":        "success",
            "action":        "cancel_booking",
            "booking_id":    booking_id,
            "refund_amount": refund_amount,
            "refund_pct":    refund_pct,
            "message": (
                f"❌ CANCELLATION PROCESSED\n\n"
                f"Reference: {booking['reference_code']}\n"
                f"Original Amount: ₹{original_price:,}\n"
                f"Refund: {refund_pct}% → ₹{refund_amount:,}\n\n"
                f"Refund credited to your original payment method within 5–7 business days.\n"
                f"Need to rebook for different dates? I'm happy to help! 😊"
            ),
        }

    # ── Add Ancillary ────────────────────────────────────────────────────────
    _ANCILLARY_CATALOGUE = {
        "travel_insurance":  {"label": "Travel Insurance",    "price": 2500},
        "visa_assistance":   {"label": "Visa Assistance",     "price": 1500},
        "hotel_upgrade":     {"label": "Hotel Upgrade",       "price": 5000},
        "airport_transfer":  {"label": "Airport Transfer",    "price": 1200},
        "activity_package":  {"label": "Activity Package",    "price": 3500},
        "meal_plan":         {"label": "Meal Plan",           "price": 2000},
        "travel_sim":        {"label": "International SIM",   "price": 800},
        "forex_card":        {"label": "Forex Card",          "price": 500},
    }

    @classmethod
    def add_ancillary(
        cls,
        session_id: str,
        booking_id: str = None,
        ancillary_type: str = None,
        details: dict = None,
    ) -> dict:
        if not ancillary_type or ancillary_type not in cls._ANCILLARY_CATALOGUE:
            available = "\n".join(
                f"• {v['label']} — ₹{v['price']:,}"
                for v in cls._ANCILLARY_CATALOGUE.values()
            )
            return {
                "status": "error",
                "message": f"Unknown ancillary type. Available options:\n{available}",
            }

        item = cls._ANCILLARY_CATALOGUE[ancillary_type]
        anc_id = f"ANC-{str(uuid.uuid4())[:8].upper()}"

        conn = get_db()
        conn.execute(
            """INSERT INTO ancillaries (booking_id, ancillary_id, type, price, details)
               VALUES (?, ?, ?, ?, ?)""",
            (booking_id or "PENDING", anc_id, ancillary_type, item["price"], str(details or {})),
        )
        conn.commit()
        conn.close()

        all_options = "\n".join(
            f"  • {v['label']} — ₹{v['price']:,}"
            for k, v in cls._ANCILLARY_CATALOGUE.items()
            if k != ancillary_type
        )

        return {
            "status":       "success",
            "action":       "add_ancillary",
            "ancillary_id": anc_id,
            "type":         ancillary_type,
            "price":        item["price"],
            "message": (
                f"✨ {item['label'].upper()} ADDED\n\n"
                f"ID: {anc_id}\n"
                f"Price: ₹{item['price']:,}\n\n"
                f"Your updated total will be confirmed by our team.\n\n"
                f"Other add-ons available:\n{all_options}"
            ),
        }

    # ── Generate Payment Link ────────────────────────────────────────────────
    @staticmethod
    def generate_payment_link(session_id: str, booking_id: str = None) -> dict:
        if not booking_id:
            conn = get_db()
            row = conn.execute(
                "SELECT booking_id FROM bookings WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            conn.close()
            booking_id = row["booking_id"] if row else None

        if not booking_id:
            return {
                "status": "error",
                "message": "No booking found. Please complete your booking details first.",
            }

        conn = get_db()
        booking = conn.execute(
            "SELECT * FROM bookings WHERE booking_id=?", (booking_id,)
        ).fetchone()
        conn.close()

        if not booking:
            return {"status": "error", "message": f"Booking '{booking_id}' not found."}

        # In production: call Razorpay / PayU API here
        token = str(uuid.uuid4())[:12]
        payment_link = f"https://pay.uniglobemkov.in/{booking_id}?token={token}"

        return {
            "status":        "success",
            "action":        "payment_link",
            "payment_link":  payment_link,
            "amount":        booking["total_price"],
            "message": (
                f"💳 PAYMENT LINK READY\n\n"
                f"Amount: ₹{booking['total_price']:,}\n"
                f"Link: {payment_link}\n\n"
                f"Accepted: Credit/Debit card, UPI, Net Banking, Wallets\n"
                f"Secured by Razorpay 🔒\n\n"
                f"Booking is confirmed once payment is successful."
            ),
        }

    # ── Custom Request / Support Ticket ─────────────────────────────────────
    @staticmethod
    def process_custom_request(session_id: str, request_text: str) -> dict:
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"

        conn = get_db()
        conn.execute(
            """INSERT INTO support_tickets (ticket_id, session_id, request_text)
               VALUES (?, ?, ?)""",
            (ticket_id, session_id, request_text),
        )
        conn.commit()
        conn.close()

        preview = request_text[:120] + ("..." if len(request_text) > 120 else "")

        return {
            "status":    "success",
            "action":    "custom_request",
            "ticket_id": ticket_id,
            "message": (
                f"📋 SUPPORT TICKET CREATED\n\n"
                f"Ticket ID: {ticket_id}\n\n"
                f"Request: \"{preview}\"\n\n"
                f"A travel specialist will contact you within 2 hours.\n"
                f"Track your request with ticket ID: {ticket_id}"
            ),
        }


# Singleton
actions = MKOVActions()
