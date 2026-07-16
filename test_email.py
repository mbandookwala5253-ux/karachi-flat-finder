import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def test_email():
    if not EMAIL_USER or not EMAIL_PASS:
        print("[ERROR] Email credentials not found in .env file!")
        print("Please verify EMAIL_USER and EMAIL_PASS are set.")
        return
        
    print(f"Sending test email from {EMAIL_USER} to {EMAIL_USER}...")
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🏠 Test Email Alert - Karachi Flat Finder"
        msg['From'] = f"Karachi Flat Finder Test <{EMAIL_USER}>"
        msg['To'] = EMAIL_USER
        
        html_body = """
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #090a0f; color: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #161926; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <h1 style="color: #6366f1; margin-top: 0;">🎉 Email Setup Success!</h1>
                <p>Hello!</p>
                <p>This is a test notification from your <b>Karachi Flat Finder Automation</b> tool.</p>
                <p>Your Gmail SMTP configurations (copied from the Maimoon Dental Care website) are working perfectly. You will now receive instant, rich email alerts whenever new flats or portions matching your search criteria are discovered!</p>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.05); margin: 20px 0;">
                <p style="font-size: 12px; color: #9ca3af;">Karachi Flat Finder Automation Engine</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.close()
        
        print("[SUCCESS] Test email successfully sent! Check your Gmail inbox.")
    except Exception as e:
        print(f"[FAILED] Error sending email: {e}")

if __name__ == "__main__":
    test_email()
