from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.giantbomb import search_games, get_game_by_guid, extract_cover_urls

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

@router.get("/games/{guid}", summary="Get GiantBomb game details by GUID")
def gb_game_detail(guid: str):
    try:
        game = get_game_by_guid(guid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    covers = extract_cover_urls(game)
    return {"game": game, "covers": covers}
