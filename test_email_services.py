
import os
from dotenv import load_dotenv
import resend
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")
ZOHO_PASSWORD = os.getenv("JENNY_PASSWORD")

def test_resend():
    try:
        resend.Emails.send({
            "from": "Jenny from AI Form Reply <info@aiformreply.com>",
            "to": ["ds@gam0.com"],
            "subject": "Test Email via Resend",
            "html": "<p>This is a test email sent via Resend service</p>",
            "reply_to": "jenny@autoformchat.com"
        })
        print("✅ Resend test email sent successfully")
    except Exception as e:
        print(f"❌ Resend test failed: {str(e)}")

def test_zoho():
    try:
        msg = MIMEMultipart()
        msg['From'] = 'jenny@autoformchat.com'
        msg['To'] = 'ds@gam0.com'
        msg['Subject'] = 'Test Email via Zoho SMTP'
        
        body = MIMEText('This is a test email sent via Zoho SMTP', 'plain')
        msg.attach(body)
        
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login('jenny@autoformchat.com', ZOHO_PASSWORD)
        server.sendmail('jenny@autoformchat.com', 'ds@gam0.com', msg.as_string())
        server.quit()
        print("✅ Zoho test email sent successfully")
    except Exception as e:
        print(f"❌ Zoho test failed: {str(e)}")

if __name__ == "__main__":
    print("Testing both email services...")
    test_resend()
    test_zoho()
