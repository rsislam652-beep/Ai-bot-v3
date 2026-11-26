
from fastapi import FastAPI
from fastapi.responses import FileResponse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os
import json

app = FastAPI(title="SNIPER AI BOT")
API_KEY = os.getenv("OTCHARTS_API_KEY")

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"status": "online", "bot": "SNIPER AI"}

@app.get("/api/status")
def api_status():
    return {"api_key_added": bool(API_KEY)}

@app.get("/api/candles")
def candles():
    if not API_KEY:
        return {"error": "API key missing"}

    url = "https://otcharts.com/v1/candles?venue=quotex&symbol=EURUSD_otc&tf=60&limit=5"

    req = Request(url, headers={
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "SNIPER-AI-BOT/1.0"
    })

    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return {"error": "API request failed", "status": e.code, "detail": detail[:500]}
    except URLError as e:
        return {"error": "Connection failed", "detail": str(e.reason)}
    except Exception as e:
        return {"error": "Unexpected error", "detail": str(e)[:300]}
