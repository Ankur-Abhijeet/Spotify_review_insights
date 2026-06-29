# ⚠️ Edge Cases & Failure Recovery Guide

This document catalogs critical edge cases, failure scenarios, and recovery plans for the Spotify Feedback Intelligence Platform. Each entry is organized by phase and details the **failure mode**, its **impact**, and the **mitigation/remediation strategy**.

---

## Table of Contents

1. [Phase 0 — Project Scaffolding & Environment](#phase-0--project-scaffolding--environment)
2. [Phase 1 — Data Collection (Scrapers)](#phase-1--data-collection-scrapers)
3. [Phase 2 — Preprocessing & Normalization](#phase-2--preprocessing--normalization)
4. [Phase 3 — AI Analysis & Annotation](#phase-3--ai-analysis--annotation)
5. [Phase 4 — Aggregation & Insight Generation](#phase-4--aggregation--insight-generation)
6. [Phase 5 — Backend API Layer](#phase-5--backend-api-layer)
7. [Phase 8 — RAG Chatbot Integration](#phase-8--rag-chatbot-integration)
8. [Phase 6 — Frontend Dashboard](#phase-6--frontend-dashboard)
9. [Phase 7 — Export, Deployment & Polish](#phase-7--export-deployment--polish)

---

## Phase 0 — Project Scaffolding & Environment

### E-0.1: Ollama Model Missing or Service Offline
- **Scenario**: The backend starts, but the Ollama server is not running, or the model `llama3.1:8b` or `nomic-embed-text` has not been pulled.
- **Impact**: **Blocker** — Annotation (Phase 3), RAG ingestion (Phase 8), and chat synthesis features will fail immediately with connection or model-not-found errors.
- **Mitigation**:
  - Implement a health check on backend startup (`backend/main.py`) that queries `GET http://localhost:11434/api/tags`.
  - Log a clear error message: *"Ollama is offline or model is missing. Run `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`."*
  - Automatically cascade to heuristic mock annotation if Ollama is unreachable.

### E-0.2: Playwright Chromium Binaries Not Installed
- **Scenario**: System is deployed or run in a new environment, but `playwright install chromium` was not executed.
- **Impact**: **Blocker** — Scrapers will crash on startup when launching the browser.
- **Mitigation**:
  - Include an automated installation check or run `playwright install chromium` inside the build/start script.
  - Add a pre-flight check in `BaseScraper.__init__()` that verifies Chromium availability before launching.

### E-0.3: Hosting Out-of-Memory (OOM) due to Local LLM
- **Scenario**: Running backend APIs, scrapers, and Ollama simultaneously on a memory-constrained host (e.g., Render 512MB or 2GB tier).
- **Impact**: **High** — Container gets forcefully killed by OS scheduler.
- **Mitigation**:
  - Configure Ollama's active RAM footprint (e.g., set `OLLAMA_NUM_PARALLEL=1` and lower GPU context size if needed).
  - Offload LLM inference to Groq Cloud in production, reserving Ollama strictly for local development.

### E-0.4: Python/Node Version Incompatibility
- **Scenario**: Developer uses Python < 3.10 or Node < 18, causing syntax or package compatibility errors.
- **Impact**: **Blocker** — Project fails to install or start.
- **Mitigation**:
  - Document exact version requirements in README. Add a runtime version check in `config.py` startup.
  - Enforce via `.python-version` and `.nvmrc` files.

### E-0.5: Missing `.env` File or Unset Variables
- **Scenario**: Developer clones the repo but does not copy `.env.example` to `.env`, causing `pydantic-settings` to use defaults or fail.
- **Impact**: **Medium** — Silent misconfiguration (e.g., wrong `DATA_DIR`, missing `GROQ_API_KEY`).
- **Mitigation**:
  - Pydantic Settings should have sensible defaults for all non-secret variables.
  - Log a startup warning if `.env` file is not found: *"No .env file detected. Using defaults."*

---

## Phase 1 — Data Collection (Scrapers)

### E-1.1: CSS Selectors Outdated (Target Site Redesign)
- **Scenario**: A target platform (especially Reddit or Spotify Community) rolls out a UI update, changing class names and element hierarchies.
- **Impact**: **High** — Scrapers run successfully but return 0 reviews.
- **Mitigation**:
  - Validate selector health on every run: if a page loads but 0 elements are matched, log a `WARNING: Potential DOM change detected` and fail early.
  - Use data-attribute selectors over class-name selectors where possible.

### E-1.2: CAPTCHA Wall or IP Block Triggered
- **Scenario**: Aggressive scraping or missing delays cause the target host to block the IP or display a CAPTCHA.
- **Impact**: **High** — Collection stops completely for that source.
- **Mitigation**:
  - Use `playwright-stealth` plugin to pass browser fingerprint checks.
  - Implement dynamic delays (`_random_delay(500, 2000)`) and switch to sequential scraping (never run 4 scrapers concurrently on the same IP).
  - Integrate proxies if scraping high volumes.

### E-1.3: Infinite Scroll Hangs / Fails
- **Scenario**: Play Store scroll panel fails to load new reviews due to slow network or scroll container focus issues.
- **Impact**: **Medium** — Scraper gets stuck in an infinite loop or returns far fewer reviews than the limit.
- **Mitigation**:
  - Add a maximum scroll counter/timeout (e.g., stop after 5 consecutive scrolls that yield 0 new elements).
  - Implement a global timeout per scraper run (e.g., 120 seconds max).

### E-1.4: iTunes RSS API Pagination Limit
- **Scenario**: Apple App Store RSS feed caps at 500 reviews total (50/page × 10 pages). User requests `--limit 1000`.
- **Impact**: **Low** — Scraper returns fewer results than requested without explanation.
- **Mitigation**:
  - Log a warning when the hard API ceiling is reached: *"App Store RSS API limit reached (max 500). Returning available reviews."*
  - Document the limitation in scraper docstrings.

### E-1.5: PullPush Reddit API Downtime
- **Scenario**: The PullPush Search API (used for Reddit scraping) is temporarily unavailable or returns 5xx errors.
- **Impact**: **Medium** — Reddit source returns 0 results for the run.
- **Mitigation**:
  - Implement `_retry_with_backoff()` with 3 retries and exponential delay.
  - Fall back to old.reddit.com HTML scraping if the API is consistently down.
  - Isolate source failures so other scrapers continue.

### E-1.6: Spotify Community RSS Feed Structure Change
- **Scenario**: Spotify updates their Community forum platform, changing the RSS XML schema or disabling the feed entirely.
- **Impact**: **Medium** — Community scraper crashes or returns malformed data.
- **Mitigation**:
  - Wrap XML parsing in `try-except` blocks with schema validation.
  - Fallback to HTML scraping of the community boards if RSS is unavailable.

### E-1.7: Encoding Issues in Scraped Content
- **Scenario**: Reviews contain non-UTF-8 characters, mixed encodings, or invalid byte sequences from different platform locales.
- **Impact**: **Low** — JSON serialization fails or produces garbled text.
- **Mitigation**:
  - Force UTF-8 encoding on all text extraction: `text.encode('utf-8', errors='replace').decode('utf-8')`.
  - Normalize Unicode characters using `unicodedata.normalize('NFC', text)`.

### E-1.8: `google-play-scraper` Package Breaking Changes
- **Scenario**: The `google-play-scraper` Python package updates its API, changing return field names or requiring new parameters.
- **Impact**: **Medium** — Play Store scraper silently produces records with missing fields.
- **Mitigation**:
  - Pin the package version in `requirements.txt` (e.g., `google-play-scraper==1.2.7`).
  - Validate output fields immediately after scraping, before persisting to disk.

---

## Phase 2 — Preprocessing & Normalization

### E-2.1: Corrupt JSON or Empty Raw Scraping Files
- **Scenario**: A scraper crashed or saved incomplete data, creating an empty or malformed JSON file in `data/raw/`.
- **Impact**: **Medium** — The merge script crashes while reading the file.
- **Mitigation**:
  - Wrap file reads in `try-except` blocks. If JSON parsing fails, move the corrupted file to `data/errors/` and log a diagnostic warning.
  - Validate that the parsed object is a non-empty list before processing.

### E-2.2: Extreme Characters or Non-English Fonts
- **Scenario**: Reviews containing heavy emoji strings, right-to-left fonts (Arabic, Hebrew), or corrupt byte sequences.
- **Impact**: **Low** — Regex functions or HTML-stripping scripts crash.
- **Mitigation**:
  - Force text encoding parsing to UTF-8 (`open(file, encoding='utf-8')`).
  - Strip control characters and normalize whitespace via regex before processing.
  - The non-English language filter (Track 1) should catch RTL scripts.

### E-2.3: Overly Aggressive Deduplication
- **Scenario**: Two users write the same brief phrase (e.g., *"Still loops recommendations"*). Jaccard dedup with low threshold labels them as duplicates.
- **Impact**: **Medium** — Valid review signals are lost, reducing dataset diversity.
- **Mitigation**:
  - Apply Jaccard check *only* if the review body is longer than 50 characters.
  - Keep the duplicate threshold high (e.g., `≥ 0.85`).
  - Author-aware dedup: distinct non-anonymous authors bypass the check.

### E-2.4: Track 1/Track 2 Source Misclassification
- **Scenario**: A new data source is added but assigned to the wrong preprocessing track (e.g., a forum source routed through Track 1 individual review filters instead of Track 2 thread chunking).
- **Impact**: **High** — Entire source's data is inappropriately filtered (forum threads broken apart, or reviews unchunked).
- **Mitigation**:
  - Maintain an explicit source-to-track mapping dictionary in `preprocessor.py`.
  - Validate the mapping against the architecture document during code review.

### E-2.5: Keyword Density Filter Over-Filtering
- **Scenario**: Track 1 keyword density filter uses too narrow a term list, discarding relevant reviews about discovery that use non-standard vocabulary (e.g., *"I keep hearing the same artists"* instead of *"recommendation loop"*).
- **Impact**: **Medium** — Valid discovery-related reviews are excluded from the pipeline.
- **Mitigation**:
  - Use an expansive keyword list including synonyms and colloquial terms.
  - Log the discard rate: if > 70% of reviews are filtered, alert for term list review.
  - Include a configurable `--min-keyword-density` threshold flag.

### E-2.6: Date Parsing Failures Across Locales
- **Scenario**: Different sources return dates in incompatible formats (e.g., `Jun 22, 2026`, `2026-06-22T10:30:00Z`, `22/06/2026`, relative like `3 days ago`).
- **Impact**: **Medium** — Date normalization crashes or produces incorrect `YYYY-MM-DD` values.
- **Mitigation**:
  - Use `date_normalizer.py` with a multi-format parser cascade (try ISO-8601, then common locale formats, then relative-date resolution).
  - Default to `scraped_at` date if all parsing attempts fail.

### E-2.7: Thread Chunking Produces Oversized Blocks
- **Scenario**: A Reddit thread has 200+ replies, producing a single Track 2 chunk that exceeds the LLM context window in Phase 3.
- **Impact**: **High** — LLM truncates or refuses the input during annotation.
- **Mitigation**:
  - Impose a maximum chunk size (e.g., 3,000 characters). If a thread exceeds this, split into sequential overlapping chunks.
  - Preserve thread metadata (title, OP body) as a prefix for each sub-chunk.

---

## Phase 3 — AI Analysis & Annotation

### E-3.1: Context Window Overflow (Very Long Reviews)
- **Scenario**: A batch contains long Reddit posts or community threads that exceed the `llama3.1:8b` context window limit (8K tokens).
- **Impact**: **High** — LLM cuts off text or fails to output valid JSON.
- **Mitigation**:
  - Truncate input review texts to a maximum of 1,000 characters before sending them to the LLM.
  - Batch size of 20 reviews should be validated to stay within total token limits.

### E-3.2: Malformed JSON or Code-Block Wrap in LLM Output
- **Scenario**: The LLM outputs markdown syntax (e.g., ````json ... ````) or prepends conversational text before the JSON payload.
- **Impact**: **High** — `json.loads()` fails, skipping the entire batch of 20.
- **Mitigation**:
  - Write a robust parser that extracts text between the first `{` and last `}` character.
  - Implement a retry mechanism: if parsing fails, prompt the LLM again with a strict reminder to omit markdown code wrappers (up to 3 retries).

### E-3.3: Invalid Enum/Category Generation
- **Scenario**: LLM tags a review's sentiment as `extremely_negative` instead of `negative`, or invents a theme like `podcast_fatigue` not in the taxonomy.
- **Impact**: **Medium** — Metrics in the dashboard break or display inconsistent categories.
- **Mitigation**:
  - Validate LLM output values against defined taxonomies (enums) in `normalize_and_validate()`.
  - If validation fails, clamp to default values (e.g., `neutral` for sentiment, `unrelated` for primary_theme, `unknown` for user_segment).

### E-3.4: Groq API Rate Limit Exhaustion (429 Errors)
- **Scenario**: Free-tier Groq limits (30 RPM, 6K TPM) are exceeded during annotation of a large dataset.
- **Impact**: **High** — Annotation stalls for the remainder of the rate window.
- **Mitigation**:
  - Implement proactive TPM/RPM throttling via Groq response headers (`x-ratelimit-remaining-*`).
  - Sleep preemptively when remaining tokens < 4,500 or remaining requests < 2.
  - Track daily usage in `api_usage.json` and refuse to start new runs if the daily limit is near.

### E-3.5: Groq API Key Invalid or Revoked
- **Scenario**: The `GROQ_API_KEY` in `.env` is expired, revoked, or has a typo.
- **Impact**: **Medium** — All Groq requests return 401. System silently falls back to Ollama (or mock if Ollama is also down).
- **Mitigation**:
  - On first 401 response, log a clear error: *"Groq API key is invalid. Falling back to Ollama."*
  - Validate the API key on startup with a lightweight health check call.

### E-3.6: Batch Size Causes 413 / Payload Too Large
- **Scenario**: A batch of 20 reviews with unusually long bodies exceeds the LLM provider's request size limit.
- **Impact**: **High** — Entire batch fails with HTTP 413.
- **Mitigation**:
  - Implement automatic batch splitting: on 413 or TPM-limit errors, the batch is halved and retried recursively.
  - Pre-calculate approximate token count per batch before submission.

### E-3.7: Mock Annotation Mode Produces Low-Quality Data
- **Scenario**: Ollama is offline and no Groq key is set. System falls back to heuristic mock annotations which produce simplistic, keyword-based results.
- **Impact**: **Medium** — Dashboard insights are superficial and not representative of actual review content.
- **Mitigation**:
  - Clearly tag mock-annotated reviews in the output JSON (e.g., `"annotation_source": "mock"`).
  - Display a prominent banner in the frontend: *"⚠️ Running with mock annotations. Connect an LLM for accurate insights."*

### E-3.8: Stale Analyzed Data After Preprocessing Changes
- **Scenario**: User re-runs preprocessing (adding new reviews or changing filters) but does not re-run annotation. `reviews_analyzed.json` contains stale entries that no longer exist in `all_reviews.json`.
- **Impact**: **Medium** — Dashboard metrics reference deleted/changed reviews.
- **Mitigation**:
  - On annotation startup, prune stale entries: remove any review from `reviews_analyzed.json` whose `review_id` is not present in the current `all_reviews.json`.
  - Log the number of pruned stale entries.

---

## Phase 4 — Aggregation & Insight Generation

### E-4.1: Division by Zero on Empty Themes
- **Scenario**: A theme has 0 reviews tagged (perhaps due to a small scraper limit or aggressive filtering).
- **Impact**: **High** — Aggregator crashes during average sentiment or frequency ratio calculations.
- **Mitigation**:
  - Ensure denominator checks exist: `avg_sentiment = total_score / count if count > 0 else 0.0`.
  - Skip themes/segments/archetypes with zero frequency rather than including them with NaN values.

### E-4.2: Outlier Reviews Dominating Opportunity Scores
- **Scenario**: A niche unmet need receives a high sentiment score but only has 1 review, leading to a skewed opportunity score.
- **Impact**: **Medium** — The opportunity map ranks minor issues above critical themes.
- **Mitigation**:
  - Add a frequency floor to calculations (e.g., only calculate opportunity scores for unmet needs mentioned at least 3 times across the dataset).
  - Weight the opportunity score formula to penalize low-frequency items.

### E-4.3: Unmet Need Clustering Produces Too Many / Too Few Clusters
- **Scenario**: The `SequenceMatcher.ratio() ≥ 0.70` threshold either collapses distinct needs into one cluster or fails to group nearly identical phrasings.
- **Impact**: **Medium** — Dashboard shows either 200+ micro-needs (unusable) or 3 mega-clusters (uninformative).
- **Mitigation**:
  - Make the clustering threshold configurable.
  - If cluster count exceeds 50, auto-tighten the threshold; if fewer than 5, auto-loosen.
  - Log clustering statistics: total unique needs, cluster count, largest cluster size.

### E-4.4: Summary Statistics Drift from Analyzed Data
- **Scenario**: `summary.json` is generated from a stale `reviews_analyzed.json` that was later modified (e.g., by a retry run).
- **Impact**: **Medium** — Dashboard KPI cards show incorrect counts.
- **Mitigation**:
  - Always regenerate all 6 output files atomically in a single aggregation run.
  - Include a `generated_at` timestamp and `source_hash` in `summary.json` for staleness detection.

### E-4.5: Pain Score Amplification for Multi-Source Niche Themes
- **Scenario**: A theme appears once each in 4 different sources. Pain score formula (`frequency × avg_sentiment × source_count`) gives it a score of `4 × 0.8 × 4 = 12.8`, higher than a genuine pain point appearing 20 times in 2 sources (`20 × 0.6 × 2 = 24.0`). While this specific example works correctly, edge cases with small frequencies and many sources can produce misleading rankings.
- **Impact**: **Low** — Minor distortion in theme ranking.
- **Mitigation**:
  - Apply a minimum frequency floor (e.g., `frequency >= 5`) before including a theme in pain score rankings.
  - Consider using `log(source_count)` to dampen the multi-source multiplier.

---

## Phase 5 — Backend API Layer

### E-5.1: Large Dataset API Timeout
- **Scenario**: User requests `/api/reviews` without parameters, and the backend attempts to load and transmit a large JSON file (e.g., 50MB+) containing thousands of analyzed reviews.
- **Impact**: **High** — API times out; client browser tab hangs.
- **Mitigation**:
  - Enforce pagination natively: default `page=1` and `per_page=50`.
  - Cache aggregated statistics (e.g., `summary.json`, `themes.json`) in-memory at backend startup.
  - Set a maximum `per_page` ceiling (e.g., 200).

### E-5.2: PDF Layout Overlap on Long Strings
- **Scenario**: A user review containing a very long word without spaces (e.g., a URL or repeating string) causes the ReportLab PDF table column to stretch, clipping other text.
- **Impact**: **Medium** — Unprofessional PDF exports.
- **Mitigation**:
  - Implement a string wrapper/word-truncation helper inside the ReportLab builder to limit long strings within table cells.
  - Use `Paragraph` flowables instead of raw strings for text cells.

### E-5.3: Background Job Race Condition
- **Scenario**: User triggers `POST /api/scrape` twice in rapid succession, or triggers `POST /api/analyze` while a scrape is still writing to `data/raw/`.
- **Impact**: **High** — Data corruption from concurrent file writes, or analysis runs on incomplete data.
- **Mitigation**:
  - Implement a job mutex: reject new scrape/analyze requests if a job of the same type is already running.
  - Return HTTP 409 Conflict with a message: *"A scrape job is already in progress."*

### E-5.4: Stale In-Memory Data After Pipeline Re-Run
- **Scenario**: Backend caches `summary.json` and `themes.json` in memory at startup. User runs a new analysis pipeline that updates the files, but the API still serves stale cached data.
- **Impact**: **Medium** — Dashboard shows outdated metrics until server restart.
- **Mitigation**:
  - Implement file-modification-time checking: reload cached data if the file's `mtime` has changed since last load.
  - Or, invalidate caches at the end of a successful `POST /api/analyze` job.

### E-5.5: CORS Misconfiguration in Production
- **Scenario**: Frontend is deployed to `https://app.vercel.app` but backend CORS origins still set to `http://localhost:5173`. All frontend API requests are blocked by the browser.
- **Impact**: **Blocker** — Frontend shows no data; blank dashboard.
- **Mitigation**:
  - Use the `CORS_ORIGINS` environment variable and ensure it is updated in Render's env config.
  - Support comma-separated multiple origins for dual local+production access.

### E-5.6: Missing Aggregated Files on Fresh Deploy
- **Scenario**: Backend starts on a fresh deployment before any scraping or analysis has been run. API endpoints try to read `themes.json`, `summary.json`, etc., which don't exist yet.
- **Impact**: **High** — All GET endpoints return 500 Internal Server Error.
- **Mitigation**:
  - Handle `FileNotFoundError` gracefully in every router. Return empty arrays `[]` or empty objects `{}` with an appropriate message.
  - Set HTTP status to 200 with an `"empty": true` flag, not 404 or 500.

---

## Phase 8 — RAG Chatbot Integration

### E-8.1: SQLite / ChromaDB Database Lock
- **Scenario**: Ingestion script writes to the ChromaDB directory while the FastAPI backend is handling a `/api/chat` request.
- **Impact**: **High** — Server crashes with a database lock exception.
- **Mitigation**:
  - Configure database connection timeouts.
  - Implement a fallback retry mechanism in ChromaDB wrappers.
  - Do not allow ingestion while the API server is actively serving chat queries (or use separate ChromaDB instances with a swap-on-complete strategy).

### E-8.2: Retrieval Pollution (Irrelevant Semantic Matches)
- **Scenario**: User asks: *"Why does the loop fail?"*. Vector database retrieves reviews saying *"I love this loop"* (positive sentiment) along with actual bug reports about recommendation loops (negative sentiment).
- **Impact**: **Medium** — Chatbot outputs contradictory or overly optimistic answers.
- **Mitigation**:
  - Apply metadata pre-filters in the retriever (e.g., filter by sentiment or theme when context suggests a frustration query).
  - Filter out reviews with low cosine similarity (e.g., `similarity_score < 0.3`).
  - Retrieve more candidates (K=20) then re-rank by relevance before passing to synthesis.

### E-8.3: LLM Synthesizes Answers Without Citations
- **Scenario**: The LLM synthesizes an answer but fails to include bracketed source numbers (e.g., `[1]`) despite Prompt 3 instructions.
- **Impact**: **Medium** — Stakeholders cannot trace claims back to source reviews.
- **Mitigation**:
  - Use regex to verify citations exist in the output text.
  - If missing, append a summary list of the top 3 retrieved source titles manually to the end of the chatbot's answer.
  - Add explicit citation formatting examples in the system prompt.

### E-8.4: Memory 1 / Memory 2 Collection Size Imbalance
- **Scenario**: App Store + Play Store yield 400 reviews (Memory 1), but Reddit + Community yield only 20 threads (Memory 2). Retrieval is dominated by Memory 1 results.
- **Impact**: **Medium** — Chatbot answers skew toward short-form review perspectives, missing nuanced community discussion insights.
- **Mitigation**:
  - Retrieve top-K from each memory independently (e.g., K=15 each) rather than a combined K=30 across both.
  - Ensure the synthesis prompt instructs the LLM to consider both review and discussion perspectives.

### E-8.5: Embedding Model Mismatch Between Ingestion and Query
- **Scenario**: Reviews are ingested with `nomic-embed-text` v1, but Ollama auto-updates to v2 with different embedding dimensions or vector space.
- **Impact**: **High** — Similarity search returns nonsensical results or crashes with dimension mismatch errors.
- **Mitigation**:
  - Pin the embedding model version in `config.py`.
  - Store the model version used for ingestion as metadata in ChromaDB.
  - On query, verify the active model matches the ingested model; if not, prompt for re-ingestion.

### E-8.6: Empty Vector Store (No Ingestion Run)
- **Scenario**: User opens the chat page before running `ingest_reviews.py`. ChromaDB collections are empty.
- **Impact**: **High** — Chatbot returns generic answers with no citations, or crashes.
- **Mitigation**:
  - Check collection count on chat request. If 0, return a friendly message: *"No review data has been ingested yet. Please run the analysis pipeline first."*
  - Disable the chat input field in the frontend when the vector store is empty.

### E-8.7: Prompt 3 Context Window Overflow
- **Scenario**: Top-K retrieval (K=15 from each memory = 30 documents) plus the system prompt and user query exceeds the LLM's context window.
- **Impact**: **High** — LLM truncates retrieved context, producing incomplete or hallucinated answers.
- **Mitigation**:
  - Estimate total token count before calling the LLM. If it exceeds 80% of the context window, reduce K dynamically.
  - Truncate individual retrieved documents to a maximum of 500 characters each.

### E-8.8: Chatbot Hallucination (Fabricated Statistics)
- **Scenario**: LLM generates plausible-sounding statistics (e.g., *"73% of users report recommendation fatigue"*) that are not grounded in the retrieved context.
- **Impact**: **High** — Stakeholders make product decisions based on fabricated data.
- **Mitigation**:
  - Prompt 3 should explicitly instruct: *"Do not fabricate statistics. Only cite information present in the provided context."*
  - Include a confidence disclaimer in the chatbot UI: *"Responses are synthesized from user reviews and may not represent statistically significant trends."*

---

## Phase 6 — Frontend Dashboard

### E-6.1: Empty State UI Crash
- **Scenario**: The dashboard starts before the scrapers or pipeline have run, meaning `summary.json` and `themes.json` do not exist or are empty.
- **Impact**: **High** — Blank screen of death in React (unhandled null/undefined in chart components).
- **Mitigation**:
  - Verify API response states. If data is missing or empty, render user-friendly, descriptive empty state illustrations with a *"Run Pipeline"* helper button.
  - Use optional chaining and default values in all Zustand store selectors.

### E-6.2: Recharts Rendering Nulls
- **Scenario**: A trend chart receives a date array with missing intermediate dates, or a theme bar chart gets `null` frequency values.
- **Impact**: **Low** — Visual gaps or broken lines in the charts.
- **Mitigation**:
  - Fill date gaps in the API layer before transmitting, or configure Recharts to connect points with null values smoothly.
  - Provide default `0` values for missing metrics.

### E-6.3: Review Detail Modal Overflow
- **Scenario**: A review has an extremely long `body` text (1,000+ words) or an `unmet_need` field with a paragraph-length string, causing the modal to overflow the viewport.
- **Impact**: **Low** — Poor UX; content is clipped or not scrollable.
- **Mitigation**:
  - Add `max-height` and `overflow-y: auto` to the modal body.
  - Truncate long text fields with a "Show more" expand toggle.

### E-6.4: Concurrent Zustand State Mutations
- **Scenario**: User rapidly navigates between pages, triggering multiple concurrent `fetch*()` actions that update shared loading states.
- **Impact**: **Low** — Loading spinners flash inconsistently or a stale page's data overwrites the current page's data.
- **Mitigation**:
  - Use per-slice loading states (e.g., `summaryLoading`, `themesLoading`) instead of a single global `isLoading`.
  - Cancel pending Axios requests on page navigation using `AbortController`.

### E-6.5: Chat Page Message Ordering
- **Scenario**: User sends two rapid queries. The second query's response arrives before the first, causing messages to display out of order.
- **Impact**: **Medium** — Confusing chat UX; citations reference the wrong query.
- **Mitigation**:
  - Queue chat messages with sequential IDs. Display responses in order of their request, not their arrival.
  - Disable the input field while a query is in flight.

### E-6.6: Theme Explorer Treemap Overflow
- **Scenario**: 16+ themes all rendered as treemap tiles at once. On small screens, labels overlap and tiles become unreadable.
- **Impact**: **Low** — Poor data visualization UX.
- **Mitigation**:
  - Show only top 10 themes in the treemap by default. Provide a "Show all" toggle.
  - Use responsive font sizing based on tile area.

---

## Phase 7 — Export, Deployment & Polish

### E-7.1: SPA Routing Returns 404 on Refresh
- **Scenario**: Deployed React SPA URL `/#/themes` or `/themes` is refreshed in the browser, causing the hosting platform to return a 404 error.
- **Impact**: **High** — Broken navigation on page refreshes.
- **Mitigation**:
  - Use `HashRouter` (already specified in architecture) which avoids server-side routing issues.
  - If switching to `BrowserRouter`, add a redirect/rewrite rule (`vercel.json` rewrite config) directing all paths to `index.html`.

### E-7.2: Persistent Storage Wipe on Redeployment
- **Scenario**: Deployed container on Render restarts or redeploys, wiping the local `data/` folder.
- **Impact**: **High** — All historic scraped and analyzed reviews are lost.
- **Mitigation**:
  - Ensure Render persistent disk is configured and mounted at `/data`.
  - Point environment variable `DATA_DIR=/data` in Render console.

### E-7.3: Render Free Tier Cold Start Latency
- **Scenario**: Render free tier spins down the backend after 15 minutes of inactivity. First request after idle takes 30–60 seconds to respond.
- **Impact**: **Medium** — User sees a timeout error on the dashboard, thinks the system is broken.
- **Mitigation**:
  - Display a "Waking up server..." loading state in the frontend when the first API call takes > 5 seconds.
  - Implement a `/health` endpoint that the frontend pings first to warm up the server.

### E-7.4: GitHub Actions CI/CD Secrets Leak
- **Scenario**: GitHub Actions workflow inadvertently logs the `GROQ_API_KEY` or other secrets in build output.
- **Impact**: **Critical** — API key compromise.
- **Mitigation**:
  - Use GitHub Secrets for all sensitive values. Never echo env vars in CI scripts.
  - Mask secrets in workflow logs using `::add-mask::` syntax.

### E-7.5: Frontend Build Fails on Vercel Due to Dependency Mismatch
- **Scenario**: Local development uses Node 20 but Vercel defaults to Node 18, causing build failures in newer packages.
- **Impact**: **Medium** — Deployment blocked.
- **Mitigation**:
  - Specify Node version in `package.json` `engines` field and in Vercel project settings.
  - Pin all package versions exactly in `package-lock.json`.

### E-7.6: PDF Export Timeout on Large Datasets
- **Scenario**: `GET /api/export/pdf` takes > 30 seconds to generate a PDF for 1,000+ analyzed reviews with all sections enabled.
- **Impact**: **Medium** — Request times out; user gets no PDF.
- **Mitigation**:
  - Limit the number of sample reviews included in the PDF (e.g., top 50 per theme).
  - Pre-generate the PDF during the aggregation step and serve the cached file.
  - Increase the API timeout for export endpoints.

---

*This document should be referenced alongside [implementation_plan.md](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/implementation_plan.md) and [architecture.md](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/architecture.md) during development. Address edge cases proactively in each phase before marking exit gates as complete.*

---
**Owner:** Growth Engineering · **Status:** Living Document
