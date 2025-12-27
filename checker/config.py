from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def load_board_image_configs(
    repo_root: Path | str,
    manifests_rel: str = "packages-index/manifests/board-image",
    pattern: str = "*.toml",  # match all TOML files (including config.toml) recursively
) -> List[Tuple[Path, Dict[str, Any]]]:
    root = Path(repo_root)
    base = root / manifests_rel
    if not base.is_dir():
        raise FileNotFoundError(f"manifests base not found: {base}")

    # **/ makes it recursive
    results: List[Tuple[Path, Dict[str, Any]]] = []
    for toml_path in sorted(base.glob(f"**/{pattern}")):
        if toml_path.is_file():
            with toml_path.open("rb") as f:
                data = tomllib.load(f)
            results.append((toml_path.relative_to(root), data))
    return results


def load_configs_as_dict(
    repo_root: Path | str,
    manifests_rel: str = "packages-index/manifests/board-image",
    pattern: str = "*.toml",
) -> Dict[str, Dict[str, Any]]:
    return {
        str(path): data
        for path, data in load_board_image_configs(
            repo_root=repo_root, manifests_rel=manifests_rel, pattern=pattern
        )
    }

def load_mirror_config(repo_root: Path | str) -> Dict[str, Dict[str, List[str]]]:
    root = Path(repo_root)
    config_path = root / "packages-index" / "config.toml"
    if not config_path.is_file():
        raise FileNotFoundError(f"mirror config not found: {config_path}")

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    return data.get("mirrors", {})


if __name__ == "__main__":
    repo_root = Path(os.getenv("REPO_ROOT", ".")).resolve()
    parsed = load_configs_as_dict(repo_root)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))