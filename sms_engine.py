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


def send_sms_nudge(phone_number: str, message: str) -> bool:
    """
    Sends an outbound SMS to the user via Africa's Talking.
    Used for welcome messages, quiz feedback, and module completion nudges.
    Raises an exception if the SMS fails so failures are always visible in logs.
    """
    if sms is None:
        logger.error(
            f"[SMS] Cannot send to {phone_number} — AT credentials not configured. "
            "Set AT_USERNAME and AT_API_KEY environment variables."
        )
        return False

    try:
        response = sms.send(message, [phone_number])
        logger.info(f"[SMS] Sent to {phone_number}: {response}")
        return True
    except Exception as e:
        logger.error(f"[SMS ERROR] Failed to send to {phone_number}: {e}")
        raise
