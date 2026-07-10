import os
import time
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, Timeout, RequestException

load_dotenv()

BASE = "https://api.rawg.io/api"
API_KEY = os.getenv("RAWG_API_KEY")
DEFAULT_TIMEOUT = 15

_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 60 * 60  # 1 hora


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


def _get(path: str, params: Optional[dict] = None, retries: int = 3) -> dict:
    if not API_KEY:
        raise RuntimeError("RAWG_API_KEY não configurada no ambiente")

    params = dict(params or {})
    params["key"] = API_KEY
    url = f"{BASE}/{path.lstrip('/')}"

    attempt = 0
    last_error: Any = None
    while attempt < retries:
        try:
            r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                backoff = 0.5 * (2 ** attempt)
                print(f"⚠️ RAWG rate-limited. Aguardando {backoff}s (tentativa {attempt+1}/{retries})")
                time.sleep(backoff)
                attempt += 1
                continue
            r.raise_for_status()
        except (ConnectionError, Timeout, RequestException) as e:
            last_error = e
            backoff = 0.5 * (2 ** attempt)
            print(f"⚠️ RAWG falhou (tentativa {attempt+1}/{retries}): {e}")
            time.sleep(backoff)
            attempt += 1

    raise RuntimeError(f"RAWG API falhou após {retries} tentativas: {url}. Último erro: {last_error}")


def _map_game(raw: dict) -> dict:
    img = raw.get("background_image")
    image_obj = {"super_url": img, "medium_url": img, "small_url": img} if img else None

    description_raw = (raw.get("description_raw") or "").strip()
    deck = description_raw[:500] if description_raw else None

    return {
        "guid": f"rawg-{raw.get('slug', raw.get('id', ''))}",
        "id": raw.get("id"),
        "name": raw.get("name"),
        "original_release_date": raw.get("released"),
        "image": image_obj,
        "deck": deck,
        "description": raw.get("description"),
        "platforms": [{"name": p["platform"]["name"]} for p in raw.get("platforms", [])],
        "genres": [{"name": g["name"]} for g in raw.get("genres", [])],
        "publishers": [{"name": p["name"]} for p in raw.get("publishers", [])],
        "rating": raw.get("rating"),
        "reviews_count": raw.get("ratings_count"),
    }


def search_games(query: str, limit: int = 10, **kwargs) -> List[dict]:
    cache_key = f"search:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = _get("games", params={
        "search": query,
        "page_size": min(limit, 40),
        "search_precise": "true",
    })
    results = [_map_game(g) for g in data.get("results", [])]
    _cache_set(cache_key, results)
    return results


def get_game_by_guid(guid: str, **kwargs) -> Optional[dict]:
    cache_key = f"game:{guid}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    slug = guid.removeprefix("rawg-") if guid else guid
    data = _get(f"games/{slug}")
    result = _map_game(data)
    _cache_set(cache_key, result)
    return result


def extract_cover_urls(game_obj: dict) -> Dict[str, str]:
    image = game_obj.get("image") or {}
    if not isinstance(image, dict):
        return {}
    return {k: v for k, v in image.items() if isinstance(v, str) and v}
