from fastapi import FastAPI
import subprocess
import threading
import time
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()


def run_responder_loop():
    while True:
        try:
            logger.info("Starting responder process...")
            subprocess.run(["python3", "responder.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Responder process failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in responder loop: {e}")
        logger.info("Waiting 5 minutes before next check...")
        time.sleep(300)  # Wait 5 minutes before checking again


# Start the responder loop in the background
responder_thread = threading.Thread(target=run_responder_loop, daemon=True)
responder_thread.start()


@app.get("/")
def home():
    return {"message": "Jenny AI Responder is running!", "status": "active"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "responder",
        "port": 3001,
        "responder_thread_alive": responder_thread.is_alive()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        reload=False,
        workers=1,
        access_log=True
    )