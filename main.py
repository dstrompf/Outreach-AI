from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# New OpenAI client setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic models for proper POST request bodies
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
        prompt = f"""Write a short, friendly outreach email to {request.business_name}. 
Mention their business based on this summary: {request.summary}. 
Offer a free consultation. End with a soft call to action."""

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)