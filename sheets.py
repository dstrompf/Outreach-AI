import gspread
from google.oauth2.service_account import Credentials


# Connect to Google Sheet
def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(
        "ai-outreach-sheets-access-24fe56ec7689.json",  # <<< replace with your JSON key filename
        scopes=scopes)

    client = gspread.authorize(credentials)

    # Open the Google Sheet
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/your-sheet-id-here"
    )  # <<< replace with your sheet URL

    # Choose the worksheet (tab)
    worksheet = sheet.sheet1

    return worksheet


def get_qualified_leads():
    worksheet = connect_to_sheet()

    # Get all the data
    all_rows = worksheet.get_all_records()

    qualified_leads = []

    for row in all_rows:
        has_workspace = row.get('Has Google Workspace') == 'TRUE'
        has_email = row.get('Found Email') == 'TRUE'
        website = row.get('Website')

        # Only keep rows where both conditions are true
        if has_workspace and has_email and website:
            qualified_leads.append(website)

    return qualified_leads
