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
MAX_EMAILS_PER_DAY = 10

# Subject lines to rotate
SUBJECT_LINES = [
    "Quick question about your growth",
    "AI could help your team respond faster",
    "Loved what you're doing — quick idea",
    "Faster lead follow-up for your team",
    "Can I share something that might help?"
]


# Setup Google Sheets access
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
            "reply_to": "jenny@autoformchat.com"  # 👈 Important
        })
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")


def run_cold_email_campaign():
    worksheet = connect_to_sheet()
    data = worksheet.get_all_records()

    # Find leads that haven't been sent yet
    unsent_leads = [row for row in data if not row.get('Sent?')]

    # Limit to MAX_EMAILS_PER_DAY
    leads_to_send = unsent_leads[:MAX_EMAILS_PER_DAY]
    print(f"📬 Sending {len(leads_to_send)} cold emails today...")

    for lead in leads_to_send:
        website = lead.get('Website')
        email_content = lead.get('Email Content')

        if not website or not email_content:
            continue

        # Construct a fake email address based on website (for now)
        to_email = f"info@{website.replace('https://', '').replace('www.', '').split('/')[0]}"

        # Pick random subject
        subject = random.choice(SUBJECT_LINES)

        # Send the email
        send_cold_email(to_email, subject, email_content)

        # Mark as sent in Google Sheet
        try:
            cell = worksheet.find(website)
            worksheet.update_cell(
                cell.row, cell.col + 2,
                "Yes")  # 'Sent?' column should be 2 columns after Website
            print(f"✅ Marked {website} as sent.")
        except Exception as e:
            print(f"❌ Failed to mark {website} as sent: {str(e)}")

        # Random delay between emails
        time.sleep(random.randint(30, 90))


if __name__ == "__main__":
    run_cold_email_campaign()
