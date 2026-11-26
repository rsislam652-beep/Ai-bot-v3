@app.get("/api/candles")
def candles(symbol: str = "EURUSD", timeframe: str = "1m"):
    symbol = symbol.upper()

    if timeframe not in ("1m", "5m"):
        raise HTTPException(
            status_code=400,
            detail="Use 1m or 5m"
        )

    if not re.fullmatch(r"[A-Z0-9]{3,12}", symbol):
        raise HTTPException(
            status_code=400,
            detail="Invalid symbol"
        )

    url = (
        f"https://biquote.io/api/{symbol}/ohlc"
        f"?interval={timeframe}&limit=30"
    )

    try:
        request = Request(
            url,
            headers={"User-Agent": "SNIPER-AI-BOT"}
        )

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
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )
