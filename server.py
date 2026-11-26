
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
    return {
        "api_key_added": bool(API_KEY),
        "message": "API key found" if API_KEY else "API key missing"
    }

@app.get("/api/candles")
def candles():
    if not API_KEY:
        return {"error": "API key missing"}

    url = (
        "https://otcharts.com/v1/candles"
        "?venue=quotex&symbol=EURUSD_otc&tf=60&limit=5"
    )

    req = Request(
        url,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": "API request failed", "status": e.code}
    except (URLError, TimeoutError):
        return {"error": "Connection failed"}
    except Exception:
        return {"error": "Unexpected error"}
