# 📌 Architecture & Design Decision Log (ADR)

This document records all significant architecture, design, and implementation decisions made for the Spotify Feedback Intelligence Platform. Each entry follows a lightweight Architecture Decision Record (ADR) format with **context**, **decision**, **rationale**, and **consequences**.

> [!TIP]
> When revisiting or changing a past decision, do not delete the original entry. Instead, mark it as **Superseded** and add a new entry referencing the original.

---

## Table of Contents

1. [Data Architecture](#data-architecture)
2. [Scraping & Data Collection](#scraping--data-collection)
3. [Preprocessing Pipeline](#preprocessing-pipeline)
4. [AI / LLM Strategy](#ai--llm-strategy)
5. [RAG & Chatbot](#rag--chatbot)
6. [Backend & API](#backend--api)
7. [Frontend & UX](#frontend--ux)
8. [Deployment & Infrastructure](#deployment--infrastructure)
9. [Decision Template](#decision-template)

---

## Data Architecture

### ADR-001: Zero-Database, JSON Filesystem Design
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The platform needs to persist scraped, preprocessed, analyzed, and aggregated data. Options considered: PostgreSQL, SQLite, MongoDB, or flat JSON files.
- **Decision:** Use local JSON files as the sole persistence layer. No traditional database.
- **Rationale:**
  - Eliminates database setup complexity and migration overhead.
  - All pipeline stages produce and consume JSON naturally (scrapers → preprocessor → annotator → aggregator).
  - Pre-computed aggregated JSON files serve as the API read layer with O(1) reads and zero query computation on request.
  - Aligns with the "ephemeral processing" design principle — no PII stored persistently.
- **Consequences:**
  - No relational queries, joins, or transactions. Complex filtering done in-memory.
  - Pagination and filtering on `/api/reviews` operates on in-memory list, which scales poorly past ~50K reviews.
  - No concurrent write safety — addressed via job mutex (see ADR-016).

---

### ADR-002: Dual-Track Preprocessing Pipeline
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Raw feedback comes in two structurally different formats: short star-rated individual reviews (App Store, Play Store) and long conversational discussion threads (Reddit, Spotify Community). Applying the same preprocessing to both produces poor results.
- **Decision:** Split preprocessing into two parallel tracks:
  - **Track 1** (App Store & Play Store): Clean metadata → remove duplicates → remove emoji-only → remove <20 chars → remove non-English → keyword density filter → text chunking.
  - **Track 2** (Reddit & Spotify Community): Chunk each thread as a single cohesive block preserving context and replies.
- **Rationale:**
  - Individual reviews are atomic and need aggressive noise filtering.
  - Forum threads contain back-and-forth context, community consensus signals (upvotes), and replies that lose meaning if split into individual sentences.
  - Preserving thread-level context improves LLM annotation quality for discussion sources.
- **Consequences:**
  - Preprocessor must maintain an explicit source-to-track mapping.
  - Downstream stages (annotation, RAG) must handle both data shapes.
  - Track 2 chunks can be large — requires max chunk size limits (see [edge_cases.md E-2.7](file:///Users/ankurabhijeet/Documents/nextleap/projects/Spotify_review_scraper/docs/edge_cases.md)).

---

### ADR-003: Six Core Research Questions as System Foundation
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The platform needs a clear analytical framework to guide all data collection, annotation, and insight generation.
- **Decision:** Architect the entire system around six product research questions:
  1. Why do users struggle to discover new music? (Barrier classification)
  2. What are the most common recommendation frustrations? (Theme extraction)
  3. What listening behaviours are users trying to achieve? (Intent archetypes)
  4. What causes users to repeatedly listen to the same content? (Repetition triggers)
  5. Which user segments experience different challenges? (Segment profiling)
  6. What unmet needs emerge consistently? (Need clustering & ranking)
- **Rationale:**
  - Provides a testable, product-focused analytical framework.
  - Each question maps directly to a pipeline output and dashboard view.
  - Keeps scope focused on music discovery insights rather than general sentiment analysis.
- **Consequences:**
  - All 14 AI annotation fields are designed to answer these specific questions.
  - Adding a new research question requires extending the prompt, enum taxonomy, aggregator, and frontend.

---

## Scraping & Data Collection

### ADR-004: Four Data Sources (No Twitter/X)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The Problem Statement originally listed 5 sources including Twitter/X. Twitter's API pricing under X Corp makes free-tier access unreliable.
- **Decision:** Launch with 4 sources: Apple App Store, Google Play Store, Reddit, and Spotify Community. Defer Twitter/X.
- **Rationale:**
  - App Store and Play Store provide high-volume, structured star-rated feedback.
  - Reddit provides deep, nuanced power-user discussions.
  - Spotify Community captures explicit feature requests and bug reports.
  - Twitter/X API free tier is too restrictive for meaningful collection volume.
- **Consequences:**
  - Architecture remains extensible — new scrapers inherit from `BaseScraper`.
  - Social media signal (brief, high-volume sentiment) is not captured in v1.

---

### ADR-005: PullPush API Over Official Reddit API
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Reddit's official API requires OAuth and has restrictive rate limits. PullPush provides a search-based API for public Reddit data.
- **Decision:** Use PullPush Search API for Reddit scraping with 5 intent-based search queries targeting r/spotify.
- **Rationale:**
  - No authentication required — aligns with zero-auth design principle.
  - Search-based queries allow targeted discovery-related content retrieval.
  - Avoids Reddit API rate limit complications.
- **Consequences:**
  - PullPush may have downtime or lag — fallback to old.reddit.com HTML scraping needed.
  - Content is limited to what PullPush indexes (may miss very recent posts).

---

### ADR-006: `google-play-scraper` Package Over Playwright for Play Store
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Play Store reviews could be scraped via Playwright browser automation or the `google-play-scraper` Python package.
- **Decision:** Use `google-play-scraper` package wrapped in `asyncio.to_thread()`.
- **Rationale:**
  - Native Python package is faster, more reliable, and less fragile than DOM scraping.
  - Avoids Playwright overhead (browser launch, memory) for a source that has a package-based alternative.
  - `asyncio.to_thread()` bridges the sync package into the async scraper architecture.
- **Consequences:**
  - Dependency on a third-party package — must pin version and monitor for breaking changes.
  - Less control over pagination and request timing compared to direct browser automation.

---

### ADR-007: iTunes RSS JSON API for App Store (Not Scraping)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** App Store reviews can be accessed via the public iTunes RSS JSON feed or via browser automation of the App Store web page.
- **Decision:** Use the iTunes RSS JSON API via `httpx` GET requests, paginated at 50/page with max 10 pages (500 reviews ceiling).
- **Rationale:**
  - RSS feed is a stable, public Apple-provided endpoint.
  - No browser automation required — faster, lighter, and less detectable.
  - Returns structured JSON directly.
- **Consequences:**
  - Hard ceiling of 500 reviews per scrape run (Apple API limitation).
  - No ability to filter by date range at the API level — must filter post-fetch.

---

## Preprocessing Pipeline

### ADR-008: Two-Pass Jaccard Deduplication Strategy
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Raw scrapes contain exact duplicates (same user re-posts) and near-duplicates (slightly different wording of the same complaint).
- **Decision:** Implement two-pass deduplication:
  - **Pass 1:** Exact structural match (Jaccard = 1.0) on tokenized first 25 characters. Keep review with highest engagement score.
  - **Pass 2:** Near-duplicate detection (Jaccard > 0.85) on reviews with body > 50 characters. Skip if length ratio > 2×. Author-aware bypass for distinct non-anonymous authors.
- **Rationale:**
  - Pass 1 catches bot spam and re-posted reviews cheaply.
  - Pass 2 catches organic paraphrasing without being overly aggressive.
  - 50-character minimum prevents short common phrases from being falsely flagged.
  - 0.85 threshold is conservative enough to avoid losing valid signals.
- **Consequences:**
  - Dedup is O(n²) on the second pass — acceptable for datasets < 10K reviews but will need optimization for larger volumes.
  - The 25-character prefix in Pass 1 may miss duplicates with different openings.

---

### ADR-009: 20-Character Minimum Body Length Filter
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Many App Store and Play Store reviews are extremely short (e.g., "Great app", "Trash", "👍👍👍") and carry no actionable discovery insight.
- **Decision:** Discard Track 1 reviews with cleaned body length < 20 characters.
- **Rationale:**
  - Reviews under 20 characters rarely contain enough context for meaningful LLM annotation.
  - Reduces LLM token costs by eliminating low-signal inputs.
  - 20 characters is approximately 3–5 words — the minimum for expressing a discovery-related opinion.
- **Consequences:**
  - Some genuinely concise feedback may be lost (e.g., "Fix Discover Weekly").
  - Threshold is configurable via `--min-body-len` CLI flag for tuning.

---

## AI / LLM Strategy

### ADR-010: Three-Prompt Internal System (Annotate, Partition, Synthesize)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The platform requires LLM capabilities at three distinct stages: review annotation, RAG memory creation, and chatbot synthesis.
- **Decision:** Design three internal prompts:
  - **Prompt 1 (Annotation):** System prompt instructing the LLM to answer the 6 research questions by extracting 14 structured fields per review.
  - **Prompt 2 (RAG Partitioning):** Guides the system to create two RAG memory collections from the two preprocessing tracks.
  - **Prompt 3 (Synthesis):** Chatbot prompt that combines retrieved contexts from both memories with the user query to produce cited answers.
- **Rationale:**
  - Separating concerns allows each prompt to be optimized independently.
  - Prompt 1 focuses on structured extraction (JSON mode).
  - Prompt 3 focuses on natural language synthesis with citation.
  - Prompt 2 is architectural guidance, not a literal LLM prompt.
- **Consequences:**
  - Three distinct prompt-engineering surfaces to maintain and tune.
  - Changes to the theme taxonomy in Prompt 1 cascade to aggregation, API, and frontend.

---

### ADR-011: Groq → Ollama → Mock Provider Fallback Cascade
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The system needs LLM inference but should work without internet access and without any cloud API keys.
- **Decision:** Implement a three-tier provider cascade:
  1. **Groq Cloud** (if `GROQ_API_KEY` is set): Low-latency cloud inference with `llama-3.1-8b-instant`.
  2. **Ollama Local** (if reachable at `OLLAMA_BASE_URL`): Self-hosted inference with `llama3.1:8b`.
  3. **Heuristic Mock** (fallback): Keyword-based annotation using pattern matching.
- **Rationale:**
  - Groq provides the fastest and highest-quality inference for production use.
  - Ollama enables fully offline development without API costs.
  - Mock ensures the system never crashes due to LLM unavailability — pipeline always completes.
- **Consequences:**
  - Mock annotations are significantly lower quality — must be clearly tagged.
  - Frontend should warn users when operating in mock mode.
  - Three code paths to maintain and test.

---

### ADR-012: Batch Size of 20 Reviews per LLM Call
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** LLM annotation can process reviews individually or in batches. Batch processing reduces API calls but increases per-request token count and failure blast radius.
- **Decision:** Default batch size of 20 reviews, configurable via `LLM_BATCH_SIZE` environment variable.
- **Rationale:**
  - 20 reviews × ~100 tokens each ≈ 2,000 input tokens + structured output ≈ 4,000 total tokens. Well within the 8K context window.
  - Reduces total API calls by 20× compared to individual processing.
  - Batch-level error recovery: if 1 review in the batch causes issues, only 20 reviews are retried, not the entire dataset.
- **Consequences:**
  - If a batch fails, 20 reviews must be retried together.
  - Very long reviews (>500 tokens) in a batch can cause context overflow — addressed by automatic batch splitting on 413 errors.

---

### ADR-013: 16-Value Theme Taxonomy (Fixed, Not Dynamic)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The LLM needs a constrained set of theme labels to produce consistent, aggregatable annotations.
- **Decision:** Define a fixed 16-value `primary_theme` enum: `discovery_friction`, `algorithm_repetition`, `recommendation_quality`, `discover_weekly_specific`, `radio_quality`, `made_for_you_feedback`, `genre_exploration`, `mood_based_listening`, `social_discovery`, `cross_platform_discovery`, `concert_live_discovery`, `podcast_discovery`, `algorithm_history_lock`, `feature_request`, `positive_discovery`, `unrelated`.
- **Rationale:**
  - Fixed enums enable reliable aggregation, charting, and comparison.
  - 16 themes balance granularity (specific enough to be actionable) with manageability (not overwhelming in the dashboard).
  - `unrelated` acts as a catch-all for non-discovery reviews.
- **Consequences:**
  - New discovery patterns may not fit existing categories — requires taxonomy updates.
  - Taxonomy changes cascade across: prompt, validation, aggregation, API models, and frontend charts.
  - The Problem Statement mentions the taxonomy should be "editable in the web app UI" — this is deferred to a future version.

---

### ADR-014: Incremental Annotation with Checkpoint Resume
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** LLM annotation of hundreds of reviews can take 30–60 minutes. Crashes mid-run would lose all progress.
- **Decision:** Append each successfully annotated batch to `reviews_analyzed.json` immediately. On startup, load existing annotated `review_id`s and skip them.
- **Rationale:**
  - Provides crash resilience — a 50% complete annotation run can resume without re-processing.
  - Reduces LLM API costs on re-runs.
  - Simple to implement: just check `review_id` membership in a set.
- **Consequences:**
  - `reviews_analyzed.json` grows incrementally and may contain entries from different annotation runs with potentially different prompt versions.
  - Stale entries (from deleted/changed preprocessed reviews) require pruning on next run.

---

## RAG & Chatbot

### ADR-015: Dual ChromaDB Collections (Memory 1 & Memory 2)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The RAG subsystem needs to store and retrieve review context. Options: single collection with source metadata filtering, or separate collections per data type.
- **Decision:** Create two ChromaDB collections:
  - **Memory 1 (`memory_1_reviews`):** App Store and Play Store individual reviews.
  - **Memory 2 (`memory_2_threads`):** Reddit and Spotify Community discussion threads.
- **Rationale:**
  - Mirrors the dual-track preprocessing architecture (ADR-002).
  - Ensures balanced retrieval from both short reviews and long discussions.
  - Querying both independently with K=15 each prevents one source type from dominating.
  - Different citation formatting per memory (e.g., `[Review #1]` vs `[Discussion #3]`).
- **Consequences:**
  - Ingestion script must route documents to the correct collection.
  - Retriever queries both collections in parallel — slightly more complex than single-collection queries.
  - Memory imbalance possible if one track has far fewer documents.

---

### ADR-016: `nomic-embed-text` for Embeddings (768-dim)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** ChromaDB requires an embedding model to vectorize review text for similarity search.
- **Decision:** Use `nomic-embed-text` via Ollama for embedding generation (768-dimensional vectors). Fall back to deterministic mock embeddings (MD5 hash + XOR expansion) if Ollama is unreachable.
- **Rationale:**
  - `nomic-embed-text` is free, runs locally via Ollama, and produces high-quality semantic embeddings.
  - 768 dimensions provide a good balance of expressiveness and storage efficiency.
  - Mock embeddings ensure the system remains functional (with degraded search quality) without external dependencies.
- **Consequences:**
  - Embedding model version must be pinned — model updates can change the vector space, breaking similarity search.
  - Mock embeddings produce poor retrieval quality — acceptable only for development/testing.

---

## Backend & API

### ADR-017: Background Subprocess Job System (Not Celery/Redis)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Scraping and analysis operations are long-running (minutes to hours). They cannot block the API server. Options: Celery + Redis, Python multiprocessing, or subprocess + threading.
- **Decision:** Execute scrape and analysis operations as `subprocess.Popen` calls in background threads. Track jobs in an in-memory dictionary protected by `threading.Lock`.
- **Rationale:**
  - Zero additional infrastructure (no Redis, no message broker).
  - Subprocess isolation: scraper/analysis crashes don't affect the API server.
  - Live log streaming: stdout is captured line-by-line for real-time progress via `/scrape/{job_id}`.
  - Sufficient for a single-server deployment.
- **Consequences:**
  - Jobs are lost on server restart (in-memory tracking only).
  - No distributed job execution — single server only.
  - Log retention capped at 100 lines per job to manage memory.

---

### ADR-018: Job Mutex — One Job Per Type at a Time
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Concurrent scrape or analysis jobs could cause data corruption from simultaneous file writes.
- **Decision:** Reject new `POST /api/scrape` or `POST /api/analyze` requests if a job of the same type is already running. Return HTTP 409 Conflict.
- **Rationale:**
  - Prevents race conditions on `data/raw/`, `data/preprocessed/`, and `data/analyzed/` files.
  - Simple to implement without distributed locking.
  - Users can poll job status and retry after completion.
- **Consequences:**
  - Users cannot run multiple scrape sources in parallel via the API (CLI still supports this).
  - Must clearly communicate job status in the frontend.

---

### ADR-019: Pre-Computed JSON Read Layer (No Query-Time Computation)
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** API endpoints could compute aggregations on-the-fly from raw data, or serve pre-computed results.
- **Decision:** All aggregated API responses (`/summary`, `/themes`, `/behaviors`, `/segments`, `/unmet-needs`) read from pre-computed JSON files generated during Phase 4 aggregation.
- **Rationale:**
  - O(1) response time regardless of dataset size.
  - Aggregation logic runs once per pipeline execution, not per API request.
  - Simplifies API router code to pure file I/O + optional filtering.
- **Consequences:**
  - Data is only as fresh as the last aggregation run.
  - Adding new metrics requires updating the aggregator, not just the API.
  - Cache invalidation managed via file `mtime` checking or post-job cache busting.

---

## Frontend & UX

### ADR-020: HashRouter Over BrowserRouter
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** React Router supports `BrowserRouter` (clean URLs) and `HashRouter` (hash-based URLs). Static hosting platforms (Vercel, GitHub Pages) handle them differently on page refresh.
- **Decision:** Use `HashRouter` for client-side routing (URLs like `/#/themes`, `/#/reviews`).
- **Rationale:**
  - Hash-based routing works on all static hosting without server-side rewrite rules.
  - Eliminates the 404-on-refresh problem entirely.
  - Simpler deployment configuration.
- **Consequences:**
  - URLs contain `#` prefix — less "clean" than `/themes`.
  - SEO impact is negligible since this is an internal tool, not a public website.

---

### ADR-021: Zustand Over Redux for State Management
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The frontend needs global state management for API data, loading states, filters, and job status.
- **Decision:** Use Zustand 4 with a single `useAppStore` containing per-slice state and async actions.
- **Rationale:**
  - Zustand has minimal boilerplate compared to Redux Toolkit.
  - Single store with named slices keeps state organized without the complexity of Redux middleware.
  - Built-in support for async actions (no thunks or sagas needed).
  - Lightweight bundle size.
- **Consequences:**
  - Less structured than Redux — requires discipline to maintain slice boundaries.
  - DevTools support is available but less mature than Redux DevTools.

---

### ADR-022: Dark Mode Slate/Emerald Design System
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The dashboard needs a professional, data-focused visual identity.
- **Decision:** Dark mode with slate-950 base, emerald-950 accent surfaces, and Spotify green (#1DB954) for highlights and interactive elements.
- **Rationale:**
  - Dark mode reduces eye strain for analytics dashboards used in extended sessions.
  - Slate/emerald palette evokes the Spotify brand without directly copying it.
  - High contrast between data elements and background improves chart readability.
- **Consequences:**
  - No light mode variant in v1.
  - All chart colors must be chosen for visibility against dark backgrounds.

---

### ADR-023: Tailwind CSS 4 for Styling
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The frontend needs a styling approach. Options: vanilla CSS, CSS Modules, styled-components, or Tailwind CSS.
- **Decision:** Use Tailwind CSS 4 with `@tailwindcss/vite` plugin.
- **Rationale:**
  - Utility-first approach enables rapid UI development.
  - Dark mode support is built-in.
  - Consistent spacing, typography, and color scales via design tokens.
  - Strong ecosystem compatibility with React.
- **Consequences:**
  - HTML contains many utility classes — can be verbose.
  - Custom components need careful abstraction to avoid class duplication.

---

## Deployment & Infrastructure

### ADR-024: Render (Backend) + Vercel (Frontend) Split Deployment
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** The system has a Python backend (FastAPI + Ollama) and a React frontend. These have different hosting requirements.
- **Decision:** Deploy backend to Render (with persistent disk for data) and frontend to Vercel (static SPA hosting).
- **Rationale:**
  - Render supports Python web services with persistent disks — essential for JSON data storage.
  - Render can run Ollama as a sidecar service for local LLM inference.
  - Vercel provides zero-config React static site hosting with automatic HTTPS.
  - Split deployment allows independent scaling and deployment of frontend vs backend.
- **Consequences:**
  - CORS must be configured to allow cross-origin requests between Vercel and Render domains.
  - Render free tier has cold start latency (30–60 seconds) after inactivity.
  - Persistent disk must be explicitly configured to survive redeploys.

---

### ADR-025: Groq Cloud as Default Production LLM Provider
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** In production (Render), running Ollama requires significant memory (4–8 GB for `llama3.1:8b`), which conflicts with free/low-tier hosting constraints.
- **Decision:** Use Groq Cloud (`llama-3.1-8b-instant`) as the default LLM provider in production. Reserve Ollama for local development only.
- **Rationale:**
  - Groq provides fast inference with no local memory overhead.
  - Free tier offers sufficient capacity for moderate analysis workloads (30 RPM, 6K TPM).
  - Same model family (`llama-3.1-8b`) ensures consistent annotation quality between dev and prod.
- **Consequences:**
  - Production deployment requires a valid `GROQ_API_KEY` for full functionality.
  - Free-tier rate limits constrain annotation throughput — large datasets may require overnight processing.
  - API key must be managed securely via environment variables.

---

### ADR-026: Nested Theme Extraction Schema
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Long-form reviews (like Reddit threads) often contain multiple distinct themes with differing sentiments and barriers. A flat schema forces the LLM to choose a single global primary theme and sentiment, resulting in lost nuance.
- **Decision:** Change the AI annotation schema to a nested structure. Review-level fields (user segment, discovery related) remain global, but theme-level fields (sentiment, barrier type, unmet need, etc.) are extracted for **each** distinct theme in a `themes` array.
- **Rationale:**
  - Accurately captures mixed-sentiment reviews (e.g., positive about UI, negative about algorithm).
  - Maximizes insight extraction from dense discussion threads.
  - Eliminates the subjective "primary vs secondary" ranking by capturing all themes with equal fidelity.
- **Consequences:**
  - The Prompt 1 output schema becomes more complex (nested JSON arrays).
  - Aggregation logic must iterate over the `themes` array instead of the top-level review.
  - The frontend Review Browser must render themes as a list of tags or expandable rows.

---

### ADR-027: Dynamic Semantic Keyword Filtering
- **Status:** ✅ Accepted
- **Date:** June 2026
- **Context:** Passing all scraped data directly into the LLM Annotation engine (Prompt 1) is expensive and slow. We need to filter for highly relevant reviews, but static keyword searches fail to capture nuances and synonyms (or relevant antonyms).
- **Decision:** Implement a dynamic Semantic Expansion step during Phase 2 preprocessing. The user provides raw target keywords; the system uses an LLM to generate context-specific synonyms and antonyms; the preprocessor then scores every review for "Keyword Density" and truncates low-score/zero-score reviews.
- **Rationale:** 
  - Drastically reduces the volume of "noise" data sent to the LLM (Phase 3) and RAG VectorDB (Phase 8).
  - Domain-specific expansion (via LLM) is superior to strict dictionary matching, successfully capturing slang or opposite concepts (like "repetition" as an antonym to "discovery").
- **Consequences:**
  - Preprocessing is no longer a static step; it now depends on user input (`keywords` payload) and LLM availability.
  - Reviews with a density score of zero are permanently dropped from the dashboard view.

---

## Decision Template

Use this template when adding new decisions:

```markdown
### ADR-NNN: [Decision Title]
- **Status:** ✅ Accepted | ⏳ Proposed | ❌ Rejected | 🔄 Superseded by ADR-XXX
- **Date:** [Month Year]
- **Context:** [What is the issue or constraint that motivates this decision?]
- **Decision:** [What is the change that we are proposing or have agreed to?]
- **Rationale:**
  - [Why is this the best option?]
  - [What alternatives were considered and why were they rejected?]
- **Consequences:**
  - [What are the trade-offs or downsides?]
  - [What follow-up work is needed?]
```

---

*This document is a living record. New decisions should be appended chronologically. When revisiting a past decision, mark the original as **Superseded** and reference the new ADR.*

---
**Owner:** Growth Engineering · **Status:** Living Document
