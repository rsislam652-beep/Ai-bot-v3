from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os
import re

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
        "market_data": "test_available",
        "auto_trade": "disabled"
    }


@app.get("/api/market-data")
def market_data(symbol: str = "EURUSD"):
    symbol = symbol.upper()

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    url = f"https://biquote.io/api/{symbol}"

    try:
        request = Request(
            url,
            headers={"User-Agent": "SNIPER-AI-BOT"}
        )

        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        return {
            "source": "biquote",
            "symbol": data.get("symbol"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "mid": data.get("mid"),
            "market_state": data.get("marketState"),
            "stale": data.get("stale"),
            "timestamp": data.get("timestamp"),
            "note": "Regular forex data, not Quotex OTC"
        }

    except HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Market data provider error: {error.code}"
        )
    except (URLError, TimeoutError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail=f"Market data unavailable: {str(error)}"
        )


@app.get("/api/signal")
def signal():
    return {
        "signal": "WAIT",
        "message": "No verified Quotex OTC signal available."
    }
