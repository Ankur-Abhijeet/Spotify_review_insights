from typing import List, Dict, Any, Tuple
from backend.rag.retriever import Retriever
from backend.analysis.llm_client import LLMClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ChatService:
    def __init__(self):
        self.retriever = Retriever()
        self.llm = LLMClient()

    async def answer_question(self, question: str, filters: dict = None) -> Tuple[str, List[Dict]]:
        """
        Retrieves context, formats Prompt 3, and asks the LLM to synthesize an answer.
        Returns the answer string and a list of citations used.
        """
        # 1. Retrieve Context
        raw_docs = self.retriever.query(question, k=5, filters=filters)
        context_str = self.retriever.format_for_llm(raw_docs)
        
        # 2. Build Prompt 3
        prompt = f"""You are an AI Product Researcher for Spotify. 
You are answering questions about user feedback regarding Spotify's algorithms and UI.

You MUST use ONLY the information provided in the Context below. 
If the Context does not contain the answer, say "I don't have enough data in the current reviews to answer that."

When you make a claim, you MUST cite the source inline using the format [Citation N].

--- CONTEXT ---
{context_str}
--- END CONTEXT ---

Question: {question}
Answer:"""

        # 3. Call LLM (we override json mode just to get raw text for chat)
        # Note: Our LLMClient was built for JSON, so we will use Groq directly or tweak LLMClient.
        # To avoid modifying LLMClient heavily right now, we can ask for JSON {"answer": "..."}
        json_prompt = prompt + '\n\nOutput your response strictly as a JSON object: {"answer": "your detailed response here"}'
        
        try:
            response = await self.llm.generate_json(json_prompt)
            answer = response.get("answer", "I encountered an error synthesizing the response.")
        except Exception as e:
            logger.error(f"[ChatService] LLM generation failed: {e}")
            answer = "I'm currently offline and cannot process that request."
            
        return answer, raw_docs
