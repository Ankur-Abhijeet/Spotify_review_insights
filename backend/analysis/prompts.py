from typing import List, Dict, Any
import json

def get_analysis_prompt(reviews: List[Dict[str, Any]]) -> str:
    """
    Constructs the Prompt 1 template for the LLM to analyze a batch of reviews.
    Maintains the Growth Analyst persona and enforces the nested themes JSON schema.
    """
    
    # We strip out unnecessary fields to save token space.
    # We only need the body and perhaps the source context.
    clean_reviews = []
    for r in reviews:
        clean_reviews.append({
            "review_id": r.get("review_id"),
            "source": r.get("source"),
            "body": r.get("body")
        })
        
    reviews_json = json.dumps(clean_reviews, indent=2)
    
    prompt = f"""You are a Lead Growth Analyst at Spotify. Your goal is to deeply analyze user feedback to uncover why users struggle with music discovery and why they fall into repetitive listening loops.

Here is a batch of raw user reviews and forum discussions:
{reviews_json}

For EACH review in the batch, extract the following insights and output them strictly as a JSON array under the key "reviews". Do not include any other text. 

For each review, your JSON object must have:
- "review_id": (string) The exact review_id from the input.
- "user_segment": (enum: "casual", "power_user", "new_user", "churned", "unknown")
- "discovery_related": (boolean) Does this review explicitly mention trying to find new music?
- "user_intent": (string) Free-text description of their goal (e.g. "Wanted to find upbeat workout songs").
- "intent_archetype": (enum: "mood_listener", "genre_explorer", "social_discoverer", "passive_listener", "active_curator", "lapsed_discoverer", "unknown")
- "themes": (Array of Objects) For each distinct topic/theme mentioned in the review, create an object containing:
    - "theme_name": (string) e.g., "Algorithm Repetition", "UI Navigation", "Curated Playlists"
    - "sentiment": (enum: "positive", "negative", "neutral", "mixed")
    - "sentiment_score": (float) -1.0 to 1.0
    - "barrier_type": (enum: "algorithmic", "ui_ux", "content_gap", "awareness", "habit", "none")
    - "frustration_phrase": (string) A short 3-5 word verbatim-style summary of their frustration.
    - "repetition_trigger": (enum: "algorithm_lock", "no_exploration_ui", "comfort_habit", "no_new_content", "none")
    - "repetition_described": (boolean)
    - "unmet_need": (string) Underlying psychological or functional need Spotify failed to meet.
    - "segment_signal": (string) A short quote justifying why you chose the user_segment.

IMPORTANT RULES:
1. Your output MUST be valid, parseable JSON.
2. The root object must contain a "reviews" key pointing to the array of analyzed reviews.
3. You must process ALL reviews provided in the batch.
"""
    return prompt
