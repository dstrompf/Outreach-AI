import gspread
import time
import logging
import os
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
        SERVICE_ACCOUNT_FILE = "ai-outreach-sheets-access-24fe56ec7689.json"
        SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"

        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
            return []

        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(credentials)

        sheet = client.open_by_url(SPREADSHEET_URL)
        worksheet = sheet.worksheet("Sheet1")

        records = worksheet.get_all_records()
        logger.info(f"Successfully retrieved {len(records)} qualified leads")
        return records

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet not found: {SPREADSHEET_URL}")
        return []
    except gspread.exceptions.WorksheetNotFound:
        logger.error("Worksheet 'Sheet1' not found")
        return []
    except Exception as e:
        logger.error(f"Error getting qualified leads: {str(e)}")
        return []