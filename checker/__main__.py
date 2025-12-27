from __future__ import annotations

import json
import os
from pathlib import Path

from checker import check_url
from config import load_board_image_configs, load_mirror_config


if __name__ == '__main__':
    repo_root = Path(os.getenv("REPO_ROOT", ".")).resolve()
    mirrors = load_mirror_config(repo_root)
    configs = load_board_image_configs(repo_root)

    for path, data in configs:
        distfiles = data.get("distfiles", [])
        if not distfiles:
            continue

        print(f"\n== {path} ==")

        for df in distfiles:
            name = df.get("name")
            urls = df.get("urls", [])

            for url in urls:
                print(f"-- distfile: {name} --")
                print(f"   url: {url}")

                result = check_url(url, mirrors)
                print(json.dumps(result, indent=2, ensure_ascii=False))
