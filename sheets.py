
import gspread
import time
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
        
        # Process in batches of 100 to avoid rate limits
        batch_size = 100
        qualified_leads = []
        processed_websites = set(sent_worksheet.col_values(1)[1:])  # Skip header row
        
        # Get total rows count
        all_rows = worksheet.get_all_records()
        print(f"Found {len(all_rows)} rows in Sheet1")
        
        # Process in batches
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1} of {(len(all_rows)//batch_size) + 1}")
            
            for row in batch:
                website = row.get('Website', '').strip()
                google_workspace = str(row.get('Google Workspace', '')).strip().upper() == 'YES'
                
                if website and website not in processed_websites and google_workspace:
                    qualified_leads.append({
                        'website': website,
                        'business_name': row.get('Business Name', '').strip(),
                        'has_workspace': True
                    })
            
            # Add delay between batches to avoid rate limits
            if i + batch_size < len(all_rows):
                time.sleep(2)  # Wait 2 seconds between batches
                
        print(f"Found {len(qualified_leads)} new Google Workspace leads to process")
        return qualified_leads
    except Exception as e:
        print(f"Error in get_qualified_leads: {str(e)}")
        return []
