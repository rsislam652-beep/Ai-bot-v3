from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json
import re
import os
import uuid
from threading import Lock

app = FastAPI(title="SNIPER AI BOT")

API_KEY = os.getenv("OTCHARTS_API_KEY")

result_lock = Lock()
pending_results = {}
completed_results = []


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
        "market_data": "biquote",
        "auto_trade": "disabled"
    }


def get_candles(symbol, timeframe):
    url = (
        f"https://biquote.io/api/{symbol}/ohlc"
        f"?interval={timeframe}&limit=50"
    )
    request = Request(
        url,
        headers={"User-Agent": "SNIPER-AI-BOT"}
    )
    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("bars", [])


def get_current_price(symbol, timeframe):
    bars = get_candles(symbol, timeframe)
    if not bars:
        raise ValueError("No market candles")
    price = float(bars[0]["close"])
    if price <= 0:
        raise ValueError("Invalid market price")
    return price


@app.get("/api/market-data")
def market_data(symbol: str = "EURUSD"):
    symbol = symbol.upper()
    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        request = Request(
            f"https://biquote.io/api/{symbol}",
            headers={"User-Agent": "SNIPER-AI-BOT"}
        )
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
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": get_candles(symbol, timeframe),
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
        avg_gain = (
            avg_gain * (period - 1) + gains[i]
        ) / period
        avg_loss = (
            avg_loss * (period - 1) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def register_result(symbol, timeframe, signal, entry_price):
    result_id = str(uuid.uuid4())

    with result_lock:
        pending_results[result_id] = {
            "id": result_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal,
            "entry_price": entry_price,
            "created_at": datetime.now(timezone.utc)
        }

    return result_id


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

        age_seconds = (
            datetime.now(timezone.utc) - newest_time
        ).total_seconds()

        max_age = 180 if timeframe == "1m" else 600

        closed_bars = [
            bar for bar in bars
            if not bar.get("isOpen", False)
        ]
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

        last_close = closes[-1]
        previous_close = closes[-2]

        signal = "WAIT"
        reason = "Trend is not strongly confirmed"

        # CALL: upward trend + RSI strength + rising candle close
        if (
            ema9 > ema21
            and rsi14 > 55
            and last_close > previous_close
        ):
            signal = "CALL"
            reason = "Uptrend confirmed by EMA, RSI and rising price"

        # PUT: downward trend + RSI weakness + falling candle close
        elif (
            ema9 < ema21
            and rsi14 < 45
            and last_close < previous_close
        ):
            signal = "PUT"
            reason = "Downtrend confirmed by EMA, RSI and falling price"

        response_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal,
            "ema9": round(ema9, 6),
            "ema21": round(ema21, 6),
            "rsi14": round(rsi14, 2),
            "reason": reason,
            "source": "biquote",
            "note": "Regular forex, not Quotex OTC. Not guaranteed."
        }

        if signal in ("CALL", "PUT"):
            entry_price = float(newest["close"])
            result_id = register_result(
                symbol, timeframe, signal, entry_price
            )
            response_data["result_id"] = result_id
            response_data["entry_price"] = entry_price
            response_data["result_after_seconds"] = 60

        return response_data

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Analysis unavailable")


@app.get("/api/result-check")
def result_check():
    now = datetime.now(timezone.utc)

    with result_lock:
        due_items = [
            (key, item)
            for key, item in pending_results.items()
            if (now - item["created_at"]).total_seconds() >= 60
        ]

    for key, item in due_items:
        try:
            exit_price = get_current_price(
                item["symbol"], item["timeframe"]
            )

            entry_price = item["entry_price"]
            signal = item["signal"]

            if exit_price == entry_price:
                outcome = "DRAW"
            elif signal == "CALL":
                outcome = "WIN" if exit_price > entry_price else "LOSS"
            else:
                outcome = "WIN" if exit_price < entry_price else "LOSS"

            record = {
                "id": key,
                "symbol": item["symbol"],
                "timeframe": item["timeframe"],
                "signal": signal,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "result": outcome,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

            with result_lock:
                pending_results.pop(key, None)
                completed_results.insert(0, record)
                del completed_results[50:]

        except Exception:
            continue

    with result_lock:
        pending = [
            {
                "id": item["id"],
                "symbol": item["symbol"],
                "signal": item["signal"],
                "status": "PENDING"
            }
            for item in pending_results.values()
        ]
        completed = list(completed_results)

    return {
        "check_after_seconds": 60,
        "pending": pending,
        "completed": completed,
        "note": "Results compare BiQuote regular Forex prices, not Quotex OTC."
    }


@app.get("/api/signal")
def signal():
    return {
        "signal": "WAIT",
        "message": "Use /api/analysis for technical analysis."
    }
