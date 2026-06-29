from fastapi import APIRouter, HTTPException
from backend.utils.logger import get_logger
from backend.routers.pipeline import SESSION_DB

logger = get_logger(__name__)
router = APIRouter(prefix="/api")

@router.get("/insights")
async def get_insights():
    if not SESSION_DB.get("aggregated"):
        return {}
        
    response_data = {
        **SESSION_DB["aggregated"],
        "usage": SESSION_DB.get("usage", {})
    }
    return response_data

@router.get("/usage")
async def get_api_usage():
    return SESSION_DB.get("usage", {})
