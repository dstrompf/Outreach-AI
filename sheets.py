
import gspread
import time
import logging
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sheets_connection():
    try:
        sheet = connect_to_sheet()
        if sheet:
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
        if not sheet:
            logger.error("Failed to connect to sheet")
            return []
            
        # Get main worksheet and sent worksheet
        worksheet = sheet.worksheet("Sheet1")
        sent_worksheet = sheet.worksheet("Generated Emails")

        # Get already processed websites
        processed_websites = set()
        try:
            processed_websites = set(sent_worksheet.col_values(1)[1:])  # Skip header
        except Exception as e:
            logger.error(f"Error getting processed websites: {e}")

        # Get all records with proper column mapping
        all_records = worksheet.get_all_records()
        qualified_leads = []

        for record in all_records:
            website = record.get('Website', '').strip()
            business_name = record.get('Business Name', '').strip()
            google_workspace = str(record.get('Google Workspace', '')).strip().upper()

            if (website and 
                website not in processed_websites and 
                google_workspace == 'YES'):
                
                qualified_leads.append({
                    'website': website,
                    'business_name': business_name,
                    'has_workspace': True
                })

        logger.info(f"Found {len(qualified_leads)} qualified leads")
        return qualified_leads

    except Exception as e:
        logger.error(f"Error in get_qualified_leads: {str(e)}")
        return []
