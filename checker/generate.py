from pathlib import Path
import json
import os
from datetime import datetime, timezone

from checker.checker import check_url
from checker.config import load_board_image_configs, load_mirror_config


def main():
    repo_root = Path(os.getenv("REPO_ROOT", ".")).resolve()

    print(f"[INFO] Repo root: {repo_root}")

    mirrors = load_mirror_config(repo_root)
    configs = load_board_image_configs(repo_root)

    boards: dict[str, dict] = {}

    total_boards = 0
    total_urls = 0

    for path, data in configs:
        board_name = path.parts[-2]
        board = boards.setdefault(board_name, {"distfiles": []})
        total_boards += 1

        print(f"\n[BOARD] {board_name} ({path})")

        for df in data.get("distfiles", []):
            dist_name = df.get("name")
            urls = df.get("urls", [])

            print(f"  [DISTFILE] {dist_name}")

            urls_result = []
            for url in urls:
                total_urls += 1
                print(f"    [CHECK] {url}")

                result = check_url(url, mirrors)
                urls_result.append(result)

                status = "OK" if result.get("available") else "FAIL"
                print(f"      -> {status}")

            board["distfiles"].append({
                "name": dist_name,
                "urls": urls_result,
            })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "boards": boards,
    }

    out = Path("status.json")
    with out.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n[SUMMARY]")
    print(f"  Boards: {len(boards)}")
    print(f"  URLs checked: {total_urls}")
    print(f"  Output: {out.resolve()}")


if __name__ == "__main__":
    main()
