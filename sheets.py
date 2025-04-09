
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
    return sheet

def get_qualified_leads():
    try:
        sheet = connect_to_sheet()
        worksheet = sheet.worksheet("Sheet1")  # First tab where data is collected
        sent_worksheet = sheet.worksheet("Generated Emails")  # Second tab for email generation
        
        all_rows = worksheet.get_all_records()
        print(f"Found {len(all_rows)} rows in Sheet1")
        
        # Get websites that haven't been processed yet
        processed_websites = set(sent_worksheet.col_values(1)[1:])  # Skip header row
        qualified_leads = []

        for row in all_rows:
            website = row.get('Website', '').strip()
            if website and website not in processed_websites:
                qualified_leads.append(website)
                
        print(f"Found {len(qualified_leads)} new leads to process")
        return qualified_leads
    except Exception as e:
        print(f"Error in get_qualified_leads: {str(e)}")
        return []
