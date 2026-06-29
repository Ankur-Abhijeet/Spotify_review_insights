# ✅ Evaluation Criteria — Phase-Wise Testing & Exit Gates

> Each phase has specific, measurable exit criteria that must be met before proceeding to the next phase. This document defines what "done" means for each phase, the tests to run, and the acceptance thresholds.

---

## Table of Contents

1. [How to Use This Document](#1-how-to-use-this-document)
2. [Phase 0 — Scaffolding & Environment](#2-phase-0--scaffolding--environment)
3. [Phase 1 — Data Collection (Scrapers)](#3-phase-1--data-collection-scrapers)
4. [Phase 2 — Preprocessing & Normalization](#4-phase-2--preprocessing--normalization)
5. [Phase 3 — AI Analysis & Annotation](#5-phase-3--ai-analysis--annotation)
6. [Phase 4 — Aggregation & Insight Generation](#6-phase-4--aggregation--insight-generation)
7. [Phase 5 — Backend API Layer](#7-phase-5--backend-api-layer)
8. [Phase 8 — RAG Chatbot Integration](#8-phase-8--rag-chatbot-integration)
9. [Phase 6 — Frontend Dashboard](#9-phase-6--frontend-dashboard)
10. [Phase 7 — Export, Deployment & Polish](#10-phase-7--export-deployment--polish)

---

## 1. How to Use This Document

Each phase section contains:

- **Automated Tests**: Commands and scripts to validate outputs programmatically
- **Manual Checks**: Visual or functional verifications a developer must perform
- **Acceptance Thresholds**: Quantitative minimum bars (e.g., "≥80% of reviews have valid fields")
- **Exit Gate Checklist**: A checkbox list — every item must be checked before the phase is considered complete
- **Failure Recovery**: What to do when a test fails

> [!IMPORTANT]
> Do not proceed to the next phase unless **all** exit gate checkboxes are checked. Partial completion will cascade into harder-to-debug issues in later phases.

---

## 2. Phase 0 — Scaffolding & Environment

### Automated Tests

```bash
# 1. Python environment
cd backend
source venv/bin/activate
python -c "import fastapi, playwright, bs4, pydantic, reportlab, httpx, dotenv; print('All backend deps OK')"

# 2. Playwright browsers
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); p.stop(); print('Playwright OK')"

# 3. Frontend
cd ../frontend
npm run dev -- --host 0.0.0.0 &
sleep 5
curl -s http://localhost:5173 | head -1  # Should return HTML
kill %1

# 4. Ollama
ollama list | grep "llama3.1:8b"  # Should show the model
ollama list | grep "nomic-embed-text"  # Should show embedding model
curl -s http://localhost:11434/api/tags | python -m json.tool  # Should return valid JSON

# 5. Directory structure
for dir in data/raw/play_store data/raw/app_store data/raw/reddit data/raw/spotify_community data/preprocessed data/analyzed data/exports data/errors; do
  [ -d "$dir" ] && echo "OK: $dir" || echo "MISSING: $dir"
done

# 6. Config loading
cd backend
python -c "from config import settings; print(f'Ollama: {settings.OLLAMA_BASE_URL}, Model: {settings.OLLAMA_MODEL}')"

# 7. Utility modules
python -c "from utils.file_io import read_json, write_json; print('file_io OK')"
python -c "from utils.logger import get_logger; log = get_logger('test'); log.info('Logger OK')"
```

### Manual Checks

| # | Check | How to Verify |
|---|---|---|
| M-0.1 | `.env.example` exists with all variables documented | Open file, compare against [architecture.md Section 17.2](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/architecture.md) |
| M-0.2 | `.gitignore` excludes `data/`, `venv/`, `node_modules/`, `.env` | `cat .gitignore` |
| M-0.3 | React dev server shows blank page without errors | Open `http://localhost:5173`, check browser console |

### Exit Gate Checklist

- [ ] Python venv activates and all dependencies import without error
- [ ] Playwright launches and closes Chromium headlessly
- [ ] Frontend dev server starts and serves HTML on port 5173
- [ ] Ollama is running with both `llama3.1:8b` and `nomic-embed-text` listed
- [ ] All 8 data subdirectories exist (`raw/play_store`, `raw/app_store`, `raw/reddit`, `raw/spotify_community`, `preprocessed`, `analyzed`, `exports`, `errors`)
- [ ] `config.py` loads environment variables with defaults via Pydantic Settings
- [ ] `file_io.py` and `logger.py` are importable and functional
- [ ] `.env.example` committed, `.env` gitignored

---

## 3. Phase 1 — Data Collection (Scrapers)

### Automated Tests

```bash
# Run each scraper with minimal limit and validate output
cd backend
source venv/bin/activate

# 1. Play Store (quick test)
python -c "
import asyncio, json
from scrapers.play_store import PlayStoreScraper
results = asyncio.run(PlayStoreScraper().scrape(limit=10))
assert len(results) >= 5, f'Too few results: {len(results)}'
for r in results:
    assert 'review_id' in r, 'Missing review_id'
    assert 'body' in r and len(r['body']) > 0, 'Missing or empty body'
    assert 'source' in r and r['source'] == 'play_store', 'Wrong source'
    assert 'rating' in r and 1 <= r['rating'] <= 5, f'Invalid rating: {r[\"rating\"]}'
    assert 'date' in r, 'Missing date'
print(f'Play Store: {len(results)} reviews, all valid')
"

# 2. App Store (quick test)
python -c "
import asyncio
from scrapers.app_store import AppStoreScraper
results = asyncio.run(AppStoreScraper().scrape(limit=10))
assert len(results) >= 3, f'Too few results: {len(results)}'
for r in results:
    assert r['source'] == 'app_store'
    assert 'body' in r and len(r['body']) > 0
    assert 'rating' in r and 1 <= r['rating'] <= 5
print(f'App Store: {len(results)} reviews, all valid')
"

# 3. Reddit (quick test)
python -c "
import asyncio
from scrapers.reddit import RedditScraper
results = asyncio.run(RedditScraper().scrape(limit=5))
assert len(results) >= 2, f'Too few results: {len(results)}'
for r in results:
    assert r['source'] == 'reddit'
    assert 'body' in r and len(r['body']) > 0
print(f'Reddit: {len(results)} posts, all valid')
"

# 4. Spotify Community (quick test)
python -c "
import asyncio
from scrapers.spotify_community import SpotifyCommunityScraper
results = asyncio.run(SpotifyCommunityScraper().scrape(limit=5))
assert len(results) >= 1, f'Too few results: {len(results)}'
for r in results:
    assert r['source'] == 'spotify_community'
    assert 'body' in r and len(r['body']) > 0
print(f'Spotify Community: {len(results)} posts, all valid')
"

# 5. Validate saved files
for source in play_store app_store reddit spotify_community; do
    file="data/raw/$source/$(date +%Y-%m-%d).json"
    if [ -f "$file" ]; then
        count=$(python -c "import json; print(len(json.load(open('$file'))))")
        echo "OK: $source — $count records"
    else
        echo "MISSING: $file"
    fi
done

# 6. CLI runner
python scripts/run_scrapers.py --sources play_store --limit 5
echo "CLI runner exit code: $?"
```

### Acceptance Thresholds

| Metric | Minimum Threshold |
|---|---|
| Each scraper returns results with `--limit 10` | ≥ 5 results (50% fill rate accounts for anti-bot) |
| All returned records have `review_id`, `source`, `body`, `date` | 100% |
| App Store and Play Store records have valid `rating` (1–5) | 100% |
| Reddit and Community records have default `rating` (3) | 100% |
| Output JSON files are valid JSON | 100% |
| No unhandled exceptions during scrape | 0 crashes |
| Anti-bot retry engages and logs on failure | Visible in log output |

### Failure Recovery

| Failure | Action |
|---|---|
| Scraper returns 0 results | Check CSS selectors against live page DOM. Run with `SCRAPER_HEADLESS=false` to observe. |
| CAPTCHA or redirect detected | Increase delays. Try VPN or different IP. Check stealth plugin config. |
| Timeout errors | Increase Playwright timeout. Check network connectivity. |
| JSON write error | Check `data/raw/<source>/` directory exists and is writable. |
| `google-play-scraper` import error | Verify package is installed: `pip install google-play-scraper`. |

### Exit Gate Checklist

- [ ] `BaseScraper` abstract class implemented with browser lifecycle, delay, retry, save methods
- [ ] All 4 scrapers produce valid JSON with `--limit 10`
- [ ] All output records match the unified raw schema (`review_id`, `source`, `body`, `date`, `scraped_at`)
- [ ] `scripts/run_scrapers.py` runs with `--sources` and `--limit` flags
- [ ] Scrapers handle anti-bot blocks gracefully (retry + log, no unhandled crash)
- [ ] Output files saved to correct `data/raw/<source>/YYYY-MM-DD.json` path
- [ ] Re-running same day deduplicates by `review_id`, does not create duplicate entries

---

## 4. Phase 2 — Preprocessing & Normalization

### Automated Tests

```bash
# 1. Run preprocessing
python scripts/run_analysis.py --stage preprocess

# 2. Validate output exists and is valid JSON
python -c "
import json

data = json.load(open('data/preprocessed/all_reviews.json'))
print(f'Total preprocessed reviews: {len(data)}')

# Check no duplicates (by review_id)
ids = [r['review_id'] for r in data]
assert len(ids) == len(set(ids)), f'Duplicate review_ids found: {len(ids) - len(set(ids))}'

# Check all bodies are clean
for r in data:
    body = r['body']
    assert len(body.strip()) >= 20, f'Body too short: \"{body[:50]}\"'
    assert '<br>' not in body.lower(), f'HTML not stripped: \"{body[:50]}\"'
    assert '<a ' not in body.lower(), f'HTML link not stripped: \"{body[:50]}\"'
    assert '  ' not in body, f'Double spaces not normalized: \"{body[:50]}\"'

# Check sources are preserved
sources = set(r['source'] for r in data)
print(f'Sources present: {sources}')
assert len(sources) >= 1, 'No sources in preprocessed data'

# Verify Track 1 vs Track 2 routing
track1_sources = {'app_store', 'play_store'}
track2_sources = {'reddit', 'spotify_community'}
for r in data:
    assert r['source'] in track1_sources | track2_sources, f'Unknown source: {r[\"source\"]}'

print('All preprocessing validations passed')
"

# 3. Check dedup effectiveness
python -c "
import json, os, glob

# Count raw
raw_count = 0
for f in glob.glob('data/raw/*/*.json'):
    raw_count += len(json.load(open(f)))

preprocessed = json.load(open('data/preprocessed/all_reviews.json'))
removed = raw_count - len(preprocessed)
pct = (removed / raw_count * 100) if raw_count > 0 else 0
print(f'Raw: {raw_count}, Preprocessed: {len(preprocessed)}, Removed: {removed} ({pct:.1f}%)')
assert pct < 98, f'Dedup removed more than 98% — threshold too aggressive'
"

# 4. Verify engagement scores were computed
python -c "
import json
data = json.load(open('data/preprocessed/all_reviews.json'))
for r in data:
    assert 'engagement_score' in r, f'Missing engagement_score in review {r[\"review_id\"]}'
    assert isinstance(r['engagement_score'], (int, float)), f'Invalid engagement_score type'
print(f'All {len(data)} reviews have valid engagement scores')
"

# 5. Verify date normalization
python -c "
import json, re
data = json.load(open('data/preprocessed/all_reviews.json'))
date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
for r in data:
    assert date_pattern.match(r['date']), f'Invalid date format: {r[\"date\"]} (expected YYYY-MM-DD)'
print(f'All {len(data)} reviews have valid YYYY-MM-DD dates')
"
```

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| Output file `all_reviews.json` exists and is valid JSON | Required |
| No duplicate `review_id` values | 0 duplicates |
| All `body` fields ≥ 20 characters (Track 1) | 100% |
| No HTML tags in any `body` field | 100% |
| No double-spaces in any `body` field | 100% |
| Dedup removal rate | < 98% of raw total |
| All dates in `YYYY-MM-DD` format | 100% |
| `engagement_score` field present and numeric | 100% |
| At least 1 source represented | Required |

### Failure Recovery

| Failure | Action |
|---|---|
| `all_reviews.json` is empty | Check raw data files exist. Verify scraper outputs. |
| > 98% removal rate | Lower dedup Jaccard threshold. Check if keyword density filter is too narrow. |
| HTML tags persist | Debug BeautifulSoup stripping logic. Add missing tag patterns. |
| Date format errors | Add the failing format to `date_normalizer.py` parser cascade. |

### Exit Gate Checklist

- [ ] `preprocessor.py` implements merge, dedup, HTML strip, whitespace normalize, noise filter
- [ ] Track 1 filters applied to App Store & Play Store (emoji removal, <20 char, non-English, keyword density)
- [ ] Track 2 filters applied to Reddit & Spotify Community (thread-level chunking)
- [ ] `data/preprocessed/all_reviews.json` is produced
- [ ] Zero duplicate `review_id` values in output
- [ ] All bodies are ≥ 20 chars, no HTML, no double-spaces
- [ ] All dates normalized to `YYYY-MM-DD`
- [ ] Engagement scores computed for all records
- [ ] Dedup stats logged (raw count, duplicates removed, noise removed, final count)
- [ ] Runs successfully as `python scripts/run_analysis.py --stage preprocess`

---

## 5. Phase 3 — AI Analysis & Annotation

### Automated Tests

```bash
# 1. Run annotation on a small subset (for speed)
LLM_BATCH_SIZE=5 python scripts/run_analysis.py --stage annotate

# 2. Validate output schema
python -c "
import json

data = json.load(open('data/analyzed/reviews_analyzed.json'))
print(f'Total annotated reviews: {len(data)}')

REQUIRED_FIELDS_GLOBAL = [
    'discovery_related', 'user_segment', 'segment_signal', 
    'intent_archetype', 'repetition_described'
]
REQUIRED_FIELDS_THEME = [
    'theme_name', 'sentiment', 'sentiment_score', 'barrier_type', 
    'frustration_phrase', 'user_intent', 'repetition_trigger', 'unmet_need'
]

VALID_THEMES = {
    'discovery_friction', 'algorithm_repetition', 'recommendation_quality',
    'discover_weekly_specific', 'radio_quality', 'made_for_you_feedback',
    'genre_exploration', 'mood_based_listening', 'social_discovery',
    'cross_platform_discovery', 'concert_live_discovery', 'podcast_discovery',
    'algorithm_history_lock', 'feature_request', 'positive_discovery', 'unrelated'
}
VALID_SENTIMENTS = {'positive', 'negative', 'neutral', 'mixed'}
VALID_BARRIERS = {'algorithmic', 'ui_ux', 'content_gap', 'awareness', 'habit', 'none'}
VALID_ARCHETYPES = {'mood_listener', 'genre_explorer', 'social_discoverer', 'passive_listener', 'active_curator', 'lapsed_discoverer'}
VALID_TRIGGERS = {'algorithm_lock', 'no_exploration_ui', 'comfort_habit', 'no_new_content', 'none'}
VALID_SEGMENTS = {'casual', 'power_user', 'new_user', 'churned', 'unknown'}

errors = []
for i, r in enumerate(data):
    # Check global fields
    for field in REQUIRED_FIELDS_GLOBAL:
        if field not in r:
            errors.append(f'Review {i}: missing global field "{field}"')

    if r.get('intent_archetype') not in VALID_ARCHETYPES:
        errors.append(f'Review {i}: invalid intent_archetype "{r.get("intent_archetype")}"')
    if r.get('user_segment') not in VALID_SEGMENTS:
        errors.append(f'Review {i}: invalid user_segment "{r.get("user_segment")}"')
    if not isinstance(r.get('repetition_described'), bool):
        errors.append(f'Review {i}: repetition_described is not boolean')
    if not isinstance(r.get('discovery_related'), bool):
        errors.append(f'Review {i}: discovery_related is not boolean')

    # Check themes array
    if 'themes' not in r or not isinstance(r['themes'], list):
        errors.append(f'Review {i}: missing or invalid themes array')
        continue

    for t_idx, theme in enumerate(r['themes']):
        for field in REQUIRED_FIELDS_THEME:
            if field not in theme:
                errors.append(f'Review {i} Theme {t_idx}: missing field "{field}"')

        if theme.get('theme_name') not in VALID_THEMES:
            errors.append(f'Review {i} Theme {t_idx}: invalid theme_name "{theme.get("theme_name")}"')
        if theme.get('sentiment') not in VALID_SENTIMENTS:
            errors.append(f'Review {i} Theme {t_idx}: invalid sentiment "{theme.get("sentiment")}"')
        score = theme.get('sentiment_score', 0)
        if not (-1.0 <= score <= 1.0):
            errors.append(f'Review {i} Theme {t_idx}: sentiment_score {score} out of range')
        if theme.get('barrier_type') not in VALID_BARRIERS:
            errors.append(f'Review {i} Theme {t_idx}: invalid barrier_type "{theme.get("barrier_type")}"')
        if theme.get('repetition_trigger') not in VALID_TRIGGERS:
            errors.append(f'Review {i} Theme {t_idx}: invalid repetition_trigger "{theme.get("repetition_trigger")}"')

        # Verify discovery_related consistency
        if theme.get('theme_name') == 'unrelated' and r.get('discovery_related') == True:
            errors.append(f'Review {i} Theme {t_idx}: theme_name=unrelated but review discovery_related=True')

if errors:
    print(f'VALIDATION ERRORS ({len(errors)}):')
    for e in errors[:20]:
        print(f'  - {e}')
    if len(errors) > 20:
        print(f'  ... and {len(errors) - 20} more')
else:
    print('All validations passed')

valid = len(data) - len(set(e.split(':')[0] for e in errors))
pct = valid / len(data) * 100 if data else 0
print(f'Valid reviews: {valid}/{len(data)} ({pct:.1f}%)')
assert pct >= 80, f'Less than 80% valid — check prompt design'
"

# 3. Check for error files
error_count=$(ls data/errors/*.json 2>/dev/null | wc -l)
echo "Failed batches: $error_count"

# 4. Test retry-failed
if [ "$error_count" -gt 0 ]; then
    python scripts/run_analysis.py --retry-failed
    new_error_count=$(ls data/errors/*.json 2>/dev/null | wc -l)
    echo "After retry: $new_error_count failed batches remain"
fi

# 5. Verify original metadata preserved
python -c "
import json
data = json.load(open('data/analyzed/reviews_analyzed.json'))
ORIGINAL_FIELDS = ['review_id', 'source', 'body', 'date', 'rating']
for r in data[:10]:
    for field in ORIGINAL_FIELDS:
        assert field in r, f'Original field {field} missing after annotation'
print('Original metadata preserved in all sampled reviews')
"

# 6. Check provider annotation source tracking
python -c "
import json
data = json.load(open('data/analyzed/reviews_analyzed.json'))
mock_count = sum(1 for r in data if r.get('annotation_source') == 'mock')
total = len(data)
if mock_count > 0:
    print(f'WARNING: {mock_count}/{total} reviews annotated with mock heuristics ({mock_count/total*100:.1f}%)')
else:
    print(f'All {total} reviews annotated with LLM provider')
"
```

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| All 13 required fields present (global + theme) | ≥ 95% of reviews |
| `theme_name` contains valid taxonomy value | ≥ 80% of themes |
| All enum fields contain valid values | ≥ 80% of themes |
| `sentiment_score` in [-1.0, 1.0] range | 100% |
| `themes` is a list (not string) | 100% |
| `repetition_described` is boolean | 100% |
| `discovery_related` is boolean | 100% |
| `theme_name == "unrelated"` implies `discovery_related == False` | 100% |
| Original metadata fields preserved | 100% |
| Failed batch rate | ≤ 10% of total batches |
| Failed batches saved to `data/errors/` | 100% of failures |
| `--retry-failed` reduces error count | Recovers ≥ 50% of failures |

### Failure Recovery

| Failure | Action |
|---|---|
| > 20% invalid enum values | Revise prompt in `prompts.py`. Add explicit examples and stricter output formatting. Re-run annotation. |
| > 10% batch failures | Reduce `LLM_BATCH_SIZE` to 10. Check Ollama logs for OOM. |
| Ollama connection refused | Verify `ollama serve` is running. Check `OLLAMA_BASE_URL` in `.env`. |
| Groq 429 errors | Wait for rate limit reset. Consider reducing batch size or adding longer sleep intervals. |
| Very slow (> 2 min per batch) | Switch to `llama3.1:8b` if using larger model. Check GPU utilization. |
| All reviews annotated as "mock" | Ollama or Groq is unreachable. Verify LLM connectivity. |

### Exit Gate Checklist

- [ ] `llm_client.py` supports Groq → Ollama → Mock fallback cascade
- [ ] `prompts.py` contains Prompt 1 system prompt with all 6 RQs, theme taxonomy, and nested JSON output format
- [ ] `batch_analyzer.py` processes reviews in batches of 20 with progress logging
- [ ] `normalize_and_validate()` clamps invalid enums, coerces types, bounds scores across themes array
- [ ] `reviews_analyzed.json` contains all reviews with global and theme-level AI-extracted fields
- [ ] ≥ 80% of themes have valid enum values in all fields
- [ ] All `sentiment_score` values are in [-1.0, 1.0]
- [ ] `discovery_related` is `False` when `theme_name` is `"unrelated"`
- [ ] Original review metadata (review_id, source, body, date, rating) preserved
- [ ] Failed batches are saved to `data/errors/`
- [ ] `--retry-failed` recovers at least some failed batches
- [ ] Progress logging shows batch count, reviews processed, and ETA
- [ ] Pipeline is resumable (skips already-annotated review_ids)

---

## 6. Phase 4 — Aggregation & Insight Generation

### Automated Tests

```bash
# 1. Run aggregation
python scripts/run_analysis.py --stage aggregate

# 2. Validate all 6 output files
python -c "
import json, os

FILES = {
    'themes.json': ['theme_id', 'label', 'frequency', 'avg_sentiment_score', 'sources', 'score'],
    'behaviors.json': ['archetype', 'label', 'frequency', 'pct_of_discovery_reviews'],
    'repetition_causes.json': ['trigger', 'label', 'frequency', 'affected_segments'],
    'segments.json': ['user_segment', 'frequency'],
    'unmet_needs.json': ['need_id', 'label', 'frequency', 'opportunity_score'],
    'summary.json': ['total_reviews', 'discovery_related_count', 'sources', 'top_5_themes'],
}

for filename, required in FILES.items():
    path = f'data/analyzed/{filename}'
    if not os.path.exists(path):
        print(f'MISSING: {path}')
        continue

    data = json.load(open(path))

    if isinstance(data, list):
        print(f'OK: {filename} — {len(data)} records')
        if data:
            missing = [f for f in required if f not in data[0]]
            if missing:
                print(f'  WARNING: Missing fields in first record: {missing}')
    elif isinstance(data, dict):
        print(f'OK: {filename} — dict with {len(data)} keys')
        missing = [f for f in required if f not in data]
        if missing:
            print(f'  WARNING: Missing fields: {missing}')
    else:
        print(f'ERROR: {filename} — unexpected type {type(data)}')
"

# 3. Validate theme scores
python -c "
import json

themes = json.load(open('data/analyzed/themes.json'))
for t in themes:
    assert t['frequency'] > 0, f'Theme {t[\"theme_id\"]} has zero frequency'
    assert -1.0 <= t['avg_sentiment_score'] <= 1.0, f'Theme {t[\"theme_id\"]} sentiment out of range'
    assert t.get('score', 0) >= 0, f'Theme {t[\"theme_id\"]} has negative pain score'
    total_source = sum(t['sources'].values()) if isinstance(t.get('sources'), dict) else 0
    if total_source > 0:
        assert total_source >= t['frequency'] * 0.8, f'Theme {t[\"theme_id\"]} source total doesn\\'t match frequency'
print(f'All {len(themes)} themes valid')
"

# 4. Validate opportunity scores
python -c "
import json

needs = json.load(open('data/analyzed/unmet_needs.json'))
for n in needs:
    assert n['frequency'] > 0, f'Need {n[\"need_id\"]} has zero frequency'
    assert n.get('opportunity_score', 0) > 0, f'Need {n[\"need_id\"]} has non-positive opportunity score'
print(f'All {len(needs)} unmet needs valid, sorted by opportunity score')

# Verify sorting
scores = [n['opportunity_score'] for n in needs]
assert scores == sorted(scores, reverse=True), 'Unmet needs are not sorted by opportunity_score descending'
print('Opportunity score sorting verified')
"

# 5. Validate summary consistency
python -c "
import json

summary = json.load(open('data/analyzed/summary.json'))
reviews = json.load(open('data/analyzed/reviews_analyzed.json'))

assert summary['total_reviews'] == len(reviews), \
    f'Summary total ({summary[\"total_reviews\"]}) != actual ({len(reviews)})'

disc = sum(1 for r in reviews if r.get('discovery_related'))
assert summary['discovery_related_count'] == disc, \
    f'Summary discovery count ({summary[\"discovery_related_count\"]}) != actual ({disc})'

# Verify discovery percentage
expected_pct = round(disc / len(reviews) * 100, 1) if reviews else 0.0
assert abs(summary.get('discovery_related_pct', 0) - expected_pct) < 0.2, \
    f'Summary discovery pct ({summary.get(\"discovery_related_pct\")}) != expected ({expected_pct})'

print('Summary consistency check passed')
"

# 6. Validate pain score formula
python -c "
import json

themes = json.load(open('data/analyzed/themes.json'))
reviews = json.load(open('data/analyzed/reviews_analyzed.json'))

# Spot check first theme
t = themes[0]
matching = [r for r in reviews if r.get('primary_theme') == t['theme_id']]
if matching:
    avg_abs_sent = sum(abs(r.get('sentiment_score', 0)) for r in matching) / len(matching)
    sources = set(r.get('source') for r in matching)
    expected_score = len(matching) * avg_abs_sent * len(sources)
    actual = t.get('score', 0)
    assert abs(expected_score - actual) < 1.0, f'Pain score mismatch: expected {expected_score:.1f}, got {actual:.1f}'
    print(f'Pain score formula verified for theme: {t[\"theme_id\"]}')
"
```

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| All 6 output files exist and are valid JSON | 100% |
| `themes.json` has ≥ 5 themes with frequency > 0 | Required |
| `behaviors.json` has ≥ 3 archetypes | Required |
| `segments.json` has ≥ 3 segments | Required |
| `summary.json` `total_reviews` matches `reviews_analyzed.json` count | Exact match |
| `summary.json` `discovery_related_count` matches actual count | Exact match |
| `summary.json` `discovery_related_pct` matches calculated percentage | Within 0.2% |
| All theme `avg_sentiment_score` values in [-1.0, 1.0] | 100% |
| All `opportunity_score` values > 0 in `unmet_needs.json` | 100% |
| `unmet_needs.json` sorted by `opportunity_score` descending | Required |
| Pain score formula verified for ≥ 1 theme | Required |

### Exit Gate Checklist

- [ ] `aggregator.py` produces `themes.json` with frequency, avg sentiment, pain scores, source breakdown
- [ ] `aggregator.py` produces `behaviors.json` with archetype distribution and discovery review percentage
- [ ] `aggregator.py` produces `repetition_causes.json` with trigger frequencies and affected segments
- [ ] `aggregator.py` produces `segments.json` with per-segment sentiment, themes, and barriers
- [ ] `aggregator.py` produces `unmet_needs.json` with SequenceMatcher clustering and opportunity scores
- [ ] `summary.json` has accurate counts matching the analyzed reviews
- [ ] All output files have correct schemas with required fields
- [ ] Theme pain scores computed using formula: `frequency × avg(|sentiment_score|) × source_count`
- [ ] Unmet needs sorted by `opportunity_score` descending
- [ ] Human-readable label mappings applied to all enum keys
- [ ] Runs via `python scripts/run_analysis.py --stage aggregate`

---

## 7. Phase 5 — Backend API Layer

### Automated Tests

```bash
# 1. Start the server
source backend/venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 3

# 2. Test each endpoint
echo "=== Testing API Endpoints ==="

# Health check
curl -sf http://localhost:8000/health | python -m json.tool > /dev/null && echo "OK: GET /health" || echo "FAIL: GET /health"

# Summary
curl -sf http://localhost:8000/api/summary | python -m json.tool > /dev/null && echo "OK: GET /api/summary" || echo "FAIL: GET /api/summary"

# Summary usage
curl -sf http://localhost:8000/api/summary/usage | python -m json.tool > /dev/null && echo "OK: GET /api/summary/usage" || echo "FAIL: GET /api/summary/usage"

# Reviews (with pagination)
curl -sf "http://localhost:8000/api/reviews?page=1&per_page=10" | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'total' in data, 'Missing total'
assert 'results' in data, 'Missing results'
assert len(data['results']) <= 10, 'Exceeds per_page'
print(f'OK: GET /api/reviews — {data[\"total\"]} total, {len(data[\"results\"])} returned')
"

# Reviews with filters
curl -sf "http://localhost:8000/api/reviews?source=play_store&sentiment=negative&discovery_only=true" | python -c "
import sys, json
data = json.load(sys.stdin)
for r in data['results']:
    assert r['source'] == 'play_store', f'Filter leak: {r[\"source\"]}'
    assert r['sentiment'] == 'negative', f'Filter leak: {r[\"sentiment\"]}'
    assert r['discovery_related'] == True, f'Filter leak: discovery_related'
print(f'OK: GET /api/reviews (filtered) — {len(data[\"results\"])} results, all filters applied')
"

# Themes
curl -sf http://localhost:8000/api/themes | python -m json.tool > /dev/null && echo "OK: GET /api/themes" || echo "FAIL: GET /api/themes"

# Behaviors
curl -sf http://localhost:8000/api/behaviors | python -m json.tool > /dev/null && echo "OK: GET /api/behaviors" || echo "FAIL: GET /api/behaviors"

# Segments
curl -sf http://localhost:8000/api/segments | python -m json.tool > /dev/null && echo "OK: GET /api/segments" || echo "FAIL: GET /api/segments"

# Unmet Needs
curl -sf http://localhost:8000/api/unmet-needs | python -m json.tool > /dev/null && echo "OK: GET /api/unmet-needs" || echo "FAIL: GET /api/unmet-needs"

# Insights
curl -sf http://localhost:8000/api/insights/discovery-friction | python -m json.tool > /dev/null && echo "OK: GET /api/insights/discovery-friction" || echo "FAIL"
curl -sf http://localhost:8000/api/insights/recommendation-frustrations | python -m json.tool > /dev/null && echo "OK: GET /api/insights/recommendation-frustrations" || echo "FAIL"
curl -sf http://localhost:8000/api/insights/repetition-causes | python -m json.tool > /dev/null && echo "OK: GET /api/insights/repetition-causes" || echo "FAIL"

# PDF Export
curl -sf -o /tmp/test_report.pdf "http://localhost:8000/api/export/pdf?include_q1=true&include_q2=true"
file /tmp/test_report.pdf | grep -q "PDF" && echo "OK: GET /api/export/pdf" || echo "FAIL: GET /api/export/pdf"

# CORS
curl -sf -H "Origin: http://localhost:5173" -I http://localhost:8000/api/summary | grep -i "access-control" && echo "OK: CORS headers present" || echo "FAIL: CORS"

# Cleanup
kill $SERVER_PID 2>/dev/null
```

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| All GET endpoints return valid JSON | 100% |
| `/api/reviews` pagination respects `per_page` limit | 100% |
| `/api/reviews` filters correctly narrow results | 100% (no filter leaks) |
| CORS headers present for configured origins | Required |
| PDF export is valid PDF file | Required |
| `/health` endpoint returns 200 | Required |
| Response time for all GET endpoints | < 2 seconds |
| No 500 errors on valid requests | 0 |
| Graceful empty response when no data exists | Required |

### Failure Recovery

| Failure | Action |
|---|---|
| 500 on any endpoint | Check server logs. Verify data files exist in `data/analyzed/`. |
| Filter leak in `/api/reviews` | Debug filter logic in `reviews.py` router. Add assertion tests. |
| CORS errors | Update `CORS_ORIGINS` in `.env`. Verify middleware order in `main.py`. |
| PDF generation crash | Check ReportLab installation. Test with minimal data. |
| Slow response times | Profile data loading. Consider caching aggregated files in memory. |

### Exit Gate Checklist

- [ ] `main.py` starts with CORS and all routers registered
- [ ] `GET /health` returns 200 with health status
- [ ] `GET /api/summary` returns executive summary metrics
- [ ] `GET /api/reviews` pagination works correctly (total, page, per_page, results)
- [ ] All filter parameters on `/api/reviews` work independently and in combination
- [ ] `GET /api/themes`, `/behaviors`, `/segments`, `/unmet-needs` return valid data
- [ ] `GET /api/insights/*` endpoints return Q1, Q2, Q4 analysis
- [ ] `POST /api/scrape` spawns background job and returns job_id
- [ ] `GET /api/scrape/{job_id}` returns job status and log tail
- [ ] `POST /api/analyze` spawns background analysis job
- [ ] `GET /api/export/pdf` returns valid PDF file
- [ ] CORS headers allow the frontend origin
- [ ] Pydantic models validate response schemas
- [ ] Graceful empty responses when aggregated data files don't exist
- [ ] No unhandled exceptions on valid requests

---

## 8. Phase 8 — RAG Chatbot Integration

### Automated Tests

```bash
# 1. Run vector store ingestion
python scripts/ingest_reviews.py --source all
echo "Ingestion exit code: $?"

# 2. Verify ingestion — both collections exist
python -c "
import chromadb
client = chromadb.PersistentClient(path='backend/data/vectorstore')

# Memory 1: Individual Reviews (App Store + Play Store)
try:
    mem1 = client.get_collection('memory_1_reviews')
    print(f'Memory 1 (Reviews): {mem1.count()} documents')
    assert mem1.count() > 0, 'Memory 1 is empty'
except Exception as e:
    print(f'ERROR: Memory 1 collection not found: {e}')

# Memory 2: Discussion Threads (Reddit + Spotify Community)
try:
    mem2 = client.get_collection('memory_2_threads')
    print(f'Memory 2 (Threads): {mem2.count()} documents')
    assert mem2.count() > 0, 'Memory 2 is empty'
except Exception as e:
    print(f'ERROR: Memory 2 collection not found: {e}')
"

# 3. Verify metadata indexing
python -c "
import chromadb
client = chromadb.PersistentClient(path='backend/data/vectorstore')
mem1 = client.get_collection('memory_1_reviews')
sample = mem1.peek(1)
if sample and sample['metadatas']:
    meta = sample['metadatas'][0]
    required_meta = ['source', 'rating', 'sentiment', 'user_segment', 'primary_theme']
    for field in required_meta:
        assert field in meta, f'Missing metadata field: {field}'
    print(f'Metadata fields verified: {list(meta.keys())}')
"

# 4. Test vector similarity retrieval
python -c "
from backend.rag.retriever import retrieve_relevant_reviews
results = retrieve_relevant_reviews(query='recommendations loop', limit=5)
print(f'Retrieved {len(results)} items')
assert len(results) > 0, 'No documents retrieved'
for doc in results:
    assert 'document' in doc, 'Missing document text'
    assert 'metadata' in doc, 'Missing document metadata'
    assert 'source' in doc['metadata'], 'Missing source in metadata'
print('Retrieval test passed')
"

# 5. Test dual-memory retrieval
python -c "
from backend.rag.retriever import query_memories
mem1_results, mem2_results = query_memories(query='Why do recommendations repeat?', k=5)
print(f'Memory 1 results: {len(mem1_results)}, Memory 2 results: {len(mem2_results)}')
assert len(mem1_results) > 0 or len(mem2_results) > 0, 'Both memories returned 0 results'
"

# 6. Test RAG chat endpoint
curl -sf -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Why do users feel recommendation is repetitive?"}' \
  | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'answer' in data and len(data['answer']) > 0, 'Missing or empty answer'
assert 'sources' in data, 'Missing sources'
assert isinstance(data['sources'], list), 'Sources should be a list'
assert len(data['sources']) > 0, 'No sources returned'
print(f'OK: Chat response ({len(data[\"answer\"])} chars, {len(data[\"sources\"])} sources)')
"

# 7. Test chat with metadata filters
curl -sf -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What frustrates users?", "filters": {"sentiment": "negative"}}' \
  | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'answer' in data and len(data['answer']) > 0, 'Filtered chat failed'
print(f'OK: Filtered chat response ({len(data[\"answer\"])} chars)')
"

# 8. Verify citation format
curl -sf -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main discovery pain points?"}' \
  | python -c "
import sys, json, re
data = json.load(sys.stdin)
answer = data.get('answer', '')
citations = re.findall(r'\[.*?#\d+\]', answer)
print(f'Citations found in response: {len(citations)}')
if len(citations) == 0:
    print('WARNING: No bracket citations found in response text')
"
```

### Manual Checks

| # | Check | How to Verify | Pass Criteria |
|---|---|---|---|
| M-8.1 | **Chat Page (`/chat`) loads** | Navigate to `/chat` | Premium layout renders, includes helpful quick-start suggestions. |
| M-8.2 | **Ask suggested query** | Click a suggestion tag | Conversation starts, typing indicator shows, response loads. |
| M-8.3 | **Verify citations rendering** | Review chatbot responses | Clickable bracket numbers or tags (e.g., `[Review #1]`, `[Discussion #3]`) exist. |
| M-8.4 | **Verify citations popup** | Click or hover a citation tag | Tooltip or side panel shows exact review body, date, rating, and source. |
| M-8.5 | **Chat filter drawer** | Toggle filters panel | Selecting a source/segment limits retrieval range (evident in citations). |
| M-8.6 | **Clear chat function** | Click "Clear Chat" button | History clears, page resets to quick-start state. |
| M-8.7 | **Robust error handling** | Shut down Ollama/API, type query | Graceful error UI message shows instead of crash. |

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| Memory 1 populated with App Store + Play Store reviews | 100% of analyzed reviews |
| Memory 2 populated with Reddit + Community threads | 100% of analyzed threads |
| Ingestion execution finishes without error | 100% success rate |
| Metadata fields indexed per document | 5 fields (source, rating, sentiment, user_segment, primary_theme) |
| Similarity search returns relevant results | > 0 results for any discovery-related query |
| Chatbot synthesis response time | < 10 seconds (Ollama) / < 4 seconds (Groq) |
| Chat response includes citations | ≥ 1 citation per response |
| Citation metadata maps to real review records | 100% |
| Dual-memory retrieval queries both collections | Required |

### Exit Gate Checklist

- [ ] ChromaDB persistent client initialized at `backend/data/vectorstore`
- [ ] `OllamaEmbeddingFunction` implemented with mock fallback (768-dim vectors)
- [ ] `ingest_reviews.py` partitions data into Memory 1 (reviews) and Memory 2 (threads)
- [ ] Both collections populated with correct metadata fields indexed
- [ ] `retriever.py` queries both memories with top-K retrieval and metadata pre-filters
- [ ] Citation tagging distinguishes `[Review #N]` from `[Discussion #N]`
- [ ] `chat_service.py` formats Prompt 3 with retrieved context and user query
- [ ] `POST /api/chat` returns synthesis text, sources array, and metadata
- [ ] Chat endpoint handles empty vector store gracefully
- [ ] Chat endpoint handles LLM failures gracefully (returns error message, not 500)
- [ ] Embedding model version tracked and consistent between ingestion and query

---

## 9. Phase 6 — Frontend Dashboard

### Automated Tests

```bash
# 1. Build check (no compile errors)
cd frontend
npm run build
echo "Build exit code: $?"

# 2. Dev server starts
npm run dev &
sleep 5
curl -sf http://localhost:5173 | grep -q "<div id=\"root\">" && echo "OK: Dev server" || echo "FAIL"
kill %1
```

### Manual Checks

| # | Check | How to Verify | Pass Criteria |
|---|---|---|---|
| M-6.1 | **Dashboard (`/`) loads** | Open in browser | KPI cards show data, charts render, no console errors |
| M-6.2 | **Source breakdown chart** | Dashboard page | Donut chart shows all sources with correct proportions |
| M-6.3 | **Top themes chart** | Dashboard page | Bar chart shows ≥ 5 themes, sorted by frequency |
| M-6.4 | **Theme Explorer (`/themes`)** | Navigate to themes | Treemap renders, clicking a theme opens drill-down panel |
| M-6.5 | **Theme drill-down** | Click any theme | Shows sub-themes, frustration phrases, unmet needs, sample reviews |
| M-6.6 | **Review Browser (`/reviews`)** | Navigate to reviews | Table loads with data, columns are correct |
| M-6.7 | **Review filters** | Use filter panel | Each filter narrows results; clearing filter restores all |
| M-6.8 | **Review detail modal** | Click a review row | Full text + all 14 AI fields displayed |
| M-6.9 | **Segments page (`/segments`)** | Navigate to segments | Side-by-side cards render with per-segment data |
| M-6.10 | **Chat page (`/chat`)** | Navigate to chat | Chat interface loads with suggestion chips |
| M-6.11 | **Export page (`/export`)** | Navigate to export | Config form works, PDF download triggers |
| M-6.12 | **Navigation** | Click all sidebar links | All 6 pages load without errors, active link highlighted |
| M-6.13 | **Responsive** | Resize to 1024px width | Layout remains usable, no horizontal overflow |
| M-6.14 | **No console errors** | Open DevTools console | Zero red errors on any page |
| M-6.15 | **Loading states** | Throttle network in DevTools | Loading spinners/skeletons show during API fetches |
| M-6.16 | **Empty state** | Remove `data/analyzed/` files, refresh | Graceful "no data" messages instead of crashes |

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| `npm run build` exits with code 0 | Required |
| All 6 pages render without JavaScript errors | 100% |
| All charts render with correct data | 100% |
| All filters produce correct filtered results | 100% |
| PDF download completes successfully | Required |
| Responsive at 1024px+ | Required |
| Browser console errors (on any page) | 0 |
| Per-slice loading states work correctly | Required |

### Exit Gate Checklist

- [ ] All 6 pages render with live API data (Dashboard, Themes, Reviews, Segments, Chat, Export)
- [ ] Dashboard KPI cards show correct summary stats
- [ ] All chart components render with data and tooltips (donut, bar, treemap)
- [ ] Review browser filters work (source, theme, sentiment, segment, search, date)
- [ ] Review detail modal shows all 14 AI annotation fields
- [ ] Theme explorer treemap is clickable with drill-down
- [ ] Segment comparison shows side-by-side cards
- [ ] Chat page sends queries and displays responses with citations
- [ ] Export page triggers PDF download
- [ ] Sidebar navigation works for all routes with active state
- [ ] Zustand store manages per-slice loading and error states
- [ ] `npm run build` passes without errors
- [ ] No console errors on any page
- [ ] Responsive layout at 1024px+
- [ ] Empty states handled gracefully (no crashes on missing data)

---

## 10. Phase 7 — Export, Deployment & Polish

### Automated Tests

```bash
# 1. PDF quality check
python -c "
from reportlab.lib.pagesizes import letter
print('ReportLab import: OK')
# Verify PDF generation doesn't crash with edge cases
# Test with minimal data, maximal data, empty sections
"

# 2. Backend tests
cd backend
pytest tests/ -v
echo "Test suite exit code: $?"

# 3. Docker Compose (if applicable)
docker-compose up -d
sleep 10
curl -sf http://localhost:8000/api/summary && echo "OK: Docker backend" || echo "FAIL"
curl -sf http://localhost:5173 && echo "OK: Docker frontend" || echo "FAIL"
docker-compose down
```

### Deployment Verification

| # | Check | How to Verify |
|---|---|---|
| D-7.1 | Backend accessible on Render | `curl https://<app>.onrender.com/api/summary` returns JSON |
| D-7.2 | Ollama running on Render (or Groq configured) | `POST /api/analyze` doesn't fail with connection refused |
| D-7.3 | Persistent disk working | Deploy, scrape data, redeploy — data still present |
| D-7.4 | Frontend on Vercel | `https://<app>.vercel.app` loads dashboard |
| D-7.5 | Frontend → Backend connection | Dashboard shows data from Render backend (no CORS errors) |
| D-7.6 | CI/CD pipeline | Push commit to `main`, verify GitHub Action runs and deploys |

### End-to-End Smoke Test

Run the full pipeline on deployment:

```bash
# 1. Scrape (small)
curl -X POST https://<render-url>/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"sources": ["play_store"], "limits": {"play_store": 20}}'

# 2. Wait for scrape to complete (poll job_id)
# 3. Trigger analysis
curl -X POST https://<render-url>/api/analyze

# 4. Wait for analysis to complete
# 5. Verify dashboard loads with new data on Vercel
# 6. Test chatbot with a sample query
curl -X POST https://<render-url>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top user frustrations?"}'

# 7. Download PDF report
curl -o report.pdf https://<render-url>/api/export/pdf
file report.pdf | grep "PDF"
```

### Acceptance Thresholds

| Metric | Threshold |
|---|---|
| Backend deployed and accessible via HTTPS | Required |
| Frontend deployed and accessible via HTTPS | Required |
| CORS works between Vercel frontend and Render backend | Required |
| Full E2E pipeline completes (scrape → analyze → view → chat → export) | Required |
| Backend test suite passes | ≥ 10 meaningful tests |
| PDF report has proper formatting (headers, tables, page numbers) | Required |
| Cold start recovery time (Render free tier) | < 60 seconds |
| `docker-compose up` starts both services locally | Required |
| CI/CD runs on push to main | Required |

### Exit Gate Checklist

- [ ] Backend deployed and accessible on Render via HTTPS
- [ ] Ollama sidecar running on Render, or Groq API configured and responding
- [ ] Persistent disk retains data between redeploys
- [ ] Frontend deployed and accessible on Vercel via HTTPS
- [ ] Frontend communicates with backend without CORS errors
- [ ] GitHub Actions CI runs on push to main (tests + deploy)
- [ ] `docker-compose.yml` starts both services locally
- [ ] PDF report has polished formatting (headers, page breaks, tables, quotes)
- [ ] Backend test suite passes (≥ 10 meaningful tests covering preprocessor, aggregator, routers)
- [ ] End-to-end smoke test completes: scrape → preprocess → annotate → aggregate → serve → chat → export
- [ ] README documentation matches actual implementation
- [ ] All environment variables documented in `.env.example`

---

*This evaluation document should be used alongside [implementation_plan.md](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/implementation_plan.md) and [edge_cases.md](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/edge_cases.md) during development. Complete each phase's exit gate before moving on.*

---
**Owner:** Growth Engineering · **Status:** Living Document
