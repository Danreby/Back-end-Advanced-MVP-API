import os
import time
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, Timeout
from http.client import RemoteDisconnected

load_dotenv()

BASE = "https://www.giantbomb.com/api"
API_KEY = os.getenv("GIANTBOMB_API_KEY")
DEFAULT_TIMEOUT = 10

_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 60 * 60 

def _cache_get(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > entry["ttl"]:
        _cache.pop(key, None)
        return None
    return entry["value"]

def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL):
    _cache[key] = {"value": value, "ts": time.time(), "ttl": ttl}

def _get(url_path: str, params: Optional[dict] = None, retries: int = 3) -> dict:
    """Internal GET with retry on 429, connection errors, and timeouts."""
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
                return r.json()

            if r.status_code == 429:
                backoff = 0.5 * (2 ** attempt)
                time.sleep(backoff)
                attempt += 1
                continue

            r.raise_for_status()

        except (ConnectionError, Timeout, RemoteDisconnected) as e:
            backoff = 0.5 * (2 ** attempt)
            print(f"⚠️ GiantBomb connection failed (attempt {attempt+1}/{retries}): {e}")
            time.sleep(backoff)
            attempt += 1
            continue

    raise RuntimeError(f"GiantBomb API request failed after {retries} attempts: {url}")

    """Internal GET with basic retry on 429 and error handling."""
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
        r = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            backoff = 0.5 * (2 ** attempt)
            time.sleep(backoff)
            attempt += 1
            continue
        r.raise_for_status()
    r.raise_for_status()

def search_games(query: str, limit: int = 10, field_list: str = "id,guid,name,deck,original_release_date,image") -> List[dict]:
    """Search games by name (uses the /search/ endpoint). Returns list of result dicts."""
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
    """Get a game by its GiantBomb GUID (ex: '3030-4725')."""
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
    """
    Given a game object (as returned by get_game_by_guid or search), returns available image URLs.
    Giant Bomb 'image' object typically contains keys like: icon_url, small_url, super_url, medium_url, screen_url.
    """
    image = game_obj.get("image") or {}
    return {k: v for k, v in image.items() if v}
