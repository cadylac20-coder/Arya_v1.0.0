import json
import google.generativeai as genai
from database import get_db
from config import GEMINI_API_KEY, MODEL

genai.configure(api_key=GEMINI_API_KEY)

REQUIRED_FIELDS = ["destination", "travel_dates", "budget", "group_size"]

def extract_and_track(session_id: str, user_message: str) -> dict:
    prompt = f'Extract the following travel details from the message: destination, travel_dates, budget, group_size, trip_type, contact_name, contact_phone. Message: "{user_message}". Return ONLY a JSON object.'
    try:
        model = genai.GenerativeModel(MODEL)
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)
    except:
        extracted = {"destination": None, "travel_dates": None, "budget": None, "group_size": None, "trip_type": None, "contact_name": None, "contact_phone": None, "ambiguities": []}
    
    conn = get_db()
    existing = conn.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,)).fetchone()
    
    current_data = {
        "destination": extracted.get("destination") or (existing["destination"] if existing else None),
        "travel_dates": extracted.get("travel_dates") or (existing["travel_dates"] if existing else None),
        "budget": extracted.get("budget") or (existing["budget"] if existing else None),
        "group_size": extracted.get("group_size") or (existing["group_size"] if existing else None),
        "trip_type": extracted.get("trip_type"),
        "contact_name": extracted.get("contact_name"),
        "contact_phone": extracted.get("contact_phone"),
    }
    
    missing = [f for f in REQUIRED_FIELDS if not current_data.get(f)]
    is_complete = len(missing) == 0
    
    if existing:
        conn.execute("UPDATE leads SET destination=?, travel_dates=?, budget=?, group_size=?, trip_type=?, contact_name=?, contact_phone=?, is_complete=? WHERE session_id=?",
            (current_data["destination"], current_data["travel_dates"], current_data["budget"], current_data["group_size"], current_data["trip_type"], current_data["contact_name"], current_data["contact_phone"], int(is_complete), session_id))
    else:
        conn.execute("INSERT INTO leads (session_id, destination, travel_dates, budget, group_size, trip_type, contact_name, contact_phone, is_complete) VALUES (?,?,?,?,?,?,?,?,?)",
            (session_id, current_data["destination"], current_data["travel_dates"], current_data["budget"], current_data["group_size"], current_data["trip_type"], current_data["contact_name"], current_data["contact_phone"], int(is_complete)))
    conn.commit()
    conn.close()
    
    return {"extracted": extracted, "current_data": current_data, "missing_fields": missing, "complete": is_complete}

def generate_intelligent_question(missing_fields, current_data):
    if not missing_fields:
        return None
    field = missing_fields[0]
    if field == "destination":
        return "Where would you like to travel?"
    if field == "travel_dates":
        return "When are you planning to visit?"
    if field == "group_size":
        return "How many people will be travelling?"
    if field == "budget":
        return "What's your budget?"
    return "Tell me more about your trip!"
