# app/services/twilio_service.py
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_CALLER_ID
from utils.logger import setup_logging

# Initialize logging first
logger = setup_logging()

def send_sms(body: str, to: str) -> bool:
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(body=body, from_=TWILIO_CALLER_ID, to=to)
        logger.info("SMS sent to %s SID=%s", to, getattr(message, "sid", None))
        return True
    except Exception as e:
        logger.exception("Failed to send SMS to %s: %s", to, e)
        return False
