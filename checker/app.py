from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import Dict, List, Any
import os

from checker import check_url
from config import load_board_image_configs, load_mirror_config

app = FastAPI()

repo_root = Path(os.getenv("REPO_ROOT", ".")).resolve()

# Load mirror config
mirrors = load_mirror_config(repo_root)

# Load board-image configs
configs = load_board_image_configs(repo_root)

# Build board name
board_map: Dict[str, List[Dict[str, Any]]] = {}
for path, data in configs:
    board_name = path.parts[-2]
    distfiles = data.get("distfiles", [])
    board_map.setdefault(board_name, []).extend(distfiles)


@app.get("/board-images")
def list_board_names():
    """Return all available board names"""
    return {"boards": sorted(board_map.keys())}


@app.get("/board-images/{board_name}")
def get_board_urls(board_name: str):
    if board_name not in board_map:
        raise HTTPException(status_code=404, detail=f"Board '{board_name}' not found")

    distfiles = board_map[board_name]
    results = []

    for df in distfiles:
        name = df.get("name")
        urls = df.get("urls", [])
        url_results = []

        for url in urls:
            check_result = check_url(url, mirrors)
            url_results.append({
                "url": url,
                "result": check_result
            })

        results.append({
            "distfile": name,
            "urls": url_results
        })

    return {"board_name": board_name, "distfiles": results}
