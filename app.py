"""Local dev server: serves static/ and a live /rates.json (cached 20 min)."""

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from scraper import scrape

STATIC = Path(__file__).parent / "static"
TTL_SECONDS = 20 * 60
app = FastAPI(title="Chennai Gold Rate")
_cache: dict = {"data": None, "at": 0.0}


@app.get("/rates.json")
async def rates():
    if not _cache["data"] or time.time() - _cache["at"] > TTL_SECONDS:
        try:
            _cache["data"], _cache["at"] = await scrape(), time.time()
        except Exception as e:
            if not _cache["data"]:
                return JSONResponse({"error": str(e)}, status_code=502)
    return _cache["data"]


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")
