"""
EXAMPLE FLOWS — How the Enhanced MKOV AI Works

Shows 3 customer journeys from inquiry to transaction.
"""

import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "mkov-dev-key-2026"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("=" * 70)
print("MKOV AI ENHANCED - EXAMPLE FLOWS")
print("=" * 70)

# ─── FLOW 1: Inquiry → Hold → Payment ────────────────────────────────────

print("\n\n📖 FLOW 1: Customer Goes From Inquiry to Booking\n")
print("─" * 70)

# Step 1: Chat - Initial inquiry
print("\n1️⃣  CUSTOMER: 'I want to go to Bali in February for a honeymoon'")
response = requests.post(
    f"{BASE_URL}/chat",
    headers=HEADERS,
    json={"message": "I want to go to Bali in February for a honeymoon"}
)
chat_data = response.json()
session_id = chat_data["session_id"]
print(f"\n🤖 UMKOV: {chat_data['reply']}\n")
print(f"Session ID: {session_id}")
print(f"Suggested Actions: {json.dumps(chat_data.get('suggested_actions', []), indent=2)}")

# Step 2: Chat - Provide more details
print("\n\n2️⃣  CUSTOMER: 'There will be 2 of us, budget is 2 lakhs'")
response = requests.post(
    f"{BASE_URL}/chat",
    headers=HEADERS,
    json={
        "message": "There will be 2 of us, budget is 2 lakhs",
        "session_id": session_id
    }
)
chat_data = response.json()
print(f"\n🤖 UMKOV: {chat_data['reply']}\n")

# Step 3: Show menu of quick actions
print("\n3️⃣  SYSTEM: Showing quick action menu...")
response = requests.post(
    f"{BASE_URL}/menu/{session_id}",
    headers=HEADERS
)
menu = response.json()
print(f"\n{menu['greeting']}")
print("\nQuick Actions Available:")
for action in menu["quick_actions"]:
    print(f"  • {action['label']}")
    print(f"    {action['description']}\n")

# Step 4: Execute action - HOLD booking
print("\n4️⃣  CUSTOMER: Clicks 'Hold / Reserve Package'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "hold_booking",
        "session_id": session_id,
        "details": {
            "destination": "Bali",
            "travel_dates": "February 14-25",
            "duration_hours": 24
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

# Step 5: Execute action - Generate payment link
print("\n5️⃣  CUSTOMER: Ready to pay, clicks 'Generate Payment Link'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "payment_link",
        "session_id": session_id,
        "details": {
            "booking_id": "BK-001"  # Mock ID
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

# ─── FLOW 2: Check Confirmation → Add Ancillary ──────────────────────────

print("\n\n" + "=" * 70)
print("📖 FLOW 2: Existing Customer Checks Booking & Adds Ancillaries\n")
print("─" * 70)

new_session = "existing-customer-456"

print(f"\n1️⃣  CUSTOMER: 'Can I see my booking confirmation for Bali?'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "get_confirmation",
        "session_id": new_session,
        "booking_id": "BK-001"
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

print("\n2️⃣  CUSTOMER: 'I want to add travel insurance and upgrade the hotel'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "add_ancillary",
        "session_id": new_session,
        "booking_id": "BK-001",
        "details": {
            "type": "travel_insurance",
            "details": {"coverage": "full"}
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

print("\n3️⃣  CUSTOMER: 'Also add a hotel upgrade'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "add_ancillary",
        "session_id": new_session,
        "booking_id": "BK-001",
        "details": {
            "type": "hotel_upgrade",
            "details": {"from": "3-star", "to": "5-star"}
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

# ─── FLOW 3: Cancellation with Refund ────────────────────────────────────

print("\n\n" + "=" * 70)
print("📖 FLOW 3: Customer Needs to Cancel & Check Refund\n")
print("─" * 70)

cancel_session = "cancel-customer-789"

print(f"\n1️⃣  CUSTOMER: 'I need to cancel my Goa booking, something came up'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "cancel_booking",
        "session_id": cancel_session,
        "booking_id": "BK-002",
        "details": {
            "reason": "Emergency work commitment"
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

print("\n2️⃣  CHAT: 'Can you help me rebook for a different date?'")
response = requests.post(
    f"{BASE_URL}/chat",
    headers=HEADERS,
    json={
        "message": "Can you help me rebook for a different date in March instead?",
        "session_id": cancel_session
    }
)
chat_data = response.json()
print(f"\n🤖 UMKOV: {chat_data['reply']}\n")

# ─── FLOW 4: Custom Request to Agent ─────────────────────────────────────

print("\n\n" + "=" * 70)
print("📖 FLOW 4: Custom Request → Support Ticket\n")
print("─" * 70)

custom_session = "custom-request-111"

print(f"\n1️⃣  CUSTOMER: 'I have a group of 50 people, need a corporate retreat package'")
response = requests.post(
    f"{BASE_URL}/action",
    headers=HEADERS,
    json={
        "action": "custom_request",
        "session_id": custom_session,
        "details": {
            "request_text": "Large corporate group of 50 people. Need adventure + relaxation mix. Budget flexible. Flexible dates in next 3 months."
        }
    }
)
action_data = response.json()
print(f"\n{action_data['message']}\n")

print("\n2️⃣  SYSTEM: Support agent assigned")
print("    ✓ Ticket TKT-ABC123 created")
print("    ✓ Manager will call within 2 hours")
print("    ✓ Custom quote will be prepared\n")

# ─── Summary ──────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SUMMARY: What This Enhanced System Provides")
print("=" * 70)

print("""
✅ INQUIRY CHATBOT (AI-driven)
   • Understand customer needs
   • Ask smart follow-up questions
   • Recommend packages
   • Extract structured data (destination, budget, dates, group)

✅ MENU-DRIVEN ACTIONS (Like Riya)
   • Get Booking Confirmation (retrieve existing bookings)
   • Hold/Reserve Package (24-hour no-payment reservation)
   • Cancel Booking (with refund calculation)
   • Add Ancillaries (insurance, visas, upgrades)
   • Payment Link (generate payment gateway link)
   • Custom Request (create support tickets)

✅ TRANSACTION MANAGEMENT
   • Track holds, bookings, ancillaries, payments
   • Calculate refunds based on cancellation policy
   • Generate payment links (Razorpay integration)
   • Create support tickets for custom requests

✅ CONVERSATION MEMORY
   • Remember extracted data
   • Track session context
   • Suggest next actions based on context

✅ MULTI-CHANNEL READY
   • REST API (web)
   • WhatsApp (via Twilio integration)
   • Mobile App (custom UI)
   • Website Widget (embedded chat)
""")

print("\nRUN THIS SCRIPT:")
print("1. Make sure the API is running: uvicorn main:app --reload")
print("2. Execute: python example_flow.py")
print("=" * 70)