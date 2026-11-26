from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from urllib.request import Request, urlopen
from datetime import datetime, timezone
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


def get_candles(symbol, timeframe):
    url = (
        f"https://biquote.io/api/{symbol}/ohlc"
        f"?interval={timeframe}&limit=50"
    )
    request = Request(url, headers={"User-Agent": "SNIPER-AI-BOT"})

    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("bars", [])


@app.get("/api/market-data")
def market_data(symbol: str = "EURUSD"):
    symbol = symbol.upper()

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    url = f"https://biquote.io/api/{symbol}"

    try:
        request = Request(url, headers={"User-Agent": "SNIPER-AI-BOT"})
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=502, detail="Market data unavailable")


@app.get("/api/candles")
def candles(symbol: str = "EURUSD", timeframe: str = "1m"):
    symbol = symbol.upper()

    if timeframe not in ("1m", "5m"):
        raise HTTPException(status_code=400, detail="Use 1m or 5m")

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        bars = get_candles(symbol, timeframe)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": bars,
            "source": "biquote",
            "note": "Regular forex, not Quotex OTC"
        }
    except Exception:
        raise HTTPException(status_code=502, detail="Candle data unavailable")


def calculate_ema(values, period):
    if len(values) < period:
        return None

    ema = sum(values[:period]) / period
    multiplier = 2 / (period + 1)

    for price in values[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@app.get("/api/analysis")
def analysis(symbol: str = "EURUSD", timeframe: str = "5m"):
    symbol = symbol.upper()

    if timeframe not in ("1m", "5m"):
        raise HTTPException(status_code=400, detail="Use 1m or 5m")

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        bars = get_candles(symbol, timeframe)

        if not bars:
            raise HTTPException(status_code=502, detail="No candle data")

        newest = bars[0]
        newest_time = datetime.fromisoformat(
            newest["openTime"].replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)
        age_seconds = (now - newest_time).total_seconds()
        max_age = 180 if timeframe == "1m" else 600

        # Exclude the currently forming candle
        closed_bars = [bar for bar in bars if not bar.get("isOpen", False)]
        closed_bars = list(reversed(closed_bars))

        closes = [float(bar["close"]) for bar in closed_bars]

        if age_seconds < -60 or age_seconds > max_age:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": "WAIT",
                "reason": "Market data is stale or timestamp is invalid",
                "source": "biquote",
                "note": "Regular forex, not Quotex OTC"
            }

        if len(closes) < 22:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": "WAIT",
                "reason": "Not enough closed candles",
                "source": "biquote",
                "note": "Regular forex, not Quotex OTC"
            }

        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)
        rsi14 = calculate_rsi(closes, 14)

        signal = "WAIT"
        reason = "Indicators do not confirm a clear direction"

        if ema9 > ema21 and 50 < rsi14 < 70:
            signal = "CALL"
            reason = "EMA 9 above EMA 21 and RSI confirms upward momentum"

        elif ema9 < ema21 and 30 < rsi14 < 50:
            signal = "PUT"
            reason = "EMA 9 below EMA 21 and RSI confirms downward momentum"

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal,
            "ema9": round(ema9, 6),
            "ema21": round(ema21, 6),
            "rsi14": round(rsi14, 2),
            "reason": reason,
            "source": "biquote",
            "note": "Regular forex, not Quotex OTC. Not a guaranteed trading signal."
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Analysis unavailable")


@app.get("/api/signal")
def signal():
    return {
        "signal": "WAIT",
        "message": "Use /api/analysis for technical analysis."
    }
