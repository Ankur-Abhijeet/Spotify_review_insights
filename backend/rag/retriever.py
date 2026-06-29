from typing import List, Dict, Any, Optional
from backend.rag.vector_store import VectorStore
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class Retriever:
    def __init__(self):
        self.store = VectorStore()

    def index_records(self, records: List[Dict[str, Any]]):
        if not records:
            return
            
        logger.info(f"[Retriever] Indexing {len(records)} records into ephemeral vector store...")
        app_docs, app_metas, app_ids = [], [], []
        comm_docs, comm_metas, comm_ids = [], [], []
        
        for r in records:
            source = r.get("source", "unknown")
            doc = r.get("body", "")
            meta = {
                "source": source,
                "user_segment": r.get("user_segment", "unknown"),
                "intent_archetype": r.get("intent_archetype", "unknown")
            }
            rid = str(r.get("review_id", ""))
            
            if source in ["app_store", "play_store"]:
                app_docs.append(doc)
                app_metas.append(meta)
                app_ids.append(rid)
            else:
                comm_docs.append(doc)
                comm_metas.append(meta)
                comm_ids.append(rid)
                
        if app_docs:
            self.store.app_reviews.add(documents=app_docs, metadatas=app_metas, ids=app_ids)
        if comm_docs:
            self.store.community_threads.add(documents=comm_docs, metadatas=comm_metas, ids=comm_ids)

    def query(self, query_text: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Queries both Memory 1 (App Reviews) and Memory 2 (Community Threads) in parallel.
        Returns a blended, formatted string of contexts for the LLM.
        """
        logger.info(f"[Retriever] Querying memories for: '{query_text}' with filters {filters}")
        
        where_clause = filters if filters else None
        
        results = []
        
        # 1. Query App Reviews
        try:
            app_res = self.store.app_reviews.query(
                query_texts=[query_text],
                n_results=k,
                where=where_clause
            )
            for i in range(len(app_res['ids'][0])):
                doc = app_res['documents'][0][i]
                meta = app_res['metadatas'][0][i]
                results.append({
                    "id": app_res['ids'][0][i],
                    "text": doc,
                    "source": meta.get("source", "app_review"),
                    "tag": f"[App Review: {meta.get('user_segment', 'unknown')}]"
                })
        except Exception as e:
            logger.warning(f"[Retriever] App Reviews query failed: {e}")

        # 2. Query Community Threads
        try:
            comm_res = self.store.community_threads.query(
                query_texts=[query_text],
                n_results=k,
                where=where_clause
            )
            for i in range(len(comm_res['ids'][0])):
                doc = comm_res['documents'][0][i]
                meta = comm_res['metadatas'][0][i]
                results.append({
                    "id": comm_res['ids'][0][i],
                    "text": doc,
                    "source": meta.get("source", "community_thread"),
                    "tag": f"[Community Thread: {meta.get('intent_archetype', 'unknown')}]"
                })
        except Exception as e:
            logger.warning(f"[Retriever] Community Threads query failed: {e}")
            
        logger.info(f"[Retriever] Retrieved {len(results)} total contexts.")
        return results

    def format_for_llm(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Formats the retrieved documents into a clean string for Prompt 3."""
        if not retrieved_docs:
            return "No relevant context found in the database."
            
        formatted = ""
        for idx, doc in enumerate(retrieved_docs, 1):
            formatted += f"\n--- Citation {idx} {doc['tag']} ---\n"
            formatted += f"Source ID: {doc['id']}\n"
            formatted += f"{doc['text']}\n"
            
        return formatted
