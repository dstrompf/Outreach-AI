import gspread
from google.oauth2.service_account import Credentials
import logging
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ScrapeRequest(BaseModel):
    url: str

class SummarizeRequest(BaseModel):
    text: str

class FindEmailRequest(BaseModel):
    url: str

class GenerateEmailRequest(BaseModel):
    business_name: str
    summary: str

@app.get("/")
def home():
    return {"message": "AI Outreach System Online"}

@app.get("/test_leads")
def test_leads():
    qualified = get_qualified_leads() # Assuming get_qualified_leads is defined elsewhere
    return {"qualified_leads": qualified}

@app.post("/scrape")
def scrape_website(request: ScrapeRequest):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
        response = requests.get(request.url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        texts = [tag.get_text() for tag in soup.find_all(["h1", "h2", "p"])]
        return {"text": "\n".join(texts)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/summarize")
def summarize(request: SummarizeRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the following website content in 3 sentences."},
                {"role": "user", "content": request.text}
            ]
        )
        return {"summary": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

@app.post("/find_email")
def find_email(request: FindEmailRequest):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
        response = requests.get(request.url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        emails = []
        for a in soup.find_all('a', href=True):
            if "mailto:" in a['href']:
                emails.append(a['href'].replace('mailto:', ''))
        return {"emails": emails}
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate_email")
def generate_email(request: GenerateEmailRequest):
    try:
        prompt = f"""Write a short, friendly outreach email to {request.business_name}. Mention their business based on this summary: {request.summary}. Offer a free consultation. End with a soft call to action."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional cold email writer."},
                {"role": "user", "content": prompt}
            ]
        )
        return {"email": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

@app.get("/run_campaign")
def run_campaign():
    try:
        qualified_leads = get_qualified_leads() # Assuming get_qualified_leads is defined elsewhere
        for website in qualified_leads:
            # 1. Scrape
            scrape_resp = scrape_website(ScrapeRequest(url=website))
            if 'error' in scrape_resp:
                continue

            # 2. Find Email (Added)
            email_resp = find_email(FindEmailRequest(url=website))
            found_email = email_resp["emails"][0] if email_resp["emails"] else ""

            # 2. Summarize
            summarize_resp = summarize(SummarizeRequest(text=scrape_resp['text']))
            if 'error' in summarize_resp:
                continue

            # 3. Generate Email
            generate_resp = generate_email(GenerateEmailRequest(
                business_name=website,
                summary=summarize_resp['summary']
            ))
            if 'error' in generate_resp:
                continue

            # 4. Save to Sheet
            save_generated_email(website, generate_resp['email'], found_email)

        return {"status": "Campaign completed"}
    except Exception as e:
        return {"error": str(e)}


def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        credentials = Credentials.from_service_account_file(
            "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
        )
        return sheet.worksheet("Generated Emails")
    except Exception as e:
        logger.error(f"Failed to connect to sheet: {str(e)}")
        return None

def save_generated_email(website, email_content, found_email=""):
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            worksheet = connect_to_sheet()
            if not worksheet:
                raise Exception("Could not connect to worksheet")

            # Check for existing entry with retry
            try:
                existing_websites = worksheet.col_values(1)
            except Exception as e:
                logger.warning(f"Retrying to get column values: {str(e)}")
                time.sleep(retry_delay)
                existing_websites = worksheet.col_values(1)

            if website in existing_websites:
                row_num = existing_websites.index(website) + 1
                
                # Update with retry
                try:
                    worksheet.update_cell(row_num, 2, email_content)
                    if found_email:
                        worksheet.update_cell(row_num, 3, found_email)
                    logger.info(f"Updated existing entry for {website}")
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Retrying update for {website}: {str(e)}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
            else:
                # Append with retry
                try:
                    worksheet.append_row([
                        website,
                        email_content,
                        found_email,
                        "Pending"
                    ])
                    logger.info(f"Added new entry for {website}")
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Retrying append for {website}: {str(e)}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
            
            return True

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to save email for {website} after {max_retries} attempts: {str(e)}")
                return False
            logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
            time.sleep(retry_delay * (attempt + 1))
    
    return False