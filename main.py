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
    import resend  # <-- NEW

    load_dotenv()
    app = FastAPI()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resend.api_key = os.getenv("RESEND_API_KEY")  # <-- NEW

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
        worksheet.append_row([website, email_content])
        print(f"Saved new website: {website}")

    # ----- DAILY EMAIL REPORT HELPER (NEW) -----
    def send_daily_report(count):
        try:
            resend.Emails.send({
                "from": "Good At Marketing <YOUR_VERIFIED_EMAIL@yourdomain.com>",  # <-- change this to your verified email
                "to": ["YOUR_PERSONAL_EMAIL@gmail.com"],  # <-- your personal email here
                "subject": "Daily AI Outreach Report",
                "html": f"<p>Today's AI Outreach Campaign completed successfully.<br><strong>New emails generated: {count}</strong></p>"
            })
            print("✅ Daily report email sent.")
        except Exception as e:
            print(f"❌ Failed to send daily report email: {str(e)}")

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
            prompt = f"""You are an AI outreach assistant for a marketing agency.

    Task: Write a short, friendly, and personalized cold email to {request.business_name}.

    Based on this business summary: {request.summary}.

    [Follow the instructions you already have...]
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
            emails_generated = 0  # Count how many emails

            for website in qualified_leads:
                scrape_resp = scrape_website(ScrapeRequest(url=website))
                if 'error' in scrape_resp:
                    continue

                summarize_resp = summarize(SummarizeRequest(text=scrape_resp['text']))
                if 'error' in summarize_resp:
                    continue

                generate_resp = generate_email(
                    GenerateEmailRequest(
                        business_name=website,
                        summary=summarize_resp['summary']
                    )
                )
                if 'error' in generate_resp:
                    continue

                save_generated_email(website, generate_resp['email'])
                emails_generated += 1  # Increment email count

            # 📬 Send daily report after campaign
            send_daily_report(emails_generated)

            return {"status": "Campaign complete."}
        except Exception as e:
            return {"error": str(e)}

    # ----- SCHEDULER -----
    scheduler = BackgroundScheduler()

    def scheduled_campaign():
        print("Running scheduled campaign...")
        run_campaign()

    scheduler.add_job(scheduled_campaign, 'cron', hour=9, minute=0)
    scheduler.start()

    # ----- MAIN -----
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=5000)