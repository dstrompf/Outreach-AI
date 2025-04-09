import random
import time
import gspread
from google.oauth2.service_account import Credentials
import resend
import os
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

# Config
BASE_EMAILS_PER_DAY = 5  # Starting point
MAX_EMAILS_PER_DAY = 200  # Maximum cap
WARM_UP_INCREASE_PERCENT = 15  # Daily increase percentage

def get_warmed_email_limit():
    try:
        # Use absolute path and ensure directory exists
        warm_up_file = os.path.join(os.path.dirname(__file__), 'email_warm_up.txt')
        
        try:
            with open(warm_up_file, 'r') as f:
                day_count = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            day_count = 1
            
        # Calculate warmed limit with 15% daily increase
        warmed_limit = min(
            MAX_EMAILS_PER_DAY,
            int(BASE_EMAILS_PER_DAY * (1 + (WARM_UP_INCREASE_PERCENT/100)) ** (day_count-1))
        )
        
        # Save incremented day count
        with open(warm_up_file, 'w') as f:
            f.write(str(day_count + 1))
            
        logger.info(f"Day {day_count}: Warmed limit set to {warmed_limit} emails")
        return warmed_limit
        
    except Exception as e:
        logger.error(f"Error in email warm-up tracking: {str(e)}")
        return BASE_EMAILS_PER_DAY  # Fallback to base limit

# Subject lines to rotate
SUBJECT_LINES = [
    "Quick question about your growth",
    "AI could help your team respond faster",
    "Loved what you're doing — quick idea",
    "Faster lead follow-up for your team",
    "Can I share something that might help?"
]


def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(
        "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
    )
    return sheet.worksheet("Generated Emails")


def send_cold_email(to_email, subject, body_html):
    try:
        resend.Emails.send({
            "from": "Jenny from AI Form Reply <info@aiformreply.com>",
            "to": [to_email],
            "subject": subject,
            "html": body_html,
            "reply_to": "jenny@autoformchat.com"
        })
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")


def run_cold_email_campaign():
    try:
        worksheet = connect_to_sheet()
        data = worksheet.get_all_records()

        daily_limit = get_warmed_email_limit()
        print(f"📈 Today's warmed email limit: {daily_limit}")
        
        # Filter for unsent leads with valid emails
        unsent_leads = [
            row for row in data 
            if row.get('Status') != 'Sent' 
            and row.get('Found Email')
            and '@' in row.get('Found Email', '')
        ]
        
        leads_to_send = unsent_leads[:daily_limit]
        print(f"📬 Found {len(unsent_leads)} unsent leads, sending {len(leads_to_send)} today...")
        
        for lead in leads_to_send:
            website = lead.get('Website')
            email_content = lead.get('Email Content')
            to_email = lead.get('Found Email')
            
            if not all([website, email_content, to_email]):
                print(f"❌ Missing data for {website}")
                continue

    for lead in leads_to_send:
        website = lead.get('Website')
        email_content = lead.get('Email Content')

        if not website or not email_content:
            continue

        to_email = f"info@{website.replace('https://', '').replace('www.', '').split('/')[0]}"
        subject = random.choice(SUBJECT_LINES)

        send_cold_email(to_email, subject, email_content)

        try:
            # Find the website row
            cell = worksheet.find(website)
            if cell:
                # Update Status column (4th column) to "Sent"
                worksheet.update_cell(cell.row, 4, "Sent")
                print(f"✅ Marked {website} as sent in row {cell.row}")
                
                # Verify the update
                updated_value = worksheet.cell(cell.row, 4).value
                if updated_value != "Sent":
                    print(f"⚠️ Update verification failed for {website}")
                    
            else:
                print(f"❌ Could not find row for website: {website}")
                
        except Exception as e:
            print(f"❌ Failed to mark {website} as sent: {str(e)}")
            time.sleep(2)  # Back off on API error

        time.sleep(random.randint(30, 90))


if __name__ == "__main__":
    run_cold_email_campaign()