import imaplib
import email
import os
import time
import random
import traceback
from dotenv import load_dotenv
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import logging

# Load environment variables
load_dotenv()

# Jenny's Zoho Email Credentials
IMAP_SERVER = 'imap.zoho.com'
IMAP_PORT = 993
SMTP_SERVER = 'smtp.zoho.com'
SMTP_PORT = 587
EMAIL_ACCOUNT = 'jenny@autoformchat.com'
EMAIL_PASSWORD = os.getenv("JENNY_PASSWORD")
AI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check required environment variables
if not EMAIL_PASSWORD:
    raise ValueError("JENNY_PASSWORD environment variable is not set")
if not AI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=AI_API_KEY)

# Knowledge Base
knowledge_base = {
    "ai_automation": "AI Form Reply automates the process from website form submissions to scheduling meetings. It directly integrates with Google Workspace, answers common questions, qualifies leads, and books them into your calendar.",
    "pricing": "Our solution is cost-effective for small businesses. Please schedule a call to discuss pricing for your specific needs.",
    "google_workspace": "AI Form Reply integrates seamlessly with Google Workspace. It uses Google Calendar for scheduling and Google Meet for virtual meetings.",
    "booking": "If you're ready to schedule a call, feel free to book a time that works best for you using this link: https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ36P0ABwQ5qKYkBrQ302KCunFUEoe23GadJe8JFnQnApuoDbID8QD26WJio1oDY5TqrEV2QfIQq",
    "default": "I'm happy to help with any other questions about how AI Form Reply can help automate your lead management."
}

def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        credentials = Credentials.from_service_account_file(
            "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
        client = gspread.authorize(credentials)
        
        # Test connection and refresh if needed
        try:
            client.list_spreadsheet_files()
        except Exception:
            logger.warning("Refreshing credentials...")
            credentials = Credentials.from_service_account_file(
                "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
            client = gspread.authorize(credentials)
            
        sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
        )
        return sheet
    except Exception as e:
        logger.error(f"Failed to connect to sheet: {str(e)}")
        return None

def find_emails_on_page(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        emails = set()

        # Find mailto links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip()
                if '@' in email and '.' in email:
                    emails.add(email)

        return list(emails)
    except Exception as e:
        logger.error(f"Error finding emails on {url}: {str(e)}")
        return []

def save_found_email(website, email):
    try:
        sheet = connect_to_sheet()
        worksheet = sheet.worksheet("Generated Emails")

        # Find row with website
        cell = worksheet.find(website)
        if cell:
            worksheet.update_cell(cell.row, 3, email)  # Update email column
            logger.info(f"Updated email for {website}: {email}")
    except Exception as e:
        logger.error(f"Error saving email for {website}: {str(e)}")

def send_email(to_email, subject, content):
    try:
        msg = MIMEMultipart()
        msg['From'] = "Jenny from AI Form Reply <info@aiformreply.com>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Reply-To'] = "jenny@autoformchat.com"

        body = MIMEText(content, 'plain')
        msg.attach(body)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False

def process_website(website_url, business_name=""):
    emails = find_emails_on_page(website_url)

    if not emails:
        logger.info(f"No valid emails found for {website_url}")
        return None

    # Use the first found email
    email = emails[0]
    save_found_email(website_url, email)
    return email

def process_emails():
    logger.info("Starting email processing cycle")
    try:
        sheet = connect_to_sheet()
        worksheet = sheet.worksheet("Generated Emails")
        rows = worksheet.get_all_records()

        for row in rows:
            website = row.get('Website', '')
            email_content = row.get('Email Content', '')
            status = row.get('Status', '')

            if not website or not email_content or status == 'Sent':
                continue

            # Find or validate email
            email = process_website(website)
            if not email:
                logger.info(f"Skipping {website} - no valid email found")
                continue

            # Send email
            if send_email(email, "Quick question about your Google Workspace setup", email_content):
                try:
                    cell = worksheet.find(website)
                    worksheet.update_cell(cell.row, 4, "Sent")
                    time.sleep(random.randint(30, 60))
                except Exception as e:
                    logger.error(f"Error updating status for {website}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in process_emails: {str(e)}")

if __name__ == "__main__":
    logger.info("✨ Email responder system starting up...")
    while True:
        process_emails()
        time.sleep(300)  # Wait 5 minutes between cycles