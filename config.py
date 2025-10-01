# app/config.py
from dotenv import load_dotenv
import os

load_dotenv()

TWILIO_ACCOUNT_SID = "ACaaaa83e9255e4d10cc5ca3168a510b07"
TWILIO_AUTH_TOKEN = "11b64e53dc4b1b3bcdcb165fae510792"
PUBLIC_URL = "https://9e1f23fea783.ngrok-free.app" 
TWILIO_CALLER_ID = "+16093090331"  # Your Twilio number
VOICE_VOICE = "Google.en-IN-Chirp3-HD-Puck"