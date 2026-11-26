from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re
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
        "market_data": "biquote",
        "auto_trade": "disabled"
    }


@app.get("/api/market-data")
def market_data(symbol: str = "EURUSD"):
    symbol = symbol.upper()

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    url = f"https://biquote.io/api/{symbol}"

    try:
        request = Request(url, headers={"User-Agent": "SNIPER-AI-BOT"})

        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data

    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/api/candles")
def candles(symbol: str = "EURUSD", timeframe: str = "1m"):
    symbol = symbol.upper()

    if timeframe not in ("1m", "5m"):
        raise HTTPException(status_code=400, detail="Use 1m or 5m")

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    url = (
        f"https://biquote.io/api/{symbol}/ohlc"
        f"?interval={timeframe}&limit=30"
    )

    try:
        request = Request(url, headers={"User-Agent": "SNIPER-AI-BOT"})

        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": data.get("bars", []),
            "source": "biquote",
            "note": "Regular forex, not Quotex OTC"
        }

    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/api/signal")
def signal():
    return {
        "signal": "WAIT",
        "message": "No verified Quotex OTC signal available."
    }
