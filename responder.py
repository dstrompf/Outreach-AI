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
    "If you're ready to schedule a call, feel free to book a time that works best for you using this link: https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ36P0ABwQ5qKYkBrQ302KCunFUEoe23GadJe8JFnQnApuoDbID8QD26WJio1oDY5TqrEV2QfIQq",
    "default":
    "I'm happy to help with any other questions! Feel free to ask about how AI Form Reply can help automate your lead management and scheduling process.",
}


def fetch_unread_emails():
    log_email_check()
    try:
        # Connect to Zoho IMAP server with longer timeout
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        logger.info("Connected to IMAP server")
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        logger.info("✅ Connected to Jenny's inbox!")
        
        # Set longer socket timeout after connection
        mail.socket().settimeout(60)

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

                message_id = msg.get('Message-ID', '')
                references = msg.get('References', '')
                
                emails.append({
                    "subject": subject,
                    "from_email": from_email,
                    "body": body,
                    "num": num,
                    "message_id": message_id,
                    "references": references
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


def get_initial_correspondence(from_email):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_file("ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit")
        worksheet = sheet.worksheet("Generated Emails")
        
        # Find the row with matching email
        cell = worksheet.find(from_email)
        if cell:
            row = worksheet.row_values(cell.row)
            return {
                'website': row[0],
                'initial_email': row[1],
                'business_summary': row[2] if len(row) > 2 else ''
            }
    except Exception as e:
        logger.error(f"Error getting initial correspondence: {e}")
    return None

def generate_reply(email_body, from_email):
    try:
        # Extract first name from email if possible
        recipient_name = from_email.split('@')[0].split('.')[0].title() if '@' in from_email else ''
        
        # Get context from initial correspondence
        context = get_initial_correspondence(from_email)
        system_prompt = f"""You are Jenny, a helpful AI assistant for AI Form Reply.
        The recipient's name is '{recipient_name}' - use it naturally in the response if available.
        Never use 'Dear Customer' or similar generic greetings.
        Analyze the incoming email and provide a personalized, friendly response.
        Address their specific questions or concerns.
        Highlight relevant features based on their interests.
        If appropriate, guide them towards booking a meeting, but do so naturally.
        Keep responses professional yet conversational."""
        
        if context:
            system_prompt += f"\n\nContext about this business:\nWebsite: {context['website']}\nBusiness Summary: {context['business_summary']}\nInitial Outreach: {context['initial_email']}"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a friendly reply to this email that addresses their questions, references their business context when relevant, and encourages booking a meeting when appropriate: {email_body}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating reply: {e}")
        return "Thank you for your interest. I'd be happy to schedule a call to discuss how we can help automate your lead responses."


def reply_to_email(to_email, original_subject, reply_content, message_id=None, references=None):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import make_msgid

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_email
    msg['Subject'] = f"Re: {original_subject.replace('Re: ', '')}" if original_subject else "Re: Your inquiry"
    
    # Set proper threading headers
    if message_id:
        msg['In-Reply-To'] = message_id
        msg['References'] = message_id if not references else f"{references} {message_id}"
    
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

# Track processed message IDs to prevent duplicates
PROCESSED_IDS_FILE = "processed_messages.txt"

def load_processed_messages():
    try:
        with open(PROCESSED_IDS_FILE, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_processed_message(message_id):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(f"{message_id}\n")

processed_messages = load_processed_messages()

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
                
                # Skip system emails and already processed messages
                message_id = email.get('message_id', '')
                if is_system_email(email['subject'], email['from_email'], email['body']) or message_id in processed_messages:
                    logger.info("Skipping system/duplicate email")
                    continue
                save_processed_message(message_id)
                processed_messages.add(message_id)
                
                # Generate a reply based on the email content
                reply_content = generate_reply(email['body'], email['from_email'])
                if reply_content:
                    reply_to_email(
                        email['from_email'], 
                        email['subject'], 
                        reply_content,
                        email['message_id'],
                        email['references']
                    )
                    logger.info(f"✅ Reply sent to {email['from_email']}")
                    
                    # Wait for 3-5 minutes before processing next email
                    wait_time = random.randint(180, 300)
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