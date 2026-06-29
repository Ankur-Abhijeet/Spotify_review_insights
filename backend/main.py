from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.routers import insights, reviews, chat, pipeline

app = FastAPI(
    title="Spotify Feedback Intelligence API",
    description="Backend services for analyzing and serving Spotify user feedback.",
    version="1.0.0"
)

from backend.config import settings

# Allow React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins since it's a stateless public API
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router, tags=["Insights Dashboard"])
app.include_router(reviews.router, tags=["Review Browser"])

app.include_router(chat.router, tags=["RAG Chatbot"])
app.include_router(pipeline.router, tags=["Pipeline"])

@app.get("/")
def read_root():
    return {"message": "Spotify Feedback API is running. Visit /docs for Swagger UI."}
