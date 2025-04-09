from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time
from openai import OpenAI
import os
from dotenv import load_dotenv
from sheets import get_qualified_leads
import gspread
from google.oauth2.service_account import Credentials
import resend
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
resend.api_key = os.getenv("RESEND_API_KEY")

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        collected_text = ""
        collected_emails = set()

        response = requests.get(request.url, headers=headers, timeout=10)
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

@app.post("/generate_email")
def generate_email(request: GenerateEmailRequest):
    try:
        prompt = f"""You are an AI outreach assistant specializing in Google Workspace solutions.

Task: Write a personalized cold email for {request.business_name}. They are using Google Workspace.

Based on this business summary: {request.summary}

Keep it short, friendly, and focused on how AI form automation can help their business."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "You are a friendly outreach email assistant helping offer AI solutions to businesses."
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
        qualified_leads = get_qualified_leads()
        logger.info(f"Found {len(qualified_leads)} qualified leads")
        emails_generated = 0

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
                generate_resp = generate_email(
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
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        workers=1,
        log_level="info",
        reload=False,
        access_log=True
    )