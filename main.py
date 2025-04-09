from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time
import random
from openai import OpenAI
import os
from dotenv import load_dotenv
from sheets import get_qualified_leads
import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- SETUP -----
load_dotenv()
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Assuming resend is defined elsewhere, this line remains unchanged.
#resend.api_key = os.getenv("RESEND_API_KEY")

# ----- MODELS -----
class ScrapeRequest(BaseModel):
    url: str

class GenerateEmailRequest(BaseModel):
    business_name: str
    summary: str

# ----- HELPERS -----
def find_internal_links(soup, base_url):
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/') or base_url in href:
            if any(x in href.lower() for x in ['contact', 'about', 'team']):
                full_url = urljoin(base_url, href)
                links.append(full_url)
    return links[:3]

def scrape_website(request: ScrapeRequest):
    try:
        # Setup Session with Retry
        session = requests.Session()
        retry_strategy = requests.packages.urllib3.util.retry.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        collected_text = ""
        collected_emails = set()

        response = session.get(request.url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        collected_text += " ".join([tag.get_text() for tag in soup.find_all(["h1", "h2", "p"])])

        for a in soup.find_all('a', href=True):
            if "mailto:" in a['href']:
                email = a['href'].replace('mailto:', '').split('?')[0].strip()
                if '@' in email and '.' in email:
                    collected_emails.add(email)

        links = find_internal_links(soup, request.url)
        for link in links:
            try:
                sub_resp = requests.get(link, headers=headers, timeout=10)
                sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                collected_text += " ".join([tag.get_text() for tag in sub_soup.find_all(["h1", "h2", "p"])])
                for a in sub_soup.find_all('a', href=True):
                    if "mailto:" in a['href']:
                        collected_emails.add(a['href'].replace('mailto:', ''))
            except:
                continue

        return {"text": collected_text, "emails": list(collected_emails)}
    except Exception as e:
        return {"error": str(e)}

def save_generated_email(website, email_content, found_email=""):
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "ai-outreach-sheets-access-24fe56ec7689.json")
                SPREADSHEET_URL = os.getenv("SPREADSHEET_URL", "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit")
                logger.info(f"Attempt {attempt + 1} to save email for {website}")

                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
                credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
                client = gspread.authorize(credentials)
                sheet = client.open_by_url(
                    "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
                )
            try:
                worksheet = sheet.worksheet("Generated Emails")

                # Check for existing websites
                existing_websites = worksheet.col_values(1)
                if website in existing_websites:
                    logger.info(f"Website {website} already exists. Skipping save.")
                    return False

                worksheet.append_row([website, email_content, found_email, "Pending"])
                logger.info(f"Found {len(existing_websites)} existing processed websites")
                logger.info(f"Saved new website: {website}")
                return True
            except Exception as e:
                logger.error(f"Failed to save email: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Failed to save email: {str(e)}")
            return False

# ----- ROUTES -----
@app.get("/")
def home():
    return {"message": "AI Outreach System Online"}

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "main",
        "port": 5000
    }

# Global variables for caching and rate limiting
email_cache = {}
last_api_call = 0
MIN_TIME_BETWEEN_CALLS = 1  # seconds

@app.post("/generate_email")
def generate_email(request: GenerateEmailRequest):
    try:
        # Cost tracking
        logger.info(f"OpenAI API call for {request.business_name}")

        # Check cache with fuzzy matching
        for cached_key in email_cache:
            if request.business_name.lower() in cached_key.lower():
                logger.info("Using similar business cached response")
                return {"email": email_cache[cached_key]}

        # Token optimization
        prompt = f"""Business: {request.business_name}
Summary: {request.summary[:500]}  # Limit summary length
Task: Write a short cold email."""

        # Rate limiting
        global last_api_call
        current_time = time.time()
        if current_time - last_api_call < MIN_TIME_BETWEEN_CALLS:
            time.sleep(MIN_TIME_BETWEEN_CALLS)

        with open('knowledge_base.txt', 'r') as f:
            knowledge_base = f.read()

        prompt = f"""You are Jenny, an AI outreach specialist for AI Form Reply.

Context from their website: {request.summary}
Business name: {request.business_name}

Use this knowledge base for the product offering:
{knowledge_base}

Task: Write a personalized cold email that:
1. Opens with a personal observation about their business based on their website
2. Explains how AI Form Reply can help their specific business case
3. Focuses on the automated Google Workspace integration
4. Keeps it short, friendly, and focused on solving slow lead response times

End the email with this footer:
---
Note: This email address was found publicly on your website. To unsubscribe and be removed from our database, simply reply with "UNSUBSCRIBE".

Best regards,
Jenny from AI Form Reply
info@aiformreply.com
You can book a quick demo here: https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ36P0ABwQ5qKYkBrQ302KCunFUEoe23GadJe8JFnQnApuoDbID8QD26WJio1oDY5TqrEV2QfIQq"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "You are Jenny, a friendly outreach specialist focused on helping businesses automate their lead responses."
                }, {
                    "role": "user",
                    "content": prompt
                }])
            response_text = response.choices[0].message.content
            # Cache the response
            cache_key = f"{request.business_name}:{request.summary}"
            email_cache[cache_key] = response_text
            last_api_call = time.time()
            return {"email": response_text}
        except Exception as e:
            if "insufficient_quota" in str(e):
                logger.error("OpenAI API quota exceeded - please check billing")
                return {"error": "OpenAI API quota exceeded - please check billing at platform.openai.com/account/billing"}
            elif "rate_limit" in str(e):
                time.sleep(20)  # Wait before retry
                return {"error": "Rate limit hit, please try again in a few minutes"}
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def generate_email_with_retry(request: GenerateEmailRequest, max_retries=3, base_delay=1):
    RETRYABLE_ERRORS = {
        '429',  # Rate limit
        '500',  # Internal server error
        '502',  # Bad gateway
        '503',  # Service unavailable
        '504',  # Gateway timeout
        'timeout',  # Connection timeout
        'connection error'  # Generic connection issues
    }

    for attempt in range(max_retries):
        try:
            response = generate_email(request)
            if response and not response.get('error'):
                return response

            # Handle empty or error responses
            error_msg = response.get('error') if response else 'Empty response'
            raise Exception(error_msg)

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = (
                any(code in error_str for code in RETRYABLE_ERRORS) or
                'rate_limit' in error_str or
                'capacity' in error_str
            )

            if is_retryable and attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = min(base_delay * (2 ** attempt) * (1 + random.random() * 0.1), 15)
                logger.warning(
                    f"Temporary error: {str(e)}. "
                    f"Attempt {attempt + 1}/{max_retries}. "
                    f"Retrying in {wait_time:.1f}s"
                )
                time.sleep(wait_time)
                continue

            logger.error(
                f"{'Retryable' if is_retryable else 'Non-retryable'} "
                f"error on attempt {attempt + 1}/{max_retries}: {str(e)}"
            )
            if attempt == max_retries - 1:
                return {
                    "error": f"Failed after {max_retries} attempts. Last error: {str(e)}",
                    "status": "error",
                    "attempts": attempt + 1
                }

    return {"error": "Max retries exceeded", "status": "error", "attempts": max_retries}

@app.get("/run-campaign")
@app.get("/run_campaign")  # Support both formats
def run_campaign():
    try:
        qualified_leads = get_qualified_leads()
        logger.info(f"Found {len(qualified_leads)} qualified leads")
        emails_generated = 0

        # Process only 3 leads at a time to avoid rate limits
        batch_size = 3
        current_batch = qualified_leads[:batch_size]
        logger.info(f"Processing batch of {len(current_batch)} leads")

        for lead in qualified_leads[:5]:  # Process 5 at a time
            try:
                website = lead['website']
                logger.info(f"Processing website: {website}")

                scrape_resp = scrape_website(ScrapeRequest(url=website))
                if 'error' in scrape_resp:
                    logger.error(f"Scraping failed for {website}: {scrape_resp['error']}")
                    continue

                if not scrape_resp.get('emails'):
                    logger.info(f"No emails found for {website}")
                    continue

                summary = "Business using Google Workspace that could benefit from AI form automation"
                generate_resp = generate_email_with_retry(
                    GenerateEmailRequest(
                        business_name=lead.get('business_name', website),
                        summary=summary
                    )
                )

                if 'error' in generate_resp:
                    logger.error(f"Email generation failed for {website}")
                    continue

                first_email = scrape_resp['emails'][0]
                if save_generated_email(website, generate_resp['email'], first_email):
                    emails_generated += 1
                    logger.info(f"Successfully processed {website}")

            except Exception as e:
                logger.error(f"Error processing {website}: {str(e)}")
                continue

        logger.info(f"Campaign complete. Generated {emails_generated} emails.")
        return {"status": "success", "emails_generated": emails_generated}

    except Exception as e:
        logger.error(f"Campaign failed: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        workers=1
    )