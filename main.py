from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time
import random
from openai import OpenAI
import os
# ----- SETUP -----

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

        domain = request.url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        default_email = f"info@{domain}"

        collected_text = ""
        collected_emails = set([default_email])

        response = session.get(request.url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        collected_text += " ".join([tag.get_text() for tag in soup.find_all(["h1", "h2", "p"])])

        for a in soup.find_all('a', href=True):
            if "mailto:" in a['href']:
                email = a['href'].replace('mailto:', '').split('?')[0].strip()
                if '@' in email and '.' in email:
                    collected_emails.add(email)

        if len(collected_emails) == 1:
            collected_emails.add(f"contact@{domain}")

        logger.info(f"Found emails for {request.url}: {collected_emails}")

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
        logger.info(f"OpenAI API call for {request.business_name}")

        for cached_key in email_cache:
            if request.business_name.lower() in cached_key.lower():
                logger.info("Using similar business cached response")
                return {"email": email_cache[cached_key]}

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
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are Jenny, a friendly outreach specialist focused on helping businesses automate their lead responses."
                }, {
                    "role": "user",
                    "content": prompt
                }])
            response_text = response.choices[0].message.content
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