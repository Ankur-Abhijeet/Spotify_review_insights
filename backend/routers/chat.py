from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.rag.chat_service import ChatService
from backend.utils.logger import get_logger
from backend.routers.pipeline import SESSION_DB

logger = get_logger(__name__)
router = APIRouter(prefix="/api")

class ChatRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]

chat_service = ChatService()

@router.post("/chat", response_model=ChatResponse)
async def ask_chatbot(request: ChatRequest):
    try:
        # We assume the user has clicked "Sync Chatbot Database" (Step 5) to index data.
        if not SESSION_DB.get("indexed"):
            logger.warning("[ChatAPI] Database not synced recently, using whatever is in ephemeral storage.")
            
        answer, citations = await chat_service.answer_question(request.query, request.filters)
        return ChatResponse(answer=answer, citations=citations)
    except Exception as e:
        logger.error(f"[ChatAPI] Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat query.")
