
import gspread
import time
import logging
from google.oauth2.service_account import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        if not sheet:
            logger.error("Failed to connect to sheet")
            return []
            
        worksheet = sheet.worksheet("Sheet1")
        sent_worksheet = sheet.worksheet("Generated Emails")

        # Get processed websites efficiently
        try:
            processed_websites = set(sent_worksheet.col_values(1)[1:])
        except Exception as e:
            logger.error(f"Error getting processed websites: {e}")
            processed_websites = set()

        # Get only needed columns
        try:
            websites = worksheet.col_values(1)[1:]  # Assuming Website is first column
            business_names = worksheet.col_values(2)[1:]  # Assuming Business Name is second column
            workspace_status = worksheet.col_values(3)[1:]  # Assuming Google Workspace is third column
            
            qualified_leads = []
            for website, business_name, workspace in zip(websites, business_names, workspace_status):
                website = website.strip()
                if website and website not in processed_websites and workspace.strip().upper() == 'YES':
                    qualified_leads.append({
                        'website': website,
                        'business_name': business_name.strip(),
                        'has_workspace': True
                    })
            
            logger.info(f"Found {len(qualified_leads)} qualified leads")
            return qualified_leads

        except Exception as e:
            logger.error(f"Error processing sheet data: {e}")
            return []
            
    except Exception as e:
        logger.error(f"Error in get_qualified_leads: {str(e)}")
        return []
                
        print(f"Found {len(qualified_leads)} new Google Workspace leads to process")
        return qualified_leads
    except Exception as e:
        print(f"Error in get_qualified_leads: {str(e)}")
        return []
