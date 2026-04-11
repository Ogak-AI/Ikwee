import os
import logging
import africastalking
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

USERNAME = os.getenv("AT_USERNAME")
API_KEY = os.getenv("AT_API_KEY")

# Initialize AT SDK if credentials exist; warn (don't crash) if missing.
# This lets FastAPI boot even without AT creds so Render health checks pass
# and you can diagnose via logs instead of a mystery 404.
sms = None
if USERNAME and API_KEY:
    africastalking.initialize(USERNAME, API_KEY)
    sms = africastalking.SMS
    logger.info(f"[SMS] Africa's Talking initialized for user: {USERNAME}")
else:
    logger.warning(
        "[SMS] AT_USERNAME or AT_API_KEY not set — SMS sending is DISABLED. "
        "Set these in Render Environment Variables to enable SMS."
    )


def send_sms_nudge(phone_number: str, message: str, keyword: str = None, link_id: str = None) -> bool:
    """
    Sends an outbound SMS. 
    If 'keyword' and 'link_id' are provided, it acts as a Premium SMS response 
    (charging the user's airtime based on your AT configuration).
    """
    if sms is None:
        logger.error(f"[SMS] Cannot send to {phone_number} — AT credentials missing.")
        return False

    # Get shortCode from env if available
    short_code = os.getenv("SENDER_ID") or os.getenv("AT_SHORTCODE")

    try:
        # AT SDK send() accepts keyword, shortCode, and linkId for premium billing
        params = {
            "message": message,
            "recipients": [phone_number]
        }
        if short_code:
            params["short_code"] = short_code
        if keyword:
            params["keyword"] = keyword
        if link_id:
            params["link_id"] = link_id

        response = sms.send(**params)
        logger.info(f"[SMS] Sent to {phone_number}: {response}")
        return True
    except Exception as e:
        logger.error(f"[SMS ERROR] Failed to send to {phone_number}: {e}")
        return False
