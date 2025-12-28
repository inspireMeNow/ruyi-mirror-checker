from fastapi import FastAPI, HTTPException
import httpx
from typing import Dict, Any
import os
import asyncio
import uvicorn

app = FastAPI()

# status.json
RESULTS_URL = os.getenv(
    "RESULTS_URL",
    "https://raw.githubusercontent.com/inspireMeNow/ruyi-mirror-checker/refs/heads/hidden/status.json"
)

# results
status_data: Dict[str, Any] = {}

REFRESH_INTERVAL = 3 * 60 * 60  # 3 hours


async def fetch_status_json():
    """Fetch the pre-generated JSON from GitHub"""
    global status_data
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(RESULTS_URL)
            resp.raise_for_status()
            status_data = resp.json()
            print(f"Loaded {len(status_data.get('boards', {}))} boards from status.json")
    except Exception as e:
        print(f"Failed to fetch status.json from GitHub: {e}")


async def refresh_status_periodically():
    """Background task to refresh status_data"""
    while True:
        await fetch_status_json()
        await asyncio.sleep(REFRESH_INTERVAL)


@app.on_event("startup")
async def startup_event():
    """Fetch JSON once at startup"""
    await fetch_status_json()
    asyncio.create_task(refresh_status_periodically())


@app.get("/")
def root():
    return {"service": "ruyi-mirror-checker", "results_url": RESULTS_URL}


@app.get("/board-images")
def list_board_images():
    boards = status_data.get("boards", {})
    return {
        "generated_at": status_data.get("generated_at"),
        "boards": sorted(boards.keys())
    }


@app.get("/board-images/{board_name}")
def get_board_image(board_name: str):
    boards = status_data.get("boards", {})

    if board_name not in boards:
        raise HTTPException(status_code=404, detail=f"Board '{board_name}' not found")

    return {
        "generated_at": status_data.get("generated_at"),
        "board": board_name,
        "distfiles": boards[board_name].get("distfiles", [])
    }
