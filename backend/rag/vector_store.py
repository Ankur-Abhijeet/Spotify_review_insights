import os
import chromadb
from chromadb.config import Settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class VectorStore:
    def __init__(self):
        try:
            self.client = chromadb.EphemeralClient(settings=Settings(allow_reset=True))
            
            # Memory 1: App Store & Play Store
            self.app_reviews = self.client.get_or_create_collection(
                name="app_reviews",
                metadata={"description": "Short-form mobile app reviews"}
            )
            
            # Memory 2: Reddit & Spotify Community
            self.community_threads = self.client.get_or_create_collection(
                name="community_threads",
                metadata={"description": "Long-form discussion threads and feature requests"}
            )
            logger.info("[VectorStore] Initialized successfully in-memory")
        except Exception as e:
            logger.error(f"[VectorStore] Failed to initialize ChromaDB: {e}")
            raise

    def get_collection(self, source: str):
        if source in ["app_store", "play_store"]:
            return self.app_reviews
        elif source in ["reddit", "spotify_community"]:
            return self.community_threads
        else:
            raise ValueError(f"Unknown source memory mapping: {source}")
