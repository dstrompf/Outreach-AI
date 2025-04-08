import os
from resend import Resend

resend = Resend(api_key=os.getenv("RESEND_API_KEY"))

def send_test_email():
    params = {
        "from": "AI Form Reply <info@aiformreply.com>",
        "to": ["dstrompf@gmail.com"],  # <-- Replace with your real email
        "subject": "Test Email from AI Outreach System",
        "html": "<p>Hi there! 🎯<br>This is a test email sent from your new domain <strong>aiformreply.com</strong> using Resend. Everything is working!</p>"
    }
    resend.emails.send(params)

# Call the function
send_test_email()