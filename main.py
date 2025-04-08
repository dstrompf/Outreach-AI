# main.py (Final Updated)

from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv
from sheets import get_qualified_leads
import gspread
from google.oauth2.service_account import Credentials
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----- MODELS -----
class ScrapeRequest(BaseModel):
    url: str

class SummarizeRequest(BaseModel):
    text: str

class FindEmailRequest(BaseModel):
    url: str

class GenerateEmailRequest(BaseModel):
    business_name: str
    summary: str

# ----- HELPERS -----
def save_generated_email(website, email_content):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(
        "ai-outreach-sheets-access-24fe56ec7689.json", scopes=scopes
    )

    client = gspread.authorize(credentials)
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1WbdwNIdbvuCPG_Lh3-mtPCPO8ddLR5RIatcdeq29EPs/edit"
    )
    worksheet = sheet.worksheet("Generated Emails")
    worksheet.append_row([website, email_content])

# ----- ROUTES -----
@app.get("/")
def home():
    return {"message": "AI Outreach System Online"}

@app.get("/test_leads")
def test_leads():
    qualified = get_qualified_leads()
    return {"qualified_leads": qualified}

@app.post("/scrape")
def scrape_website(request: ScrapeRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
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
        prompt = f"""
You are an AI outreach assistant for a marketing agency.

Task: Write a short, friendly, and personalized cold email to {request.business_name}.

Based on this business summary: {request.summary}.

1. Start by finding common ground or complimenting something about their business (e.g., location, industry, services).
2. Mention that you noticed they are using Google Workspace and have a contact form on their website.
3. Introduce our application — "AI Form Reply" — in a natural way. Briefly explain:
   - It connects directly with Google Workspace.
   - It automatically responds to inbound form submissions.
   - It answers common questions immediately and books qualified leads to appointments.
   - It reduces manual email work and speeds up sales cycles.
4. Highlight one key benefit: faster lead follow-up = more closed deals.
5. Keep the tone helpful, genuine, and conversational (not robotic or overly salesy).
6. End with a soft open-ended question like: 
   "Would you be open to chatting about how we could help you respond faster and close more leads?"

Rules:
- Keep it under 150 words.
- Sound like a real human: warm, helpful, confident.
- No hard selling.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a friendly outreach email assistant helping a marketing agency offer AI solutions to businesses."},
                {"role": "user", "content": prompt}
            ]
        )
        return {"email": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

@app.get("/run_campaign")
def run_campaign():
    try:
        qualified_leads = get_qualified_leads()
        for website in qualified_leads:
            # 1. Scrape
            scrape_resp = scrape_website(ScrapeRequest(url=website))
            if 'error' in scrape_resp:
                continue

            # 2. Summarize
            summarize_resp = summarize(SummarizeRequest(text=scrape_resp['text']))
            if 'error' in summarize_resp:
                continue

            # 3. Generate Email
            generate_resp = generate_email(
                GenerateEmailRequest(
                    business_name=website,
                    summary=summarize_resp['summary']
                )
            )
            if 'error' in generate_resp:
                continue

            # 4. Save to Google Sheet
            save_generated_email(website, generate_resp['email'])

        return {"status": "Campaign complete."}
    except Exception as e:
        return {"error": str(e)}

# ----- SCHEDULER -----
# Initialize scheduler
scheduler = BackgroundScheduler()

# Define the scheduled job
def scheduled_campaign():
    print("Running scheduled campaign...")
    run_campaign()

# Add the job to the scheduler (runs daily at 9:00 AM server time)
scheduler.add_job(scheduled_campaign, 'cron', hour=9, minute=0)

# Start the scheduler
scheduler.start()

# ----- MAIN -----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)