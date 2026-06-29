import os
import json
from collections import defaultdict
from typing import List, Dict, Any
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class Aggregator:
    def aggregate(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            logger.warning("[Aggregator] No data to aggregate.")
            return {}

        total_reviews = len(records)
        discovery_related_count = 0
        total_sentiment_score = 0.0
        
        theme_stats = defaultdict(lambda: {
            "frequency": 0, "total_sentiment": 0.0, "sources": set(),
            "frustrations": [], "unmet_needs": []
        })
        
        behavior_stats = defaultdict(lambda: {"frequency": 0, "discovery_count": 0, "intents": []})
        repetition_stats = defaultdict(lambda: {"frequency": 0, "segments": defaultdict(int)})
        segment_stats = defaultdict(lambda: {"frequency": 0, "total_sentiment": 0.0, "barriers": defaultdict(int)})
        unmet_needs_stats = defaultdict(lambda: {"frequency": 0, "total_sentiment": 0.0, "sources": set()})

        for review in records:
            # Global Review Stats
            if review.get("discovery_related"):
                discovery_related_count += 1
                
            seg = review.get("user_segment", "unknown")
            segment_stats[seg]["frequency"] += 1
            
            arch = review.get("intent_archetype", "unknown")
            behavior_stats[arch]["frequency"] += 1
            if review.get("discovery_related"):
                behavior_stats[arch]["discovery_count"] += 1
            if review.get("user_intent"):
                behavior_stats[arch]["intents"].append(review["user_intent"])

            # Nested Theme Stats
            themes = review.get("themes", [])
            review_sentiment_sum = 0.0
            
            for t in themes:
                t_name = t.get("theme_name", "Unknown")
                score = t.get("sentiment_score", 0.0)
                review_sentiment_sum += score
                
                theme_stats[t_name]["frequency"] += 1
                theme_stats[t_name]["total_sentiment"] += score
                theme_stats[t_name]["sources"].add(review.get("review_id", ""))
                if t.get("frustration_phrase") and t["frustration_phrase"] != "N/A":
                    theme_stats[t_name]["frustrations"].append(t["frustration_phrase"])
                    
                barrier = t.get("barrier_type", "none")
                if barrier != "none":
                    segment_stats[seg]["barriers"][barrier] += 1
                    
                trigger = t.get("repetition_trigger", "none")
                if trigger != "none":
                    repetition_stats[trigger]["frequency"] += 1
                    repetition_stats[trigger]["segments"][seg] += 1
                    
                need = t.get("unmet_need", "N/A")
                if need != "N/A":
                    unmet_needs_stats[need]["frequency"] += 1
                    unmet_needs_stats[need]["total_sentiment"] += score
                    unmet_needs_stats[need]["sources"].add(review.get("review_id", ""))

            # Average out review sentiment
            if themes:
                total_sentiment_score += (review_sentiment_sum / len(themes))
                segment_stats[seg]["total_sentiment"] += (review_sentiment_sum / len(themes))

        # Compile final outputs
        compiled_themes = []
        for name, data in theme_stats.items():
            freq = data["frequency"]
            avg_sent = data["total_sentiment"] / freq if freq > 0 else 0
            pain_score = freq * abs(avg_sent) * len(data["sources"])
            compiled_themes.append({
                "theme_name": name,
                "frequency": freq,
                "average_sentiment": round(avg_sent, 2),
                "pain_score": round(pain_score, 2),
                "top_frustrations": list(set(data["frustrations"]))[:5]
            })
        compiled_themes.sort(key=lambda x: x["pain_score"], reverse=True)

        compiled_behaviors = []
        for name, data in behavior_stats.items():
            compiled_behaviors.append({
                "intent_archetype": name,
                "frequency": data["frequency"],
                "discovery_percentage": round((data["discovery_count"] / data["frequency"]) * 100, 1) if data["frequency"] > 0 else 0,
                "sample_intents": list(set(data["intents"]))[:5]
            })

        compiled_rep = []
        for name, data in repetition_stats.items():
            compiled_rep.append({
                "repetition_trigger": name,
                "frequency": data["frequency"],
                "affected_segments": dict(data["segments"])
            })

        compiled_seg = []
        for name, data in segment_stats.items():
            freq = data["frequency"]
            compiled_seg.append({
                "user_segment": name,
                "frequency": freq,
                "average_sentiment": round(data["total_sentiment"] / freq, 2) if freq > 0 else 0,
                "top_barriers": dict(sorted(data["barriers"].items(), key=lambda x: x[1], reverse=True)[:3])
            })

        compiled_needs = []
        for name, data in unmet_needs_stats.items():
            freq = data["frequency"]
            avg_sent = data["total_sentiment"] / freq if freq > 0 else 0
            opp_score = freq * len(data["sources"]) * abs(avg_sent)
            compiled_needs.append({
                "unmet_need": name,
                "frequency": freq,
                "opportunity_score": round(opp_score, 2)
            })
        compiled_needs.sort(key=lambda x: x["opportunity_score"], reverse=True)

        summary = {
            "total_reviews": total_reviews,
            "overall_sentiment": round(total_sentiment_score / total_reviews, 2) if total_reviews > 0 else 0,
            "discovery_related_percentage": round((discovery_related_count / total_reviews) * 100, 1) if total_reviews > 0 else 0,
            "top_pain_point": compiled_themes[0]["theme_name"] if compiled_themes else "N/A",
            "top_opportunity": compiled_needs[0]["unmet_need"] if compiled_needs else "N/A"
        }
        
        return {
            "themes": compiled_themes,
            "behaviors": compiled_behaviors,
            "repetition_causes": compiled_rep,
            "segments": compiled_seg,
            "unmet_needs": compiled_needs,
            "summary": summary
        }
