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
        "bot": "SNIPER AI",
        "status": "online",
        "api_key_added": bool(API_KEY),
        "market_data": "not_connected",
        "auto_trade": "disabled"
    }


@app.get("/api/signal")
def signal():
    return {
        "signal": "WAIT",
        "message": "Live market data is not connected yet."
    }
