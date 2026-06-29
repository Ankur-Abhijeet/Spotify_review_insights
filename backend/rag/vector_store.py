import os
import math
import re
from typing import List, Dict, Any, Optional
from backend.utils.logger import get_logger

logger = get_logger(__name__)

def tokenize(text: str) -> List[str]:
    """Tokenizes text into words for simple TF-IDF indexing."""
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())

class InMemoryCollection:
    """A lightweight, zero-dependency in-memory vector collection mimicking ChromaDB's API."""
    def __init__(self, name: str):
        self.name = name
        self.documents = []
        self.metadatas = []
        self.ids = []

    def add(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Adds documents to the collection."""
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)
        logger.info(f"[InMemoryCollection:{self.name}] Added {len(documents)} documents. Total: {len(self.documents)}")

    def query(self, query_texts: List[str], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queries the collection using TF-IDF text scoring and metadata filtering."""
        if not self.documents or not query_texts:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        query_text = query_texts[0]
        query_tokens = tokenize(query_text)
        
        # 1. Pre-tokenize and calculate document frequency (DF) for matching query terms
        num_docs = len(self.documents)
        doc_tokens = [tokenize(doc) for doc in self.documents]
        
        vocab = set(query_tokens)
        df = {}
        for token in vocab:
            df[token] = sum(1 for doc in doc_tokens if token in doc)

        # 2. Calculate Inverse Document Frequency (IDF) with smoothing
        idf = {}
        for token in vocab:
            idf[token] = math.log((num_docs + 1) / (df[token] + 1)) + 1

        # 3. Score all matched documents
        scores = []
        for idx, doc in enumerate(self.documents):
            # Apply metadata filters if 'where' is specified
            if where:
                match = True
                for key, val in where.items():
                    if self.metadatas[idx].get(key) != val:
                        match = False
                        break
                if not match:
                    continue

            tokens = doc_tokens[idx]
            if not tokens:
                continue
                
            # Compute TF-IDF inner product
            score = 0.0
            for token in query_tokens:
                if token in tokens:
                    tf = tokens.count(token) / len(tokens)
                    score += tf * idf[token]
            scores.append((score, idx))

        # 4. Sort and return top results
        scores.sort(key=lambda x: x[0], reverse=True)
        top_scores = scores[:n_results]

        ids_res = [self.ids[idx] for _, idx in top_scores]
        docs_res = [self.documents[idx] for _, idx in top_scores]
        metas_res = [self.metadatas[idx] for _, idx in top_scores]

        return {
            "ids": [ids_res],
            "documents": [docs_res],
            "metadatas": [metas_res]
        }

class VectorStore:
    """A lightweight database manager that exposes Collections matching ChromaDB's API."""
    def __init__(self):
        self.app_reviews = InMemoryCollection(name="app_reviews")
        self.community_threads = InMemoryCollection(name="community_threads")
        logger.info("[VectorStore] Initialized successfully in-memory (Lightweight TF-IDF mode)")

    def get_collection(self, source: str):
        if source in ["app_store", "play_store"]:
            return self.app_reviews
        elif source in ["reddit", "spotify_community"]:
            return self.community_threads
        else:
            raise ValueError(f"Unknown source memory mapping: {source}")
