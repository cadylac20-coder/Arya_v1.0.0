import google.generativeai as genai
from memory import get_history, save_message
from config import GEMINI_API_KEY, MODEL, TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT
from lead_extractor import extract_and_track

print(f"✓ AI Engine loaded — Model: {MODEL}")
genai.configure(api_key=GEMINI_API_KEY)

def chat(session_id: str, user_message: str) -> dict:
    print(f"[CHAT] Session: {session_id}, Message: {user_message[:50]}")

    # Save user message first
    save_message(session_id, "user", user_message)

    # Build conversation history for context
    history = get_history(session_id)

    # Convert history into Gemini-compatible contents list
    # Gemini expects alternating user/model turns
    contents = []
    for msg in history[:-1]:  # exclude the message we just saved (sent separately)
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    try:
        print(f"[CHAT] Calling Gemini model: {MODEL}")
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=SYSTEM_PROMPT,
        )

        # Start chat with history, then send latest message
        chat_session = model.start_chat(history=contents)
        response = chat_session.send_message(
            user_message,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            },
        )

        reply = response.text.strip() if response.text else "I didn't get a response. Could you repeat that?"
        print(f"[CHAT] Reply: {reply[:80]}")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        reply = (
            "I'm having a brief technical issue. "
            "Please try again in a moment, or call us directly at +91-120-XXXXXX. 🙏"
        )

    # Save assistant reply
    save_message(session_id, "assistant", reply)

    # Extract lead info for the UI progress bar
    lead_info = extract_and_track(session_id, user_message)

    return {
        "reply":          reply,
        "session_id":     session_id,
        "extracted_data": lead_info["current_data"],
        "missing_fields":  lead_info["missing_fields"],
        "is_complete":    lead_info["complete"],
    }


def lookup_packages(destination, budget, dates, group):
    """Stub — packages are handled via SYSTEM_PROMPT knowledge."""
    return []
