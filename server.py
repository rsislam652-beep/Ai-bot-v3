from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="SNIPER AI BOT")

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"status": "online", "bot": "SNIPER AI"}
