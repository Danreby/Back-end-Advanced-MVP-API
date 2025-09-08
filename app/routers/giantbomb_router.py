from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.giantbomb import search_games, get_game_by_guid, extract_cover_urls
import random

router = APIRouter(prefix="/gb", tags=["giantbomb"])


@router.get("/search", summary="Search games on GiantBomb")
def gb_search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    try:
        results = search_games(q, limit=limit)
    except Exception as e:
        import traceback
        print("❌ Erro em /gb/search:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    return {"count": len(results), "results": results}


@router.get("/search/autocomplete", summary="Autocomplete suggestions (name + guid)")
def gb_search_autocomplete(q: str = Query(..., min_length=1), limit: int = Query(8, ge=1, le=50)):
    try:
        results = search_games(q, limit=limit)
    except Exception as e:
        print("❌ Erro em /gb/search/autocomplete:", e)
        raise HTTPException(status_code=500, detail=str(e))

    suggestions = []
    for r in results:
        name = r.get("name") or r.get("title") or None
        guid = r.get("guid") or r.get("id") or None
        if name and guid:
            suggestions.append({"guid": guid, "name": name})
    return {"count": len(suggestions), "suggestions": suggestions}


@router.get("/games/{guid}", summary="Get GiantBomb game details by GUID")
def gb_game_detail(guid: str):
    try:
        game = get_game_by_guid(guid)
    except Exception as e:
        print("❌ Erro em /gb/games/{guid}:", e)
        raise HTTPException(status_code=500, detail=str(e))
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    covers = extract_cover_urls(game)
    return {"game": game, "covers": covers}


@router.get("/games/{guid}/covers", summary="Get only cover image URLs for a GiantBomb game")
def gb_game_covers(guid: str):
    try:
        game = get_game_by_guid(guid)
    except Exception as e:
        print("❌ Erro em /gb/games/{guid}/covers:", e)
        raise HTTPException(status_code=500, detail=str(e))
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    covers = extract_cover_urls(game)
    return {"guid": guid, "covers": covers}


@router.get("/games/{guid}/screenshots", summary="Get screenshots for a GiantBomb game (if available)")
def gb_game_screenshots(guid: str):
    try:
        game = get_game_by_guid(guid)
    except Exception as e:
        print("❌ Erro em /gb/games/{guid}/screenshots:", e)
        raise HTTPException(status_code=500, detail=str(e))
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    screenshots = []
    for key in ("screenshots", "images", "media", "image", "images_list"):
        if key in game and isinstance(game[key], list):
            for it in game[key]:
                # se item for dict com url
                if isinstance(it, dict):
                    url = it.get("url") or it.get("original") or it.get("thumb")
                    if url:
                        screenshots.append(url)
                elif isinstance(it, str):
                    screenshots.append(it)
    if not screenshots:
        img = game.get("image") or {}
        if isinstance(img, dict):
            for candidate in ("screen_url", "medium_url", "small_url", "original_url", "super_url", "thumb_url"):
                url = img.get(candidate)
                if url:
                    screenshots.append(url)
    return {"guid": guid, "count": len(screenshots), "screenshots": screenshots}


@router.get("/lookup", summary="Lookup by name (tries to match name exactly, else returns first matches)")
def gb_lookup_by_name(name: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=50)):
    try:
        results = search_games(name, limit=limit)
    except Exception as e:
        print("❌ Erro em /gb/lookup:", e)
        raise HTTPException(status_code=500, detail=str(e))
    if not results:
        raise HTTPException(status_code=404, detail="No games found for that name")

    lower_name = name.strip().lower()
    exact = None
    for r in results:
        candidate = (r.get("name") or r.get("title") or "").strip().lower()
        if candidate == lower_name:
            exact = r
            break
    if exact:
        return {"match_type": "exact", "game": exact}
    return {"match_type": "partial", "results": results}


@router.get("/bulk", summary="Bulk fetch games by comma-separated GUIDs")
def gb_bulk_lookup(guids: str = Query(..., description="Comma-separated list of GUIDs"), allow_missing: bool = Query(False)):
    guid_list = [g.strip() for g in guids.split(",") if g.strip()]
    if not guid_list:
        raise HTTPException(status_code=400, detail="No GUIDs provided")

    results = {}
    errors = {}
    for g in guid_list:
        try:
            game = get_game_by_guid(g)
            if not game:
                if allow_missing:
                    results[g] = None
                else:
                    errors[g] = "not found"
            else:
                results[g] = game
        except Exception as e:
            errors[g] = str(e)

    if errors and not allow_missing:
        raise HTTPException(status_code=500, detail={"errors": errors, "fetched": results})
    return {"count_requested": len(guid_list), "results": results, "errors": errors}


@router.get("/random", summary="Get a random game (best-effort)")
def gb_random_sample(seed: Optional[int] = Query(None), sample_q: str = Query("a", min_length=1), sample_limit: int = Query(100, ge=1, le=200)):
    try:
        pool = search_games(sample_q, limit=sample_limit)
    except Exception as e:
        print("❌ Erro em /gb/random:", e)
        raise HTTPException(status_code=500, detail=str(e))
    if not pool:
        raise HTTPException(status_code=404, detail="No games available for random selection")
    if seed is not None:
        random.seed(seed)
    chosen = random.choice(pool)
    return {"pool_size": len(pool), "selected": chosen}
