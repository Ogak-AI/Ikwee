import os
import africastalking
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERNAME = os.getenv("AT_USERNAME", "sandbox")
API_KEY = os.getenv("AT_API_KEY", "")

# Initialize SDK
if API_KEY:
    africastalking.initialize(USERNAME, API_KEY)
    sms = africastalking.SMS
else:
    sms = None

def send_sms_nudge(phone_number: str, message: str):
    """
    Sends an outbound SMS to the user via Africa's Talking.
    Used for nudges or quiz feedback.
    """
    if not sms:
        print(f"[MOCK SMS] To {phone_number}: {message}")
        return False

    try:
        # SenderId is optional. If you don't have one, Africa's Talking uses a default.
        response = sms.send(message, [phone_number])
        print(f"SMS sent successfully: {response}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False
