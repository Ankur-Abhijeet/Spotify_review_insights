from pydantic import BaseModel
from typing import List, Optional

class ScrapeJobRequest(BaseModel):
    sources: List[str] # e.g. ["play_store", "app_store"]
    limits: Optional[dict] = {"play_store": 100, "app_store": 100, "reddit": 100, "spotify_community": 100}

class PreprocessJobRequest(BaseModel):
    keywords: Optional[str] = ""

class AnalyzeJobRequest(BaseModel):
    keywords: Optional[List[str]] = None
    limit: Optional[int] = 50

class JobResponse(BaseModel):
    status: str
    job_id: str
    message: str
