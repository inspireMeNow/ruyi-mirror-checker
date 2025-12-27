import time
from typing import Any, Dict, List, Optional, Tuple

import httpx


def is_mirror_url(url: str) -> bool:
    return url.startswith("mirror://")


def parse_mirror_url(url: str) -> Tuple[str, str]:
    """
    mirror://openbsd/OpenBSD/7.5/riscv64/install75.img
    -> ("openbsd", "OpenBSD/7.5/riscv64/install75.img")
    """
    rest = url[len("mirror://") :]
    mirror_name, path = rest.split("/", 1)
    return mirror_name, path


def check_http_url(
    url: str,
    timeout: float = 5.0,
) -> Dict[str, Optional[Any]]:
    start = time.monotonic()

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "ruyi-resource-bot/0.1"},
        ) as client:
            resp = client.head(url)
            status = resp.status_code

            # fallback
            if status >= 400:
                resp = client.get(url, headers={"Range": "bytes=0-0"})
                status = resp.status_code

        latency_ms = int((time.monotonic() - start) * 1000)

        return {
            "url": url,
            "available": status < 400 or status == 403,
            "status_code": status,
            "error": None,
            "latency_ms": latency_ms,
        }

    except httpx.TimeoutException:
        return {
            "url": url,
            "available": False,
            "status_code": None,
            "error": "timeout",
            "latency_ms": None,
        }
    except httpx.RequestError as e:
        return {
            "url": url,
            "available": False,
            "status_code": None,
            "error": str(e),
            "latency_ms": None,
        }


def check_mirror_url(
    mirror_url: str,
    mirrors_config: Dict[str, Dict[str, List[str]]],
    timeout: float = 5.0,
) -> Dict[str, Any]:
    mirror_name, path = parse_mirror_url(mirror_url)

    mirror_def = None
    if isinstance(mirrors_config, dict):
        mirror_def = mirrors_config.get(mirror_name)
    elif isinstance(mirrors_config, list):
        for item in mirrors_config:
            # match [[mirrors]].id in config.toml
            if isinstance(item, dict) and item.get("id") == mirror_name:
                mirror_def = item
                break

    if not mirror_def:
        return {
            "type": "mirror",
            "mirror": mirror_name,
            "path": path,
            "available": False,
            "error": f"mirror '{mirror_name}' not defined",
            "entries": [],
        }

    bases = mirror_def.get("urls", [])
    entries: List[Dict[str, Any]] = []

    for base in bases:
        full_url = base.rstrip("/") + "/" + path
        result = check_http_url(full_url, timeout=timeout)
        entries.append(result)

    return {
        "type": "mirror",
        "mirror": mirror_name,
        "path": path,
        "available": any(e["available"] for e in entries),
        "entries": entries,
    }


def check_url(
    url: str,
    mirrors_config: Dict[str, Dict[str, List[str]]],
    timeout: float = 5.0,
) -> Dict[str, Any]:
    if is_mirror_url(url):
        return check_mirror_url(url, mirrors_config, timeout=timeout)
    else:
        result = check_http_url(url, timeout=timeout)
        return {
            "type": "normal",
            **result,
        }
