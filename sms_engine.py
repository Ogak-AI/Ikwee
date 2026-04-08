import os
import africastalking
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERNAME = os.getenv("AT_USERNAME")
API_KEY = os.getenv("AT_API_KEY")

# Fail hard at startup if credentials are missing — no silent mock mode
if not USERNAME:
    raise RuntimeError("AT_USERNAME environment variable is not set.")
if not API_KEY:
    raise RuntimeError("AT_API_KEY environment variable is not set.")

africastalking.initialize(USERNAME, API_KEY)
sms = africastalking.SMS


def send_sms_nudge(phone_number: str, message: str) -> bool:
    """
    Sends an outbound SMS to the user via Africa's Talking.
    Used for welcome messages, quiz feedback, and module completion nudges.
    Raises an exception if the SMS fails so failures are always visible in logs.
    """
    try:
        response = sms.send(message, [phone_number])
        print(f"[SMS] Sent to {phone_number}: {response}")
        return True
    except Exception as e:
        print(f"[SMS ERROR] Failed to send to {phone_number}: {e}")
        raise
