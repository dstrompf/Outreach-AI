from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/")
def home():
    return {"message": "AI Outreach System Online"}

@app.post("/scrape")
def scrape_website(url: str):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        texts = [tag.get_text() for tag in soup.find_all(["h1", "h2", "p"])]
        return {"text": "\n".join(texts)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/summarize")
def summarize(text: str):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the following website content in 3 sentences."},
                {"role": "user", "content": text}
            ]
        )
        return {"summary": response['choices'][0]['message']['content']}
    except Exception as e:
        return {"error": str(e)}

@app.post("/find_email")
def find_email(url: str):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        emails = []
        for a in soup.find_all('a', href=True):
            if "mailto:" in a['href']:
                emails.append(a['href'].replace('mailto:', ''))
        return {"emails": emails}
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate_email")
def generate_email(business_name: str, summary: str):
    try:
        prompt = f"""Write a short, friendly outreach email to {business_name}. 
        Mention their business based on this summary: {summary}. 
        Offer a free consultation. End with a soft call to action."""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional cold email writer."},
                {"role": "user", "content": prompt}
            ]
        )
        return {"email": response['choices'][0]['message']['content']}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)