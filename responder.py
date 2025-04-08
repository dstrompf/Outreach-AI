import imaplib
import email
import os
import time
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
    "I’m happy to help with any other questions! Feel free to ask about how AI Form Reply can help automate your lead management and scheduling process.",
}


def fetch_unread_emails():
    # Connect to Zoho IMAP server
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
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


def generate_reply(message, website=""):
    """Generate a reply from Jenny based on the message content."""
    prompt = f"""
    You are an AI assistant for a marketing agency. You respond in a friendly and professional manner.
    If the email mentions Google Workspace, explain that our AI Form Reply integrates directly with it, automating form-to-lead conversions and booking meetings.

    Here’s the message:
    {message}

    If the user asks about the AI automation process, explain it in simple terms, and mention Google Workspace integration. 
    Be sure to offer a free consultation or demo if they’re interested.
    Use the website info to sound more personalized (if available).

    Respond with an email reply.
    """

    # Use OpenAI to generate a personalized response
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role":
            "system",
            "content":
            "You are a friendly and helpful outreach assistant."
        }, {
            "role": "user",
            "content": prompt
        }])

    return response.choices[0].message.content


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
    emails = fetch_unread_emails()
    for email in emails:
        print(
            f"📥 New email from {email['from_email']} with subject {email['subject']}"
        )

        # Generate a reply based on the email content
        reply_content = generate_reply(email['body'])
        reply_to_email(email['from_email'], email['subject'], reply_content)

        # Wait for 5 to 10 minutes before sending the reply
        print("⏳ Waiting before replying...")
        time.sleep(5 * 60)  # Wait 5 minutes (300 seconds)


if __name__ == "__main__":
    while True:
        process_emails()
