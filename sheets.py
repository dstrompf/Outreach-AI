
import gspread
from google.oauth2.service_account import Credentials

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
    worksheet = connect_to_sheet()
    all_rows = worksheet.get_all_records()
    qualified_leads = []

    for row in all_rows:
        has_workspace = str(row.get('Google Workspace', '')).strip().upper() == 'YES'
        has_email = bool(row.get('Email', '').strip())
        website = row.get('Website', '').strip()

        if has_workspace and has_email and website:
            qualified_leads.append(website)

    return qualified_leads
