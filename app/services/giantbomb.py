import os
import time
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, Timeout, RequestException
from http.client import RemoteDisconnected

load_dotenv()

BASE = "https://www.giantbomb.com/api"
API_KEY = os.getenv("GIANTBOMB_API_KEY")
DEFAULT_TIMEOUT = 10

_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 60 * 60 


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > entry["ttl"]:
        _cache.pop(key, None)
        return None
    return entry["value"]


def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    _cache[key] = {"value": value, "ts": time.time(), "ttl": ttl}


def _get(url_path: str, params: Optional[dict] = None, retries: int = 3) -> dict:
    if API_KEY is None:
        raise RuntimeError("GIANTBOMB_API_KEY not set in environment")

    params = dict(params or {})
    params.update({"api_key": API_KEY, "format": "json"})
    url = f"{BASE}/{url_path.lstrip('/')}"
    headers = {
        "User-Agent": "my-fastapi-app/1.0",
        "Accept": "application/json",
    }

    attempt = 0
    while attempt < retries:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)

            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    raise RuntimeError(f"Invalid JSON response from GiantBomb: {url}")

            if r.status_code == 429:
                backoff = 0.5 * (2 ** attempt)
                print(f"⚠️ GiantBomb rate-limited (429). Backing off {backoff}s (attempt {attempt+1}/{retries})")
                time.sleep(backoff)
                attempt += 1
                continue

            r.raise_for_status()

        except (ConnectionError, Timeout, RemoteDisconnected, RequestException) as e:
            backoff = 0.5 * (2 ** attempt)
            print(f"⚠️ GiantBomb connection/request failed (attempt {attempt+1}/{retries}): {e}")
            time.sleep(backoff)
            attempt += 1
            continue

    raise RuntimeError(f"GiantBomb API request failed after {retries} attempts: {url}")


def search_games(query: str, limit: int = 10, field_list: str = "id,guid,name,deck,original_release_date,image") -> List[dict]:
    cache_key = f"search:{query}:{limit}:{field_list}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params = {
        "query": query,
        "resources": "game",
        "field_list": field_list,
        "limit": limit
    }
    data = _get("search/", params=params)
    results = data.get("results", [])
    _cache_set(cache_key, results)
    return results


def get_game_by_guid(guid: str, field_list: str = "id,guid,name,deck,description,original_release_date,platforms,developers,publishers,genres,image,releases,images,videos") -> Optional[dict]:
    cache_key = f"game:{guid}:{field_list}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    path = f"game/{guid}/"
    data = _get(path, params={"field_list": field_list})
    result = data.get("results")
    _cache_set(cache_key, result)
    return result


def extract_cover_urls(game_obj: dict) -> Dict[str, str]:
    image = game_obj.get("image") or {}
    if not isinstance(image, dict):
        return {}

    covers: Dict[str, str] = {}
    for k, v in image.items():
        if isinstance(v, str) and v:
            covers[k] = v
        elif isinstance(v, dict):
            for candidate in ("url", "original", "super_url", "medium_url", "screen_url", "small_url", "thumb"):
                url = v.get(candidate)
                if isinstance(url, str) and url:
                    covers[f"{k}.{candidate}"] = url
                    break
    return covers
