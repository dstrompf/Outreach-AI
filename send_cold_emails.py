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
        response = resend.Emails.send({
            "from": "Jenny from AI Form Reply <info@aiformreply.com>",
            "to": [to_email],
            "subject": subject,
            "html": body_html,
            "reply_to": "jenny@autoformchat.com"
        })
        print(f"✅ Email sent to {to_email} with ID: {response.id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False

def get_warmed_email_limit():
    try:
        warm_up_file = 'email_warm_up.txt'
        try:
            with open(warm_up_file, 'r') as f:
                day_count = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            day_count = 1

        warmed_limit = min(
            MAX_EMAILS_PER_DAY,
            int(BASE_EMAILS_PER_DAY * (1 + (WARM_UP_INCREASE_PERCENT/100)) ** (day_count-1))
        )

        with open(warm_up_file, 'w') as f:
            f.write(str(day_count + 1))

        print(f"Day {day_count}: Warmed limit set to {warmed_limit} emails")
        return warmed_limit

    except Exception as e:
        print(f"Error in email warm-up tracking: {str(e)}")
        return BASE_EMAILS_PER_DAY

def run_cold_email_campaign():
    try:
        worksheet = connect_to_sheet()
        data = worksheet.get_all_records()

        #No change needed here.

        daily_limit = get_warmed_email_limit()
        print(f"📈 Today's warmed email limit: {daily_limit}")

        leads_to_send = data[:daily_limit] #Send all leads within the daily limit.
        print(f"📬 Found {len(data)} leads, sending {len(leads_to_send)} today...")

        for lead in leads_to_send:
            website = lead.get('Website')
            email_content = lead.get('Email Content')
            to_email = lead.get('Found Email')
            status = lead.get('Status')

            if not all([website, email_content, to_email]):
                print(f"❌ Missing data for {website}")
                continue

            if status != "Sent": #Check if email is already sent
                subject = random.choice(SUBJECT_LINES)
                if send_cold_email(to_email, subject, email_content):
                    try:
                        cell = worksheet.find(website)
                        if cell:
                            worksheet.update_cell(cell.row, 4, "Sent")
                            print(f"✅ Marked {website} as sent in row {cell.row}")
                    except Exception as e:
                        print(f"❌ Failed to mark {website} as sent: {str(e)}")
                        time.sleep(2)
            else:
                print(f"Email already sent to {website}") #Inform if already sent

            time.sleep(random.randint(30, 90))

    except Exception as e:
        print(f"❌ Campaign failed: {str(e)}")

if __name__ == "__main__":
    run_cold_email_campaign()