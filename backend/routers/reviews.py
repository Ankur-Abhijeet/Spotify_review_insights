import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.utils.logger import get_logger
from backend.routers.pipeline import SESSION_DB

logger = get_logger(__name__)
router = APIRouter(prefix="/api")

@router.get("/reviews")
async def get_paginated_reviews(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    segment: Optional[str] = None,
    theme: Optional[str] = None,
    sentiment: Optional[str] = None,
    discovery_only: Optional[bool] = None
):
    records = SESSION_DB.get("analyzed", [])

    # Apply filters
    filtered = []
    for r in records:
        if segment and r.get("user_segment") != segment:
            continue
        if discovery_only and not r.get("discovery_related"):
            continue
            
        themes = r.get("themes", [])
        if theme:
            if not any(t.get("theme_name") == theme for t in themes):
                continue
        if sentiment:
            if not any(t.get("sentiment") == sentiment for t in themes):
                continue
                
        filtered.append(r)

    # Paginate
    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size if size > 0 else 0,
        "data": filtered[start:end]
    }
