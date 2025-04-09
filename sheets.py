
import gspread
from google.oauth2.service_account import Credentials

def test_sheets_connection():
    try:
        worksheet = connect_to_sheet()
        if worksheet:
            logger.info("✅ Successfully connected to Google Sheets")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Sheets: {e}")
        return False

def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(
        "ai-outreach-sheets-access-24fe56ec7689.json",
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit#gid=0"
    )
    worksheet = sheet.sheet1
    return worksheet

def get_qualified_leads():
    sheet = connect_to_sheet()
    worksheet = sheet.sheet1
    sent_worksheet = sheet.worksheet("Generated Emails")
    
    all_rows = worksheet.get_all_records()
    sent_emails = set(email.strip() for email in sent_worksheet.col_values(3)[1:] if email.strip())  # Column C contains found emails
    qualified_leads = []

    for row in all_rows:
        has_workspace = str(row.get('Google Workspace', '')).strip().upper() == 'YES'
        website = row.get('Website', '').strip()
        
        # Check if website's email is not in sent_emails
        if has_workspace and website:
            qualified_leads.append(website)

    return qualified_leads
