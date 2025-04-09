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
    "booking":
    "If you're ready to schedule a call, feel free to book a time that works best for you using this link: https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ1k_oINRYACe0-7qy5wJzL4oZ6pdSs2FC5yzRyqEEv4guZxJg2u95EhW1BfpzP_Jp6C4eHYUxv2",
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
        logger.info("✅ Connected to Jenny's inbox!")

        # Select inbox and get unread emails
        mail.select('inbox')
        status, response = mail.search(None, '(UNSEEN)')
        unread_msg_nums = response[0].split()
        
        logger.info(f"Found {len(unread_msg_nums)} unread messages")
        
        emails = []
        for num in unread_msg_nums:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = msg['subject']
                from_email = msg['from']
                
                # Handle multipart messages
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                emails.append({
                    "subject": subject,
                    "from_email": from_email,
                    "body": body,
                    "num": num
                })
                logger.info(f"Processed email from: {from_email}")
            except Exception as e:
                logger.error(f"Error processing individual email: {e}")
                continue
                
        mail.logout()
        return emails
    except Exception as e:
        logger.error(f"Error in fetch_unread_emails: {e}")
        return []


def generate_reply(email_body):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are Jenny, a helpful AI assistant. Respond naturally and professionally to inquiries about AI Form Reply. Always try to guide the conversation towards booking a meeting, but do so naturally based on their interest level. Keep responses concise and focused."},
                {"role": "user", "content": f"Generate a friendly reply to this email that addresses their questions and encourages booking a meeting when appropriate: {email_body}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating reply: {e}")
        return "Thank you for your interest. I'd be happy to schedule a call to discuss how we can help automate your lead responses."


def reply_to_email(to_email, original_subject, reply_content):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_email
    msg['Subject'] = f"Re: {original_subject}" if original_subject else "Re: Your inquiry"

    # Always append booking link to responses
    booking_link = knowledge_base.get("booking", "").split(":")[-1].strip()
    full_response = f"{reply_content}\n\nWould you like to discuss this further? You can book a time that works best for you here:{booking_link}"
    
    body = MIMEText(full_response, 'plain')
    msg.attach(body)

    try:
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ACCOUNT, to_email, msg.as_string())
        server.quit()

        print(f"✅ Replied to {to_email}")
    except Exception as e:
        print(f"❌ Failed to reply to {to_email}: {str(e)}")


def is_system_email(subject, from_email, body):
    system_indicators = [
        "mailer-daemon",
        "postmaster",
        "no-reply",
        "noreply",
        "do-not-reply",
        "automated-message",
        "invoice",
        "confirmation",
        "subscription",
        "payment",
        "order"
    ]
    
    from_lower = from_email.lower() if from_email else ""
    subject_lower = subject.lower() if subject else ""
    
    # Block emails from aiformreply.com domain
    if "@aiformreply.com" in from_lower:
        return True
    
    # Check both subject and sender for system indicators
    return any(indicator in from_lower or indicator in subject_lower for indicator in system_indicators)

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
                
                # Skip system emails
                if is_system_email(email['subject'], email['from_email'], email['body']):
                    logger.info("Skipping system email")
                    continue
                
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