
from fastapi import FastAPI
import subprocess
import threading
import time

app = FastAPI()

def run_responder_loop():
    while True:
        subprocess.run(["python3", "responder.py"])
        time.sleep(300)  # Wait 5 minutes before checking again

# Start the responder loop in the background
threading.Thread(target=run_responder_loop, daemon=True).start()

@app.get("/")
def home():
    return {"message": "Jenny AI Responder is running!"}
