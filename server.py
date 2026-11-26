from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI(title="SNIPER AI BOT")

API_KEY = os.getenv("OTCHARTS_API_KEY")


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "online"}


@app.get("/api/status")
def api_status():
    return {
        "api_key_added": bool(API_KEY),
        "message": "API key found" if API_KEY else "API key missing"
    }
