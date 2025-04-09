import imaplib
import email
import os
import time
import random
import traceback
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Jenny's Zoho Email Credentials
IMAP_SERVER = 'imap.zoho.com'
IMAP_PORT = 993
EMAIL_ACCOUNT = 'jenny@autoformchat.com'
EMAIL_PASSWORD = os.getenv("JENNY_PASSWORD")  # Using correct env var name
AI_API_KEY = os.getenv("OPENAI_API_KEY")

# Check required environment variables
if not EMAIL_PASSWORD:
    raise ValueError("JENNY_PASSWORD environment variable is not set")
if not AI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Enable debug logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def log_email_check():
    logger.info(f"Checking emails using account: {EMAIL_ACCOUNT}")
    logger.info(f"IMAP Server: {IMAP_SERVER}:{IMAP_PORT}")

client = OpenAI(api_key=AI_API_KEY)

# Knowledge Base - You can update this knowledge based on customer needs or frequently asked questions
knowledge_base = {
    "ai_automation":
    "AI Form Reply automates the process from website form submissions to scheduling meetings. It directly integrates with Google Workspace, answers common questions, qualifies leads, and books them into your calendar. This all happens automatically, saving you time and increasing sales!",
    "pricing":
    "Our solution is cost-effective for small businesses, with plans starting at $X per month. Please contact us for a custom quote depending on your needs.",
    "google_workspace":
    "AI Form Reply integrates seamlessly with Google Workspace. It uses Google Calendar for scheduling and Google Meet for virtual meetings.",
    "default":
    "I'm happy to help with any other questions! Feel free to ask about how AI Form Reply can help automate your lead management and scheduling process.",
}


def fetch_unread_emails():
    log_email_check()
    try:
        # Connect to Zoho IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        logger.info("Connected to IMAP server")
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    print("✅ Connected to Jenny's inbox!")

    # Select inbox and get unread emails
    mail.select('inbox')
    status, response = mail.search(None, '(UNSEEN)')
    unread_msg_nums = response[0].split()

    emails = []
    for num in unread_msg_nums:
        status, data = mail.fetch(num, '(RFC822)')
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg['subject']
        from_email = msg['from']
        body = msg.get_payload(decode=True).decode()

        emails.append({
            "subject": subject,
            "from_email": from_email,
            "body": body,
            "num": num
        })
    mail.logout()

    return emails
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []


def generate_reply(email_body):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are Jenny, a helpful AI assistant. Respond naturally and professionally to customer inquiries about AI Form Reply."},
                {"role": "user", "content": f"Please respond to this email: {email_body}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating reply: {e}")
        return "Thank you for your email. I'll get back to you shortly."


def reply_to_email(to_email, subject, reply_content):
    # Send the reply via the Zoho SMTP server (or another service like SendGrid or Resend)
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_email
    msg['Subject'] = subject

    body = MIMEText(reply_content, 'plain')
    msg.attach(body)

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ACCOUNT, to_email, msg.as_string())
        server.quit()

        print(f"✅ Replied to {to_email}")
    except Exception as e:
        print(f"❌ Failed to reply to {to_email}: {str(e)}")


def process_emails():
    try:
        logger.info("Starting email processing cycle")
        logger.info(f"Using email account: {EMAIL_ACCOUNT}")
        
        # Verify IMAP connection
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            logger.info("✅ IMAP connection successful")
            mail.logout()
        except Exception as e:
            logger.error(f"❌ IMAP connection failed: {str(e)}")
            return

        emails = fetch_unread_emails()
        logger.info(f"Found {len(emails)} unread emails")
        
        for email in emails:
            try:
                logger.info(f"📥 Processing email from {email['from_email']} with subject {email['subject']}")
                
                # Generate a reply based on the email content
                reply_content = generate_reply(email['body'])
                if reply_content:
                    reply_to_email(email['from_email'], email['subject'], reply_content)
                    logger.info(f"✅ Reply sent to {email['from_email']}")
                    
                    # Wait for 2-3 minutes before processing next email
                    wait_time = random.randint(120, 180)
                    logger.info(f"⏳ Waiting {wait_time} seconds before next email...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error processing individual email: {e}")
                continue
                
        logger.info("Completed email processing cycle")
    except Exception as e:
        logger.error(f"Error in process_emails: {e}")


if __name__ == "__main__":
    print("✨ Email responder system starting up...")
    while True:
        process_emails()
        time.sleep(30)  # Check every 30 seconds