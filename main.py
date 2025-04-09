from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time # Added import for time module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI
import os
from dotenv import load_dotenv
from sheets import get_qualified_leads
import gspread
from google.oauth2.service_account import Credentials
from apscheduler.schedulers.background import BackgroundScheduler
import resend

# ----- SETUP -----
load_dotenv()
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")


# ----- MODELS -----
class ScrapeRequest(BaseModel):
    url: str


class SummarizeRequest(BaseModel):
    text: str


class GenerateEmailRequest(BaseModel):
    business_name: str
    summary: str


# ----- HELPERS -----
def save_generated_email(website, email_content, found_email=""):
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
    worksheet = sheet.worksheet("Generated Emails")
    existing_websites = worksheet.col_values(1)
    if website in existing_websites:
        print(f"Website {website} already exists. Skipping save.")
        return
    worksheet.append_row([website, email_content, found_email,
                          ""])  # Website | Email | Email found | Status
    print(f"Saved new website: {website}")


def send_daily_report(count):
    try:
        resend.Emails.send({
            "from": "Good At Marketing <info@aiformreply.com>",
            "to": ["YOUR_PERSONAL_EMAIL@gmail.com"],
            "subject": "Daily AI Outreach Report",
            "html":
            f"<p>Today's AI Outreach Campaign completed successfully.<br><strong>New emails generated: {count}</strong></p>",
            "reply_to": "jenny@autoformchat.com"
        })
        print("✅ Daily report email sent.")
    except Exception as e:
        print(f"❌ Failed to send daily report email: {str(e)}")


def find_internal_links(soup, base_url):
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/') or base_url in href:
            if any(x in href.lower() for x in ['contact', 'about', 'team']):
                full_url = urljoin(base_url, href)
                links.append(full_url)
    return links[:3]  # Limit to 3 most relevant pages


def send_outreach_email(to_email, email_content):
    try:
        resend.Emails.send({
            "from": "Jenny from AI Form Reply <info@aiformreply.com>",
            "to": [to_email],
            "subject": "Helping You Close More Leads Faster 🚀",
            "html": email_content,
            "reply_to": "jenny@autoformchat.com"
        })
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")


def mark_as_sent(website):
    try:
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
        worksheet = sheet.worksheet("Generated Emails")
        websites = worksheet.col_values(1)
        for idx, site in enumerate(websites):
            if site == website:
                worksheet.update_cell(idx + 1, 4, "Sent")  # Column 4 = Status
                print(f"🔵 Marked {website} as Sent")
                break
    except Exception as e:
        print(f"❌ Failed to mark {website} as sent: {str(e)}")


def send_outreach_emails_daily():
    try:
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
        worksheet = sheet.worksheet("Generated Emails")
        all_rows = worksheet.get_all_records()
        emails_sent = 0

        for row in all_rows:
            if emails_sent >= 10:
                break

            website = row.get('Website')
            email_content = row.get('Email')
            email_found = row.get('Email found', '')
            status = row.get('Status', '')

            if status != "Sent" and website and email_content and email_found:
                send_outreach_email(email_found, email_content)
                mark_as_sent(website)
                emails_sent += 1

        print(f"✅ Daily outreach complete. {emails_sent} emails sent.")
    except Exception as e:
        print(f"❌ Failed to send outreach emails: {str(e)}")


# ----- ROUTES -----
@app.get("/")
def home():
    return {"message": "AI Outreach System Online"}

@app.get("/system-health")
def system_health():
    from sheets import test_sheets_connection
    try:
        sheet_status = test_sheets_connection()
        scheduler_status = scheduler.running
        last_run = scheduler.get_job('campaign').next_run_time if scheduler.get_job('campaign') else None
        return {
            "google_sheets": "connected" if sheet_status else "disconnected",
            "scheduler": "running" if scheduler_status else "stopped",
            "cron_job": "scheduled for 9:00 AM daily",
            "last_campaign": last_run
        }
    except Exception as e:
        return {
            "error": str(e),
            "scheduler": "running" if scheduler.running else "stopped"
        }


@app.get("/test_leads")
def test_leads():
    try:
        logger.info("Starting test_leads endpoint check")
        qualified = get_qualified_leads()
        if not qualified:
            logger.warning("No qualified leads found")
            return {"status": "No qualified leads found", "qualified_leads": []}
        
        total_leads = len(qualified)
        workspace_leads = sum(1 for lead in qualified if lead.get('has_workspace'))
        
        # Log the first 3 leads for verification
        for idx, lead in enumerate(qualified[:3]):
            logger.info(f"Sample lead {idx + 1}: Website={lead.get('website')}, Has Workspace={lead.get('has_workspace')}")
        
        logger.info(f"Total leads: {total_leads}, Workspace leads: {workspace_leads}")
        return {
            "status": "success", 
            "total_leads": total_leads,
            "workspace_leads": workspace_leads,
            "sample_leads": qualified[:3]
        }
    except Exception as e:
        logger.error(f"Error in test_leads endpoint: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/scrape")
def scrape_website(request: ScrapeRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        collected_text = ""
        collected_emails = set()

        # Get main page
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Store the entire HTML content
        html_content = response.text
        
        # Use regex to find email patterns in the entire HTML
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, html_content)
        collected_emails.update(found_emails)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        collected_text += " ".join([tag.get_text() for tag in soup.find_all(["h1", "h2", "p", "div", "span", "a"])])

        # Find emails on main page
        for a in soup.find_all('a', href=True):
            if "mailto:" in a['href'].lower():
                email = a['href'].replace('mailto:', '').split('?')[0].strip()
                if '@' in email and '.' in email:
                    collected_emails.add(email)

        # Look for contact form fields that might contain email information
        contact_inputs = soup.find_all('input', {'type': ['email', 'text']})
        for input_field in contact_inputs:
            placeholder = input_field.get('placeholder', '').lower()
            name = input_field.get('name', '').lower()
            if 'email' in placeholder or 'email' in name:
                parent_div = input_field.find_parent('div')
                if parent_div:
                    text_content = parent_div.get_text()
                    email_matches = re.findall(email_pattern, text_content)
                    collected_emails.update(email_matches)

        # Check contact and about pages
        contact_links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if any(x in href for x in ['contact', 'about', 'team', 'locations']):
                if href.startswith('/'):
                    href = request.url.rstrip('/') + '/' + href.lstrip('/')
                elif not href.startswith('http'):
                    href = request.url.rstrip('/') + '/' + href
                contact_links.append(href)

        # Visit contact pages
        for link in set(contact_links[:3]):  # Limit to 3 pages
            try:
                resp = requests.get(link, headers=headers, timeout=10)
                sub_soup = BeautifulSoup(resp.text, "html.parser")
                
                # Get text content
                collected_text += " ".join([tag.get_text() for tag in sub_soup.find_all(["h1", "h2", "p"])])
                
                # Check for emails in contact page
                for a in sub_soup.find_all('a', href=True):
                    if "mailto:" in a['href'].lower():
                        email = a['href'].replace('mailto:', '').split('?')[0].strip()
                        if '@' in email and '.' in email:
                            collected_emails.add(email)
                
                # Look for email patterns in text
                text = sub_soup.get_text()
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found_emails = re.findall(email_pattern, text)
                collected_emails.update(found_emails)
                
            except Exception as e:
                logger.error(f"Error scraping contact page {link}: {str(e)}")
                continue


        links = find_internal_links(soup, request.url)
        important_links = [
            link for link in links
            if any(x in link.lower() for x in ["about", "contact", "services"])
        ]

        for link in important_links[:3]:
            try:
                sub_resp = requests.get(link, headers=headers, timeout=10)
                sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                collected_text += " ".join([
                    tag.get_text()
                    for tag in sub_soup.find_all(["h1", "h2", "p"])
                ])
                for a in sub_soup.find_all('a', href=True):
                    if "mailto:" in a['href']:
                        collected_emails.add(a['href'].replace('mailto:', ''))
            except:
                continue

        return {"text": collected_text, "emails": list(collected_emails)} if collected_emails else {"error": "No emails found"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/summarize")
def summarize(request: SummarizeRequest):
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Summarize the following website content in 3 sentences."
                }, {
                    "role": "user",
                    "content": request.text
                }])
            return {"summary": response.choices[0].message.content}
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            return {"error": str(e)}
    return {"error": "Max retries exceeded"}


@app.post("/generate_email")
def generate_email(request: GenerateEmailRequest):
    try:
        prompt = f"""You are an AI outreach assistant specializing in Google Workspace solutions.

Task: Write a personalized cold email for {request.business_name}. They are a luxury spa/wellness business using Google Workspace.

Key points:
- Mention their focus on premium spa services and client experience
- Show how AI form automation can provide 24/7 instant responses to booking inquiries
- Highlight seamless integration with their existing Google Workspace setup
- Keep tone sophisticated and professional, matching their luxury brand
- Focus on how this helps capture more bookings by responding instantly

Based on this business summary: {request.summary}"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role":
                "system",
                "content":
                "You are a friendly outreach email assistant helping a marketing agency offer AI solutions to businesses."
            }, {
                "role": "user",
                "content": prompt
            }])
        return {"email": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}


@app.get("/run-campaign")
def run_campaign():
    try:
        # Add initial delay to reset rate limits
        time.sleep(30)
        
        qualified_leads = get_qualified_leads()
        logger.info(f"Found {len(qualified_leads)} qualified leads")
        emails_generated = 0

        # Process just one lead to test
        for lead in qualified_leads[:1]:
            try:
                website = lead['website']
                logger.info(f"Processing website: {website}")

                # Add longer delay between API calls
                time.sleep(15)
                
                scrape_resp = scrape_website(ScrapeRequest(url=website))
                if 'error' in scrape_resp:
                    logger.error(f"Scraping failed for {website}: {scrape_resp['error']}")
                    continue

                if not scrape_resp.get('emails'):
                    logger.info(f"No emails found for {website}")
                    continue

                # Add delay before OpenAI call
                time.sleep(5)

                # Attempt to connect to Google Sheets
                try:
                    scopes = [
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive"
                    ]
                    credentials = Credentials.from_service_account_file(
                        "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
                    gc = gspread.authorize(credentials)
                    
                    # Test connection and refresh if needed
                    gc.list_spreadsheet_files()
        except Exception as e:
            logger.warning("Refreshing sheets connection...")
            credentials = Credentials.from_service_account_file(
                "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
            gc = gspread.authorize(credentials)
        sheet = gc.open_by_url(
            "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
        )
        generated_emails_sheet = sheet.worksheet("Generated Emails")
        
        # Get existing websites to avoid duplicates
        existing_websites = generated_emails_sheet.col_values(1)[1:]  # Skip header
        logger.info(f"Found {len(existing_websites)} existing processed websites")

        for lead in qualified_leads[:5]:  # Process 5 at a time
            try:
                website = lead['website']
                if website in existing_websites:
                    logger.info(f"Skipping {website} - already processed")
                    continue
                    
                logger.info(f"Processing website: {website}")

                scrape_resp = scrape_website(ScrapeRequest(url=website))
                if 'error' in scrape_resp:
                    logger.error(f"Scraping failed for {website}: {scrape_resp['error']}")
                    continue

                if not scrape_resp.get('emails'):
                    logger.info(f"No emails found for {website}")
                    continue

                time.sleep(2)  # Delay between API calls

                # More conservative retry logic
                max_retries = 2
                last_error = None
                for retry in range(max_retries):
                    try:
                        summarize_resp = summarize(SummarizeRequest(text=scrape_resp['text']))
                        if 'error' not in summarize_resp:
                            break
                        last_error = summarize_resp.get('error')
                        wait_time = (2 ** retry) * 60  # Longer waits: 60s, 120s
                        logger.info(f"Rate limited, waiting {wait_time} seconds before retry {retry + 1}")
                        time.sleep(wait_time)
                    except Exception as e:
                        last_error = str(e)
                        logger.error(f"Error during summarization: {str(e)}")
                        time.sleep(60)

                if 'error' in summarize_resp or last_error:
                    return {"status": "Rate limited", "message": "OpenAI API rate limit reached. Please try again in a few minutes."}

                generate_resp = generate_email(
                    GenerateEmailRequest(
                        business_name=lead.get('business_name', website),
                        summary=summarize_resp['summary']
                    )
                )

                if 'error' in generate_resp:
                    logger.error(f"Email generation failed for {website}")
                    continue

                first_email = scrape_resp['emails'][0]
                try:
                    time.sleep(1)  # Add delay before API call
                    generated_email = generate_resp['email']
                    first_email = scrape_resp['emails'][0]

                    logger.info(f"Writing to sheet - Website: {website}, Email: {first_email}")
                    try:
                        # Use existing sheet connection with retry logic
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                generated_emails_sheet.append_row([
                                    website,
                                    generated_email,
                                    first_email,
                                    "Pending"  # Status column
                                ])
                                existing_websites.append(website)  # Update local cache
                                emails_generated += 1
                                logger.info(f"Successfully saved email for {website}")
                                break
                            except Exception as sheet_error:
                                if attempt == max_retries - 1:
                                    raise sheet_error
                                logger.warning(f"Retrying sheet write for {website}, attempt {attempt + 1}")
                                time.sleep(2)
                    except Exception as e:
                        logger.error(f"Failed to write to sheet for {website}: {str(e)}")
                        continue
                except Exception as e:
                    logger.error(f"Failed to save generated email for {website}: {str(e)}")
                    continue
                logger.info(f"Successfully processed {website}")

            except Exception as e:
                logger.error(f"Error processing {website}: {str(e)}")
                continue

        logger.info(f"Campaign complete. Generated {emails_generated} emails.")
        send_daily_report(emails_generated)
        send_outreach_emails_daily()
        return {"status": "Campaign complete.", "emails_generated": emails_generated}
    except Exception as e:
        return {"error": str(e)}


# ----- SCHEDULER -----
scheduler = BackgroundScheduler()


def scheduled_campaign():
    logger.info("🔄 Starting scheduled campaign...")
    try:
        result = run_campaign()
        logger.info(f"✅ Campaign completed: {result}")
    except Exception as e:
        logger.error(f"❌ Campaign failed: {e}")

scheduler.add_job(scheduled_campaign, 'cron', hour=9, minute=0, id='campaign')


scheduler.add_job(scheduled_campaign, 'cron', hour=9, minute=0)
scheduler.start()

# ----- MAIN -----
@app.get("/test_email_scraping")
def test_email_scraping():
    test_websites = [
        "https://www.python.org/about/help/",
        "https://www.apache.org/foundation/contact.html",
        "https://www.fsf.org/about/contact/"
    ]
    results = []

    for website in test_websites:
        try:
            scrape_resp = scrape_website(ScrapeRequest(url=website))
            results.append({
                "website": website,
                "success": "error" not in scrape_resp,
                "emails_found": scrape_resp.get("emails", []),
                "error": scrape_resp.get("error", None)
            })
        except Exception as e:
            results.append({
                "website": website,
                "success": False,
                "error": str(e)
            })

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        access_log=True,
        workers=1
    )
@app.get("/test_scraping/{encoded_url:path}")
async def test_scraping(encoded_url: str):
    import base64
    try:
        url = base64.b64decode(encoded_url).decode('utf-8')
        logger.info(f"Testing website scraping for: {url}")
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Test main page scraping
        scrape_result = scrape_website(ScrapeRequest(url=url))
        
        # Get internal links
        soup = BeautifulSoup(requests.get(url).text, "html.parser")
        internal_links = find_internal_links(soup, url)
        
        return {
            "url": url,
            "success": "error" not in scrape_result,
            "text_sample": scrape_result.get("text", "")[:200] if "text" in scrape_result else None,
            "emails_found": scrape_result.get("emails", []),
            "internal_pages_checked": internal_links,
            "error": scrape_result.get("error", None)
        }
    except Exception as e:
        logger.error(f"Error in test_scraping: {str(e)}")
        return {"error": str(e)}
