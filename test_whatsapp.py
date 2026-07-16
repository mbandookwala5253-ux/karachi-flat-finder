import os
import requests
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM", "whatsapp:+14155238886")
TWILIO_TO = os.getenv("TWILIO_TO", "whatsapp:+923111666121")

def test_send():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[ERROR] Twilio credentials not found in .env file!")
        print("Please create a .env file and fill in TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
        return
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    payload = {
        "From": TWILIO_FROM,
        "To": TWILIO_TO,
        "Body": "👋 Hello! This is a dummy test message from your Karachi Flat Finder Automation tool. Your WhatsApp integration is working perfectly!"
    }
    
    print(f"Sending test message to {TWILIO_TO}...")
    try:
        response = requests.post(
            url,
            data=payload,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=15
        )
        
        if response.status_code == 201:
            print(f"[SUCCESS] Message sent! SID: {response.json().get('sid')}")
        else:
            print(f"[FAILED] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    test_send()
