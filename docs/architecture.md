# Spotify Feedback Intelligence Platform — System Architecture

**Team:** Growth · **Role:** Engineering · **Version:** 1.0  
**Date:** June 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Layer 1 — Data Acquisition (Scrapers)](#4-layer-1--data-acquisition-scrapers)
5. [Layer 2 — Preprocessing Pipeline](#5-layer-2--preprocessing-pipeline)
6. [Layer 3 — AI Analysis Engine](#6-layer-3--ai-analysis-engine)
7. [Layer 4 — Aggregation & Insight Generation](#7-layer-4--aggregation--insight-generation)
8. [Layer 5 — RAG (Retrieval-Augmented Generation)](#8-layer-5--rag-retrieval-augmented-generation)
9. [Layer 6 — REST API](#9-layer-6--rest-api)
10. [Layer 7 — Frontend Application](#10-layer-7--frontend-application)
11. [Data Models & Schemas](#11-data-models--schemas)
12. [Data Flow & Pipeline Orchestration](#12-data-flow--pipeline-orchestration)
13. [File System & Storage Layout](#13-file-system--storage-layout)
14. [Resilience & Error Handling](#14-resilience-error-handling)
15. [Privacy & Security](#15-privacy-security)
16. [Performance & Rate Limiting](#16-performance-rate-limiting)
17. [Deployment Architecture](#17-deployment-architecture)
18. [Detailed Phase-Wise Implementation Roadmap](#18-detailed-phase-wise-implementation-roadmap)

---

## 1. System Overview

The Spotify Feedback Intelligence Platform is an **AI-powered review analysis engine** that ingests user feedback from multiple public platforms, processes it through a multi-stage pipeline, and surfaces structured product insights through an interactive dashboard.

### 1.1 Core Mission

> Surface the precise friction points, behavioural patterns, and unmet needs preventing meaningful music discovery — using real user feedback at scale.

### 1.2 Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Ephemeral Processing** | All analysis occurs in-memory per pipeline run; no PII is stored persistently |
| **Stateless API** | Each API query is independent; aggregated JSON files serve as the read layer |
| **Modular Pipeline** | Each stage (scrape → preprocess → annotate → aggregate) runs independently and is resumable |
| **LLM-Agnostic** | Swappable LLM backends (Ollama local, Groq cloud) with automatic fallback to heuristic mock annotations |
| **Progressive Enhancement** | Frontend displays results as they become available; scraping and analysis run as background jobs |

### 1.3 Six Research Questions

The entire system is architected to answer six product research questions:

| # | Question | Pipeline Stage |
|---|----------|---------------|
| Q1 | Why do users struggle to discover new music? | Barrier type classification |
| Q2 | What are the most common recommendation frustrations? | Theme extraction & scoring |
| Q3 | What listening behaviours are users trying to achieve? | Intent archetype segmentation |
| Q4 | What causes users to repeatedly listen to the same content? | Repetition trigger analysis |
| Q5 | Which user segments experience different challenges? | Segment-level aggregation |
| Q6 | What unmet needs emerge consistently across reviews? | Unmet need clustering & ranking |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                              │
│  ┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐ │
│  │Dashboard │  │Theme Explorer│  │ Reviews │  │ Segments │  │  RAG Chat │ │
│  └────┬─────┘  └──────┬───────┘  └────┬────┘  └────┬─────┘  └─────┬─────┘ │
│       │               │              │             │              │        │
│       └───────────────┴──────────┬───┴─────────────┴──────────────┘        │
│                                  │  Axios HTTP                             │
└──────────────────────────────────┼─────────────────────────────────────────┘
                                   │
                              CORS (localhost:5173)
                                   │
┌──────────────────────────────────┼─────────────────────────────────────────┐
│                       BACKEND (FastAPI + Uvicorn)                          │
│                                  │                                         │
│  ┌───────────────────────────────┴──────────────────────────────────────┐  │
│  │                         REST API Layer (/api)                        │  │
│  │  /summary  /reviews  /themes  /behaviors  /segments  /unmet-needs   │  │
│  │  /insights/*  /scrape  /analyze  /export/*  /chat (Prompt 3)        │  │
│  └───────────┬───────────────────────────────────────────┬─────────────┘  │
│              │                                           │                 │
│  ┌───────────┴────────────┐              ┌───────────────┴──────────────┐  │
│  │   Aggregated JSON      │              │       RAG Subsystem          │  │
│  │   (Read Layer)         │              │  ┌────────────────────────┐  │  │
│  │  data/analyzed/*.json  │              │  │  ChromaDB Vector Store │  │  │
│  └───────────┬────────────┘              │  │  (Memory 1 & Memory 2) │  │  │
│              │                           │  └──────────┬─────────────┘  │  │
│              │ written by                │             │ embeddings     │  │
│  ┌───────────┴──────────────────────┐    │  ┌──────────┴─────────────┐  │  │
│  │     ANALYSIS PIPELINE            │    │  │  Ollama Embeddings     │  │  │
│  │                                  │    │  │  (nomic-embed-text)    │  │  │
│  │  ┌──────────────────────────┐    │    │  └────────────────────────┘  │  │
│  │  │ Phase 4: Aggregator      │    │    └─────────────────────────────┘  │
│  │  │ (themes, behaviors,      │    │                                     │
│  │  │  segments, needs, stats) │    │                                     │
│  │  └──────────┬───────────────┘    │                                     │
│  │             │                    │                                     │
│  │  ┌──────────┴───────────────┐    │                                     │
│  │  │ Phase 3: BatchAnalyzer   │    │                                     │
│  │  │ (Prompt 1 Annotation &   │    │                                     │
│  │  │  Prompt 2 RAG Ingestion) │    │                                     │
│  │  └──────────┬───────────────┘    │                                     │
│  │             │                    │                                     │
│  │  ┌──────────┴───────────────┐    │                                     │
│  │  │ Phase 2: Preprocessor    │    │                                     │
│  │  │ (Track 1 / Track 2       │    │                                     │
│  │  │  parallel filtering)     │    │                                     │
│  │  └──────────┬───────────────┘    │                                     │
│  │             │                    │                                     │
│  └─────────────┼────────────────────┘                                     │
│                │                                                          │
│  ┌─────────────┴────────────────────┐                                     │
│  │     SCRAPERS (Phase 1)           │                                     │
│  │  ┌──────────┐  ┌──────────────┐  │                                     │
│  │  │App Store │  │ Play Store   │  │                                     │
│  │  │(Track 1: │  │ (Track 1:    │  │                                     │
│  │  │ reviews) │  │  reviews)    │  │                                     │
│  │  └──────────┘  └──────────────┘  │                                     │
│  │  ┌──────────┐  ┌──────────────┐  │                                     │
│  │  │Reddit    │  │ Spotify      │  │                                     │
│  │  │(Track 2: │  │ Community    │  │                                     │
│  │  │ threads) │  │ (Track 2)    │  │                                     │
│  │  └──────────┘  └──────────────┘  │                                     │
│  └──────────────────────────────────┘                                     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  CROSS-CUTTING: LLM Client (Ollama / Groq) · Token Tracker ·      │  │
│  │  Logger · File I/O · Date Normalizer · Pydantic Config             │  │
│  │  Prompts (1: Annotate, 2: Ingest RAG, 3: Synthesize Chatbot)        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI ≥ 0.110 | Async REST API with auto-generated OpenAPI docs |
| **ASGI Server** | Uvicorn ≥ 0.28 | High-performance async server with hot-reload |
| **LLM — Local** | Ollama (llama3.1:8b) | Self-hosted inference for AI annotation |
| **LLM — Cloud** | Groq API (llama-3.1-8b-instant) | Low-latency cloud LLM with automatic failover |
| **Vector Database** | ChromaDB ≥ 0.4.24 | Persistent vector store for RAG semantic search |
| **Embedding Model** | nomic-embed-text (via Ollama) | 768-dimensional embeddings for review similarity |
| **Browser Automation** | Playwright ≥ 1.42 | Stealth headless Chromium for web scraping |
| **HTML Parsing** | BeautifulSoup4 ≥ 4.12 | HTML tag stripping and content extraction |
| **HTTP Client** | httpx ≥ 0.27 | Async HTTP requests for API calls and scraping |
| **Play Store API** | google-play-scraper ≥ 1.2.7 | Native Python package for Play Store reviews |
| **PDF Generation** | ReportLab ≥ 4.1 | Professional PDF report generation with branding |
| **Configuration** | Pydantic Settings v2 | Type-safe env-based configuration with `.env` support |
| **Data Validation** | Pydantic ≥ 2.6 | Schema enforcement for API models and data contracts |

### 3.2 Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **UI Framework** | React 18 | Component-driven SPA |
| **Build Tool** | Vite 5 | Fast HMR development server and build pipeline |
| **Styling** | Tailwind CSS 4 | Utility-first styling with dark mode (slate/emerald palette) |
| **Routing** | React Router v6 (HashRouter) | Client-side navigation with hash-based URLs |
| **State Management** | Zustand 4 | Lightweight global store with async actions |
| **HTTP Client** | Axios | Promise-based HTTP client with interceptors |
| **Charts** | Recharts 2.12 | Composable SVG chart components |
| **Data Tables** | TanStack React Table 8 | Headless, type-safe table with sorting/filtering/pagination |
| **Icons** | Lucide React | Consistent icon set |

### 3.3 Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Storage** | Local JSON filesystem | Zero-database design; all data persisted as JSON files |
| **Process Orchestration** | Python subprocess + threading | Background job execution with real-time log streaming |
| **Testing** | pytest ≥ 8.0 | Backend test framework |
| **Linting** | ESLint 8 | Frontend code quality enforcement |

---

## 4. Layer 1 — Data Acquisition (Scrapers)

### 4.1 Architecture

All scrapers inherit from `BaseScraper`, which provides:

```
BaseScraper (ABC)
├── _random_delay()          → Anti-detection rate limiting (configurable min/max ms)
├── _retry_with_backoff()    → Exponential backoff with jitter (max 3 retries)
├── _save_raw()              → Deduplicated JSON persistence to data/raw/<source>/
├── browser_session()        → Playwright context manager with stealth configurations
└── scrape(limit) [abstract] → Source-specific implementation
```

### 4.2 Source Implementations

| Scraper | Class | Data Source | Method | Output Fields |
|---------|-------|------------|--------|---------------|
| **Apple App Store** | `AppStoreScraper` | iTunes RSS JSON API | `httpx` GET, paginated (50/page, max 10 pages) | review_id, source, author, rating, date, body |
| **Google Play Store** | `PlayStoreScraper` | `google-play-scraper` package | `asyncio.to_thread()` wrapping sync API | review_id, source, author, rating, date, body |
| **Reddit** | `RedditScraper` | PullPush Search API (r/spotify) | `httpx` GET with 5 intent-based search queries | review_id, source, author, rating (default 3), date, body, metadata.{score, num_comments, url} |
| **Spotify Community** | `SpotifyCommunityScraper` | RSS Board Feed (XML) | `httpx` GET + `xml.etree.ElementTree` parsing | review_id, source, author, rating (default 3), date, body, metadata.{url} |

### 4.3 Stealth & Anti-Detection

- Custom User-Agent strings (Chrome 122 on macOS)
- `navigator.webdriver` property overridden via `context.add_init_script()`
- Randomised delay between requests (500ms–2000ms, configurable)
- Headless mode toggle via `SCRAPER_HEADLESS` setting
- `--disable-blink-features=AutomationControlled` Chrome flag

### 4.4 Output Format

All scrapers produce a **normalised review record** saved to `data/raw/<source>/<YYYY-MM-DD>.json`:

```json
{
  "review_id": "string (unique per source)",
  "source": "app_store | play_store | reddit | spotify_community",
  "author": "string",
  "rating": 1-5,
  "date": "YYYY-MM-DD",
  "body": "string (review text)",
  "metadata": { "score": 0, "num_comments": 0, "url": "" },
  "scraped_at": "ISO-8601 UTC timestamp"
}
```

---

## 5. Layer 2 — Preprocessing Pipeline

### 5.1 Pipeline Stages & Dual-Track Processing

The preprocessing pipeline partitions raw feedback data into two parallel tracks based on source structure (individual star-rated reviews vs. conversational discussion threads) before feeding them to the AI engine.

```
                  ┌──────────────────────────────────────────────┐
                  │                 RAW SCRAPES                  │
                  │  App Store, Play Store, Reddit, Community    │
                  └──────┬────────────────────────────────┬──────┘
                         │                                │
        [Individual Reviews]                      [Discussion Threads]
       App Store & Play Store                  Reddit & Spotify Community
                         │                                │
                         ▼                                ▼
          ┌─────────────────────────────┐  ┌─────────────────────────────┐
          │     Track 1 Preprocessing   │  │    Track 2 Preprocessing    │
          ├─────────────────────────────┤  ├─────────────────────────────┤
          │ • Clean Metadata            │  │ • Chunk each thread as one  │
          │ • Remove Exact/Near Dups    │  │   single thread-level chunk │
          │ • Remove Emoji-only reviews │  └──────────────┬──────────────┘
          │ • Remove < 20 character body│                 │
          │ • Remove Non-English text   │                 │
          │ • Keyword Density Filtering │                 │
          │ • Text Chunking             │                 │
          └──────────────┬──────────────┘                 │
                         │                                │
                         ▼                                ▼
                  ┌──────┴────────────────────────────────┴──────┐
                  │            PREPROCESSED OUTPUT               │
                  │      (individual reviews & forum chunks)     │
                  └──────────────────────────────────────────────┘
```

### 5.2 Deduplication Strategy (Two-Pass)

**First Pass** — Exact structural duplicates:
- Tokenise first 25 characters of each review body
- Group by `frozenset` of tokens (Jaccard similarity = 1.0)
- Retain the review with the highest engagement score from each group

**Second Pass** — Near-duplicate detection:
- Jaccard similarity threshold: **>0.85**
- Only applied to reviews with body length > 50 characters
- Length-ratio optimisation: skip comparisons if `len2 > 2 × len1` (since reviews are sorted by length)
- Author-aware: distinct non-anonymous authors bypass duplicate check
- Retain the review with the higher engagement score

### 5.3 Noise Filtering Rules (PRE-LLM Filters)

The pipeline partitions pre-LLM filtering rules into two separate parallel pipelines depending on the track:

#### 5.3.1 PRE-LLM Filters 1 (Track 1: App Store & Play Store)
These rules clean and validate individual star-rated reviews:

| Filter | Rule / Implementation Details | Purpose |
|--------|------------------------------|---------|
| **Clean Metadata** | HTML entities decoded, HTML tags stripped, whitespace collapsed | Standardize body text and remove formatting noise |
| **Remove Duplicate** | Two-pass deduplication (Jaccard similarity threshold = 1.0 / 0.85) | Avoid processing redundant reviews to save costs and compute |
| **Remove Only Emoji** | Unicode category/block matching checks | Exclude feedback with no alphanumeric or semantic textual content |
| **Remove <20 Char** | clean body length < 20 characters | Filter out trivially short reviews that lack actionable signal |
| **Remove Non-English** | Language detection filtering | Focus synthesis on English-language user feedback |
| **Semantic Keyword Density** | Receive raw keywords from user (frontend) -> LLM expands into list of synonyms/antonyms -> Calculate density score for each review -> Sort descending and truncate to limit. | Reduce noise and constrain data fed into RAG memory based on user's target concepts |
| **Chunking** | Text split into model-optimal passages | Avoid truncation in LLM context windows |

#### 5.3.2 PRE-LLM Filters 2 (Track 2: Reddit & Spotify Community)
These rules handle conversational forum discussion threads:

| Filter | Rule / Implementation Details | Purpose |
|--------|------------------------------|---------|
| **Chunk Thread** | Chunk each conversation thread as one single cohesively indexed block | Preserve context, replies, and community consensus signals |

### 5.4 Engagement Score Extraction

Normalised from source-specific fields via a priority cascade:

```
Top-level: helpful_count → score → likes → kudos → upvotes → engagement_score
Metadata:  helpful_count → score → likes → kudos → upvotes → num_comments
Fallback:  0
```

---

## 6. Layer 3 — AI Analysis Engine

### 6.1 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   BatchAnalyzer                           │
│                                                          │
│  ┌─────────────────┐     ┌────────────────────────────┐  │
│  │ Load preprocessed│ ──▶│ Resume check (skip already │  │
│  │ all_reviews.json │     │ annotated review_ids)      │  │
│  └─────────────────┘     └──────────┬─────────────────┘  │
│                                     │                     │
│              ┌──────────────────────┴──────────────┐      │
│              │  Batch Loop (batch_size = 20)       │      │
│              │                                     │      │
│              │  ┌───────────────────────────────┐  │      │
│              │  │  LLMClient.annotate_batch()   │  │      │
│              │  │  ┌─────────────────────────┐  │  │      │
│              │  │  │ Provider Selection:     │  │  │      │
│              │  │  │ Groq (cloud) │ Ollama   │  │  │      │
│              │  │  │ (local) │ Mock (fallback)│  │  │      │
│              │  │  └─────────────────────────┘  │  │      │
│              │  └───────────┬───────────────────┘  │      │
│              │              │                      │      │
│              │  ┌───────────┴───────────────────┐  │      │
│              │  │ normalize_and_validate()      │  │      │
│              │  │ (enum clamping, type coercion,│  │      │
│              │  │  metadata preservation)       │  │      │
│              │  └───────────┬───────────────────┘  │      │
│              │              │                      │      │
│              │  ┌───────────┴───────────────────┐  │      │
│              │  │ Append to reviews_analyzed.json│  │      │
│              │  │ (incremental write per batch) │  │      │
│              │  └──────────────────────────────┘  │      │
│              └────────────────────────────────────┘      │
│                                                          │
│  Failed batches → data/errors/batch_*_failed.json        │
│  Retry pipeline: retry_failed_batches()                  │
└──────────────────────────────────────────────────────────┘
```

### 6.2 LLM Client — Provider Hierarchy

```
1. GROQ_API_KEY detected?
   ├── YES → Use Groq Cloud (llama-3.1-8b-instant)
   │         • JSON mode: response_format = {"type": "json_object"}
   │         • Rate limit: proactive TPM/RPM throttling via response headers
   │         • 429 handling: retry-after header + backoff
   │
   └── NO → Use Ollama Local (llama3.1:8b)
             ├── Ollama reachable?
             │   ├── YES → JSON mode: format = "json"
             │   └── NO → Fallback to heuristic mock annotation model
             │
             └── Mock model generates structured annotations
                 using keyword-based heuristics for all fields
```

### 6.3 Internal Prompts System

The AI Analysis Engine is driven by three distinct internal prompts designed to analyze, structure, and synthesize discovery insights.

#### 6.3.1 Prompt 1: Core Research System Prompt (Annotation Phase)
Used during Phase 3 of the pipeline. The system prompt instructs the LLM:
> **Your review analysis system should help answer questions such as:**
> - Why do users struggle to discover new music?
> - What are the most common frustrations with recommendations?
> - What listening behaviors are users trying to achieve?
> - What causes users to repeatedly listen to the same content?
> - Which user segments experience different discovery challenges?
> - What unmet needs emerge consistently across reviews?

To answer these questions, the LLM maps review content to a structured JSON object with `{"reviews": [...]}` containing two tiers of fields:

**Review-Level Fields (Global Context):**

| Field | Type | Description / Valid Values |
|-------|------|---------------------------|
| `discovery_related` | boolean | Whether review concerns music/podcast discovery |
| `user_segment` | enum | `casual`, `power_user`, `new_user`, `churned`, `unknown` |
| `segment_signal` | string | Text evidence for segment classification |
| `intent_archetype` | enum | `mood_listener`, `genre_explorer`, `social_discoverer`, `passive_listener`, `active_curator`, `lapsed_discoverer` |
| `repetition_described` | boolean | Whether review explicitly describes repetitive listening |

**Theme-Level Fields (Array of objects in `themes`):**
A single review can touch on multiple distinct themes. The LLM extracts an array of `themes`, where each object contains:

| Field | Type | Description / Valid Values |
|-------|------|---------------------------|
| `theme_name` | enum | 16 values: `discovery_friction`, `algorithm_repetition`, `recommendation_quality`, `discover_weekly_specific`, `radio_quality`, `made_for_you_feedback`, `genre_exploration`, `mood_based_listening`, `social_discovery`, `cross_platform_discovery`, `concert_live_discovery`, `podcast_discovery`, `algorithm_history_lock`, `feature_request`, `positive_discovery`, `unrelated` |
| `sentiment` | enum | `positive`, `negative`, `neutral`, `mixed` |
| `sentiment_score` | float | -1.0 to 1.0 |
| `barrier_type` | enum | `algorithmic`, `ui_ux`, `content_gap`, `awareness`, `habit`, `none` |
| `frustration_phrase` | string | Verbatim-style short phrase relevant to this specific theme |
| `user_intent` | string | Free-text description of user goal regarding this theme |
| `repetition_trigger` | enum | `algorithm_lock`, `no_exploration_ui`, `comfort_habit`, `no_new_content`, `none` |
| `unmet_need` | string | Underlying need Spotify doesn't meet regarding this theme |

#### 6.3.2 Prompt 2: RAG Memory Partitioning Prompt (Internal)
Used to divide preprocessed and analyzed content into two RAG memory collections based on the preprocessing track:
> **Make 2 rag memory, for each of the two data types from each of the filters**

Specifically:
- **Memory 1 (Individual Reviews):** Built from Track 1 (App Store & Play Store) records after cleaning, emoji removal, language filters, and keyword density checks.
- **Memory 2 (Discussion Threads):** Built from Track 2 (Reddit & Spotify Community) threads, chunking each conversation thread as a single cohesive context block.

#### 6.3.3 Prompt 3: Chatbot Synthesis Prompt (User Q&A Phase / Internal)
Triggered via POST `/api/chat`. It coordinates the chatbot synthesis flow:
1. The **User Prompt for RAG Chatbot** queries both **Memory 1** and **Memory 2** in parallel.
2. Retrieved contexts from both memories and the user's natural language query are formatted and injected into the **Prompt 3: internal** synthesis template.
3. This prompt instructs the LLM to output a synthesized, grounded answer citing specific records (e.g., `[App Store #2]` or `[Reddit #5]`) with clear citation links.

### 6.4 Post-LLM Validation

The `normalize_and_validate()` method enforces data quality after LLM output:

- **Enum clamping**: Invalid enum values → fallback default (e.g., `"unrelated"`, `"neutral"`)
- **Type coercion**: String booleans → Python booleans; string numbers → floats
- **Score bounding**: `sentiment_score` clipped to [-1.0, 1.0]
- **Metadata preservation**: Original review fields (source, body, date, etc.) are retained alongside AI-generated annotations
- **Discovery override**: `primary_theme == "unrelated"` forces `discovery_related = False`

### 6.5 Error Recovery

- **Batch-level retry**: Failed batches are saved to `data/errors/batch_<timestamp>_<num>_failed.json`
- **Request splitting**: 413/TPM-limit errors → batch is automatically split in half and retried
- **JSON repair**: Malformed LLM output → correction prompt appended to conversation and retried
- **Resumability**: `reviews_analyzed.json` tracks which `review_id`s have been processed; pipeline resumes from last checkpoint
- **Stale data cleanup**: If preprocessed data changes, stale analyzed reviews are pruned on next run

---

## 7. Layer 4 — Aggregation & Insight Generation

### 7.1 Aggregation Pipeline

The `Aggregator` class reads `reviews_analyzed.json` and produces 6 output files:

| Output File | Contents | Answers |
|-------------|----------|---------|
| `themes.json` | Theme frequency, avg sentiment, pain score, top frustrations per theme | Q1, Q2 |
| `behaviors.json` | Archetype distribution, % of discovery reviews, top intents/needs | Q3 |
| `repetition_causes.json` | Trigger frequency, affected segments, sample frustrations | Q4 |
| `segments.json` | Segment size, avg sentiment, top themes/barriers/needs per segment | Q5 |
| `unmet_needs.json` | Clustered needs ranked by opportunity score | Q6 |
| `summary.json` | Headline metrics, source breakdown, top-5 themes, generation timestamp | Executive |

### 7.2 Scoring Algorithms

**Theme Pain Score:**
```
Pain Score = frequency × avg(|sentiment_score|) × num_distinct_sources
```

**Unmet Need Opportunity Score:**
```
Opportunity Score = frequency × num_distinct_sources × avg(|sentiment_score|)
```

**Unmet Need Clustering:**
- `SequenceMatcher.ratio()` ≥ 0.70 → group as same need
- Deterministic: first occurrence becomes cluster key
- Each cluster tracked with frequency, sources, phrasings, related themes

### 7.3 Human-Readable Mappings

All internal enum keys are mapped to display labels via constant dictionaries:

```python
THEME_MAPPING = {
    "discovery_friction": "Difficulty Finding New Music",
    "algorithm_repetition": "Stuck in Listening Loops",
    ...
}
ARCHETYPE_MAPPING = { "mood_listener": "Mood Listener", ... }
TRIGGER_MAPPING = { "algorithm_lock": "Algorithm Lock", ... }
BARRIER_MAPPING = { "algorithmic": "Algorithmic", ... }
SEGMENT_MAPPING = { "casual": "Casual User", ... }
```

---

## 8. Layer 5 — RAG (Retrieval-Augmented Generation)

### 8.1 Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           RAG Subsystem                                   │
│                                                                           │
│        ┌──────────────────┐           ┌──────────────────┐                │
│        │   Chat Service   │           │    Retriever     │                │
│        │ (chat_synthesis) │ ────────▶ │ (query_memories) │                │
│        └────────┬─────────┘           └────────┬─────────┘                │
│                 │                              │                          │
│                 │ (Prompt 3 Synthesis)         │ (Dual ChromaDB query)    │
│                 ▼                              ▼                          │
│        ┌──────────────────┐           ┌──────────────────┐                │
│        │    LLMClient     │           │  ChromaDB Store  │                │
│        │ (free-text mode) │           │ ┌──────────────┐ │                │
│        └──────────────────┘           │ │   Memory 1   │ │                │
│                                       │ │  (Reviews)   │ │                │
│                                       │ └──────────────┘ │                │
│                                       │ ┌──────────────┐ │                │
│                                       │ │   Memory 2   │ │                │
│                                       │ │  (Threads)   │ │                │
│                                       │ └──────────────┘ │                │
│                                       └────────┬─────────┘                │
│                                                │                          │
│                                       ┌────────┴─────────┐                │
│                                       │ nomic-embed-text │                │
│                                       │ (768-dim Vector) │                │
│                                       └──────────────────┘                │
└───────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Ingestion Pipeline (`ingest_reviews.py`)

- **Source:** `data/analyzed/reviews_analyzed.json`
- **Dual Partitioning:** The script divides the annotated reviews and threads based on their preprocessing track:
  - **Memory 1 Collection:** Formed from App Store and Play Store reviews.
  - **Memory 2 Collection:** Formed from Reddit and Spotify Community threads.
- Clears both ChromaDB collections before a fresh ingestion run.
- Uploads documents in chunks of 50.
- **Metadata Indexed:** `source`, `rating` (int), `sentiment`, `user_segment`, `primary_theme`.
- **Document Content:** The review `body` text or conversational thread chunk.

### 8.3 Retrieval & Synthesis

1. **User Query:** The user submits a natural language query via the `/api/chat` endpoint.
2. **Dual-Memory Search:** The Retriever queries both ChromaDB collections (**Memory 1** and **Memory 2**) for top-K matches (default K=15 each) using the user's search query embedded via `nomic-embed-text`.
3. **Metadata Filters:** Applies optional pre-filters (e.g. filter by source, rating, or segment) across both memories.
4. **Citation Tagging:** Retrieved contexts are prefixed with distinct tags (e.g., `[Review #1]` vs `[Discussion #3]`) depending on the source collection.
5. **Prompt 3 Synthesis:** Prompt 3 processes the consolidated retrieved context alongside the user's prompt to generate a grounded, synthesized response.
6. **Sources Array:** Returns a structured list matching citations to their original source files, scores, and metadata.

### 8.4 Embedding Fallback

If Ollama is unreachable, the `OllamaEmbeddingFunction` generates **deterministic mock embeddings**:
- 768-dimensional vectors derived from MD5 hash of text
- XOR-based byte expansion with normalisation to [-1.0, 1.0]
- Ensures the system remains functional (with degraded search quality) without external dependencies

---

## 9. Layer 6 — REST API

### 9.1 API Architecture

The FastAPI application registers 10 routers under the `/api` prefix:

```
FastAPI App (main.py)
├── GET  /health                        → Health check
├── /api
│   ├── GET  /summary                   → Executive summary metrics
│   ├── GET  /summary/usage             → Daily API token usage stats
│   ├── GET  /reviews                   → Paginated, filtered review list
│   ├── GET  /themes                    → Aggregated theme data
│   ├── GET  /behaviors                 → Intent archetype distribution
│   ├── GET  /segments                  → User segment profiles
│   ├── GET  /unmet-needs               → Ranked unmet needs
│   ├── GET  /insights/discovery-friction       → Q1 barrier analysis
│   ├── GET  /insights/recommendation-frustrations → Q2 frustration analysis
│   ├── GET  /insights/repetition-causes        → Q4 repetition triggers
│   ├── POST /scrape                    → Trigger background scrape job
│   ├── GET  /scrape/raw-files          → Raw data status per source
│   ├── GET  /scrape/{job_id}           → Job status + log tail
│   ├── POST /analyze                   → Trigger background analysis job
│   ├── GET  /export/pdf                → Generate branded PDF report
│   ├── GET  /export/csv                → Disabled (real-time only)
│   └── POST /chat                      → RAG-powered Q&A endpoint
```

### 9.2 Background Job System

Scrape and analysis operations are executed as **background subprocess tasks**:

```python
# Job lifecycle
Job created (status: "pending")
    → subprocess.Popen launched in background thread
    → stdout streamed line-by-line (last 100 lines retained)
    → Completion: status → "completed" | "failed"

# Thread safety: jobs dict protected by threading.Lock
```

- Job tracking: in-memory dictionary keyed by UUID
- Log tailing: GET `/scrape/{job_id}` returns live output + status
- Source-specific limits: per-scraper limit overrides via request body

### 9.3 CORS Configuration

- Allowed origins: configurable via `CORS_ORIGINS` env var
- Default: `http://localhost:5173`, `http://127.0.0.1:5173`
- All methods and headers allowed for development

---

## 10. Layer 7 — Frontend Application

### 10.1 Application Structure

```
frontend/src/
├── App.jsx              → Root component with HashRouter + MainLayout
├── main.jsx             → React DOM entry point
├── index.css            → Global styles
├── api/
│   └── client.js        → Axios instance + API function exports
├── store/
│   └── useAppStore.js   → Zustand global state store
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx  → Navigation sidebar with route links
│   │   └── Header.jsx   → Top header bar
│   └── charts/          → Reusable chart components (Recharts)
└── pages/
    ├── Dashboard.jsx    → Executive overview with KPI cards, charts, and metrics
    ├── ThemeExplorer.jsx → Interactive theme breakdown and drill-down
    ├── Reviews.jsx      → Paginated review table with multi-filter support
    ├── Segments.jsx     → User segment comparison view
    ├── Export.jsx       → Data management: scraping controls + PDF export
    └── Chat.jsx         → RAG-powered conversational interface
```

### 10.2 State Management (Zustand)

The `useAppStore` maintains centralised state with async data-fetching actions:

| Slice | Fetcher | API Endpoint |
|-------|---------|-------------|
| `summary` | `fetchSummary()` | `GET /summary` |
| `apiUsage` | `fetchApiUsage()` | `GET /summary/usage` |
| `reviews` (paginated) | `fetchReviews(params)` | `GET /reviews` |
| `themes` | `fetchThemes()` | `GET /themes` |
| `segments` | `fetchSegments()` | `GET /segments` |
| `behaviors` | `fetchBehaviors()` | `GET /behaviors` |
| `unmetNeeds` | `fetchUnmetNeeds()` | `GET /unmet-needs` |
| `discoveryFriction` | `fetchDiscoveryFriction()` | `GET /insights/discovery-friction` |
| `repetitionCauses` | `fetchRepetitionCauses()` | `GET /insights/repetition-causes` |

Each action follows the pattern: `setLoading(true) → API call → set data → setLoading(false)`, with error capture.

### 10.3 Design System

- **Color Palette**: Dark mode with slate-950 base, emerald-950 accent, Spotify green (#1DB954) highlights
- **Layout**: Sidebar + Header + scrollable main content area
- **Typography**: System font stack (sans-serif)
- **Responsive**: Flexbox-based layout with `overflow-y-auto` content scrolling

---

## 11. Data Models & Schemas

### 11.1 Raw Review (Scraper Output)

```json
{
  "review_id": "string",
  "source": "app_store | play_store | reddit | spotify_community",
  "author": "string",
  "rating": "int (1-5)",
  "date": "YYYY-MM-DD",
  "body": "string",
  "metadata": { "score": "int", "num_comments": "int", "url": "string" },
  "scraped_at": "ISO-8601"
}
```

### 11.2 Preprocessed Review

Same as raw review with:
- `body` cleaned (HTML stripped, whitespace collapsed, trimmed)
- `date` normalised to `YYYY-MM-DD`
- `engagement_score` field added (int)

### 11.3 Analyzed Review (AI-Annotated)

Preprocessed review + all 14 AI annotation fields from Section 6.3.

### 11.4 Aggregated Theme

```json
{
  "theme_id": "string (enum key)",
  "label": "string (human-readable)",
  "frequency": "int",
  "avg_sentiment_score": "float",
  "sources": { "source_name": "count" },
  "score": "float (pain score)",
  "top_frustrations": ["string"],
  "top_unmet_needs": ["string"]
}
```

### 11.5 Aggregated Unmet Need

```json
{
  "need_id": "need_001",
  "label": "string (cluster key)",
  "frequency": "int",
  "sources": ["string"],
  "avg_sentiment_score": "float",
  "opportunity_score": "float",
  "example_phrasings": ["string"],
  "related_themes": ["string"]
}
```

### 11.6 Summary

```json
{
  "total_reviews": "int",
  "discovery_related_count": "int",
  "discovery_related_pct": "float",
  "sources": { "source": "count" },
  "avg_sentiment_score": "float",
  "top_5_themes": [{ "theme": "label", "count": "int" }],
  "headline_metrics": {
    "top_barrier": "string",
    "top_frustration_theme": "string",
    "top_archetype": "string",
    "top_trigger": "string",
    "most_affected_segment": "string",
    "top_unmet_need": "string"
  },
  "generated_at": "ISO-8601"
}
```

---

## 12. Data Flow & Pipeline Orchestration

### 12.1 End-to-End Pipeline

```
Phase 1: Scraping                    Phase 2: Preprocessing
┌──────────────┐                     ┌────────────────────────────┐
│ run_scrapers  │                     │ run_analysis --stage       │
│ .py           │                     │ preprocess                 │
│               │                     │                            │
│ For each src: │   data/raw/         │ Load all raw files         │
│ scraper       │──▶ <source>/  ────▶│ First-pass dedup           │
│ .scrape(limit)│   <date>.json       │ Clean text + noise filter  │
│               │                     │ Second-pass dedup          │
│               │                     │ Date normalize + 90d filter│
└──────────────┘                     │ Cross-source merge         │
                                     │                            │
                                     │ data/preprocessed/         │
                                     │ all_reviews.json     ─────▶│
                                     └────────────────────────────┘

Phase 3: AI Annotation               Phase 4: Aggregation
┌────────────────────────────┐       ┌────────────────────────────┐
│ run_analysis --stage       │       │ run_analysis --stage       │
│ annotate                   │       │ aggregate                  │
│                            │       │                            │
│ Load all_reviews.json      │       │ Load reviews_analyzed.json │
│ Resume from checkpoint     │       │                            │
│ Batch LLM annotation (20) │       │ _aggregate_themes()        │
│ Normalize + validate       │       │ _aggregate_behaviors()     │
│ Save per batch             │       │ _aggregate_repetition()    │
│                            │       │ _aggregate_segments()      │
│ data/analyzed/             │       │ _aggregate_unmet_needs()   │
│ reviews_analyzed.json ────▶│       │ _generate_summary()        │
│                            │       │                            │
│ On error:                  │       │ data/analyzed/             │
│ data/errors/*.json         │       │ ├── themes.json            │
└────────────────────────────┘       │ ├── behaviors.json         │
                                     │ ├── repetition_causes.json │
Phase 5: Vector Ingestion            │ ├── segments.json          │
┌────────────────────────────┐       │ ├── unmet_needs.json       │
│ ingest_reviews.py          │       │ └── summary.json           │
│                            │       └────────────────────────────┘
│ Clear ChromaDB collection  │
│ Batch upsert (chunks of 50)│
│ Index: body + metadata     │
│                            │
│ backend/data/vectorstore/  │
└────────────────────────────┘
```

### 12.2 Orchestration Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `run_scrapers.py` | `scripts/` | CLI with `--sources`, `--limit`, per-source overrides |
| `run_analysis.py` | `scripts/` | CLI with `--stage` (preprocess/annotate/aggregate), `--retry-failed`, `--min-body-len` |
| `ingest_reviews.py` | `scripts/` | CLI with `--source` filter for selective vector ingestion |

### 12.3 Pipeline Triggers

Pipelines can be triggered via:
1. **CLI**: Direct script execution (`python scripts/run_scrapers.py --limit 100`)
2. **API**: `POST /api/scrape` (with `limit` payload) or `POST /api/analyze` → spawns subprocess in background thread
3. **Frontend**: Export page controls call the API endpoints with progress polling

---

## 13. File System & Storage Layout

```
project-root/
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── config.py                ← Pydantic Settings (reads .env)
│   ├── .env                     ← Environment variables (GROQ_API_KEY, etc.)
│   ├── requirements.txt         ← Python dependencies
│   ├── scrapers/
│   │   ├── base_scraper.py      ← Abstract base with shared utilities
│   │   ├── app_store.py         ← Apple App Store (iTunes RSS)
│   │   ├── play_store.py        ← Google Play Store (package API)
│   │   ├── reddit.py            ← Reddit (PullPush API)
│   │   └── spotify_community.py ← Spotify Community (RSS XML)
│   ├── analysis/
│   │   ├── preprocessor.py      ← Phase 2: text cleaning + dedup
│   │   ├── batch_analyzer.py    ← Phase 3: LLM annotation loop
│   │   ├── llm_client.py        ← Multi-provider LLM client
│   │   ├── prompts.py           ← System prompt + formatting
│   │   └── aggregator.py        ← Phase 4: statistical aggregation
│   ├── rag/
│   │   ├── vector_store.py      ← ChromaDB client + embedding function
│   │   ├── retriever.py         ← Similarity search with metadata filters
│   │   └── chat_service.py      ← RAG synthesis (retrieval + LLM answer)
│   ├── routers/
│   │   ├── summary.py           ← GET /summary, /summary/usage
│   │   ├── reviews.py           ← GET /reviews (paginated + filtered)
│   │   ├── themes.py            ← GET /themes
│   │   ├── behaviors.py         ← GET /behaviors
│   │   ├── segments.py          ← GET /segments
│   │   ├── unmet_needs.py       ← GET /unmet-needs
│   │   ├── insights.py          ← GET /insights/* (Q1, Q2, Q4)
│   │   ├── scrape.py            ← POST /scrape, GET /scrape/{id}
│   │   ├── export.py            ← GET /export/pdf (ReportLab)
│   │   └── chat.py              ← POST /chat (RAG endpoint)
│   ├── models/
│   │   ├── review.py            ← Pydantic model for review
│   │   ├── summary.py           ← Pydantic model for summary
│   │   ├── theme.py             ← Pydantic model for theme
│   │   ├── behavior.py          ← Pydantic model for behavior
│   │   ├── segment.py           ← Pydantic model for segment
│   │   ├── unmet_need.py        ← Pydantic model for unmet need
│   │   └── repetition_cause.py  ← Pydantic model for repetition cause
│   ├── utils/
│   │   ├── logger.py            ← Structured logging setup
│   │   ├── file_io.py           ← JSON read/write helpers
│   │   ├── date_normalizer.py   ← Multi-format date → YYYY-MM-DD
│   │   └── token_tracker.py     ← LLM API usage tracking (daily limits)
│   ├── data/                    ← Symlink or resolved relative path to ../data
│   │   └── vectorstore/         ← ChromaDB persistent storage
│   └── tests/                   ← pytest test suite
│
├── frontend/
│   ├── index.html               ← SPA entry point
│   ├── package.json             ← Node dependencies (React, Vite, etc.)
│   ├── vite.config.js           ← Vite config with React plugin
│   └── src/                     ← React source (see Section 10.1)
│
├── scripts/
│   ├── run_scrapers.py          ← Phase 1 orchestrator
│   ├── run_analysis.py          ← Phase 2-4 orchestrator
│   └── ingest_reviews.py        ← Phase 5 vector ingestion
│
├── data/
│   ├── raw/
│   │   ├── app_store/<date>.json
│   │   ├── play_store/<date>.json
│   │   ├── reddit/<date>.json
│   │   └── spotify_community/<date>.json
│   ├── preprocessed/
│   │   └── all_reviews.json
│   ├── analyzed/
│   │   ├── reviews_analyzed.json
│   │   ├── themes.json
│   │   ├── behaviors.json
│   │   ├── repetition_causes.json
│   │   ├── segments.json
│   │   ├── unmet_needs.json
│   │   └── summary.json
│   ├── errors/
│   │   └── batch_*_failed.json
│   ├── exports/
│   └── api_usage.json
│
└── docs/
    ├── Problem_Statement.md
    └── architecture.md           ← This document
```

---

## 14. Resilience & Error Handling

### 14.1 Scraper Resilience

| Mechanism | Implementation |
|-----------|---------------|
| Exponential backoff | `_retry_with_backoff()`: 3 retries, base delay 5s, 2× growth + jitter |
| Anti-rate-limiting | Randomised delay between requests (500ms–2000ms) |
| Stealth browsing | Custom UA, webdriver property override, automation flags disabled |
| Deduplication on save | `_save_raw()` deduplicates by `review_id` before writing |
| Source isolation | Each scraper failure is caught independently; other sources continue |

### 14.2 LLM Resilience

| Mechanism | Implementation |
|-----------|---------------|
| Provider fallback | Groq → Ollama → Heuristic mock (automatic cascade) |
| JSON repair | Malformed output → correction prompt appended and retried (up to 3 times) |
| Batch splitting | 413 / TPM limit → batch halved and retried recursively |
| Request throttling | Minimum 2s between requests; proactive TPM/RPM checks via Groq headers |
| Token tracking | Daily call/token limits tracked per-day in `api_usage.json` |
| Incremental save | Each annotated batch is appended to disk immediately (no loss on crash) |
| Failed batch queue | Errors saved to `data/errors/` for later retry via `--retry-failed` |

### 14.3 Pipeline Resilience

| Mechanism | Implementation |
|-----------|---------------|
| Resumable annotation | `reviews_analyzed.json` acts as checkpoint; processed IDs are skipped |
| Stale data pruning | Analyzed reviews not in preprocessed set are removed on next run |
| Background job isolation | Scrape/analyze run as subprocesses; API server unaffected by crashes |
| Log rotation | Background jobs retain last 100 log lines to cap memory |

---

## 15. Privacy & Security

### 15.1 Data Handling Principles

| Principle | Implementation |
|-----------|---------------|
| **No PII storage** | Author names are scraped but never sent to the LLM (prompt includes only `review_id` + `body`) |
| **Public data only** | All scrapers target publicly available APIs/feeds; no authentication on behalf of users |
| **Theme-level analysis** | AI analyses patterns across reviews, never profiling individuals |
| **Ephemeral API processing** | LLM requests are stateless; no user data retained by Groq/Ollama |
| **Local-first** | Ollama runs locally; Groq is optional cloud inference |
| **No external logging** | All logs are local files; no telemetry or third-party analytics |

### 15.2 Secret Management

- API keys stored in `backend/.env` (git-ignored)
- `.env.example` provides template without real values
- `pydantic-settings` loads environment variables with type validation

---

## 16. Performance & Rate Limiting

### 16.1 Scraping Performance

| Source | Throughput | Constraint |
|--------|-----------|------------|
| App Store | ~50 reviews/page, max 500 total | iTunes RSS pagination limit |
| Play Store | Up to limit (bulk API) | `google-play-scraper` rate limits |
| Reddit | ~25 posts/query × 5 queries | PullPush API throttling |
| Spotify Community | RSS feed size (typically 25–50 items) | Single feed endpoint |

### 16.2 LLM Performance

| Provider | Batch Size | Rate Limits | Throttling |
|----------|-----------|-------------|------------|
| Groq | 20 reviews/batch | 30 RPM, 6K TPM (free tier) | Proactive: sleep when remaining tokens < 4500 or remaining requests < 2 |
| Ollama | 20 reviews/batch | Local hardware | 2s minimum between requests |
| Mock | 20 reviews/batch | None | Instant (heuristic) |

### 16.3 API Performance

- All aggregated data served from pre-computed JSON files (O(1) read, no computation on request)
- Review pagination: server-side offset/limit against in-memory list
- CORS: restricted to configured origins
- Timeout: 30s default for Axios; 90s for LLM API calls

---

## 17. Deployment Architecture

### 17.1 Development (Current)

```
┌─────────────────────────────────────────────────┐
│                  Developer Machine               │
│                                                  │
│  ┌─────────────┐          ┌─────────────┐       │
│  │ Vite Dev     │ ◀─────▶ │ Uvicorn     │       │
│  │ Server       │  HTTP    │ Dev Server  │       │
│  │ :5173        │          │ :8000       │       │
│  └─────────────┘          └──────┬──────┘       │
│                                  │               │
│                           ┌──────┴──────┐       │
│                           │ Ollama      │       │
│                           │ :11434      │       │
│                           └─────────────┘       │
│                                                  │
│  data/ (local filesystem)                        │
│  backend/data/vectorstore/ (ChromaDB)            │
└─────────────────────────────────────────────────┘
```

### 17.2 Configuration

All configuration is managed through environment variables (`.env`):

```env
# LLM Provider
LLM_PROVIDER=ollama          # ollama | groq
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
GROQ_API_KEY=                # Auto-switches to groq if set
GROQ_MODEL=llama-3.1-8b-instant
LLM_BATCH_SIZE=20
DAILY_TOKEN_LIMIT=500000
DAILY_CALL_LIMIT=1000

# RAG
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_TOP_K=15

# Scraping
SCRAPER_HEADLESS=true
SCRAPER_DELAY_MS_MIN=500
SCRAPER_DELAY_MS_MAX=2000
REDDIT_FETCH_COMMENTS=false

# Paths & Server
DATA_DIR=../data
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

---

## 18. Detailed Phase-Wise Implementation Roadmap

The building and deployment of the Spotify Feedback Intelligence Platform is partitioned into 9 chronological phases, structured by data flow dependency constraints (each stage's output feeds directly as input to the next).

### 18.1 Phase 0: Project Scaffolding & Environment Setup
- **Goal:** Initialize project folders, environments, and configuration schemas.
- **Key Tasks:**
  - Initialize the repository, `.gitignore`, and backend dependency specifications (`fastapi`, `uvicorn`, `playwright`, `beautifulsoup4`, `chromadb`, `pydantic`).
  - Scaffold folder hierarchy: `backend/`, `frontend/`, `data/`, `scripts/`, `docs/`.
  - Install Playwright automated browser binaries (`playwright install chromium`).
  - Initialize Vite React project + configuration for Tailwind CSS, Zustand, Recharts, and TanStack Table.
  - Implement type-safe global environment loader via Pydantic `Settings`.
- **Checkpoint/Deliverables:**
  - Working local development loop; React app runs on port 5173, FastAPI shell starts on port 8000.
  - Ollama is verified local-running with `llama3.1:8b` model pulled.

### 18.2 Phase 1: Data Acquisition (Scrapers)
- **Goal:** Construct isolated browser scrapers to harvest user reviews and feedback into local raw storage.
- **Key Tasks:**
  - Build `BaseScraper` class supporting Playwright lifecycle, stealth browsing injections, randomized delay intervals (500ms–2000ms), and exponential retry logic.
  - Build source-specific scrapers: `PlayStoreScraper`, `AppStoreScraper`, `RedditScraper` (old.reddit.com querying r/spotify), and `SpotifyCommunityScraper` (RSS categories parsing).
  - Develop CLI scraper orchestration script (`scripts/run_scrapers.py`) with support for selective sources and limit constraints.
- **Checkpoint/Deliverables:**
  - Scraped JSON collections saved to `data/raw/<source>/YYYY-MM-DD.json`.
  - Individual scraper components successfully handle rate limits and captcha blocks without crashes.

### 18.3 Phase 2: Preprocessing & Normalization
- **Goal:** Clean and normalize the raw review content into a uniform, deduplicated pipeline-ready dataset.
- **Key Tasks:**
  - Build two-pass deduplication logic: Jaccard similarity = 1.0 (first 25 characters) on first pass; Jaccard > 0.85 Jaccard threshold on body length > 50 characters on second pass.
  - Standardize text bodies (HTML stripping via BeautifulSoup, entity decoding, whitespace normalization).
  - Apply noise filters (discard under 20 characters, remove emoji-only inputs, filter out elements older than 90 days).
  - Normalize dates to YYYY-MM-DD format and compute standardized engagement scores.
- **Checkpoint/Deliverables:**
  - Execution of `run_analysis.py --stage preprocess` compiles all cleaned records into `data/preprocessed/all_reviews.json`.

### 18.4 Phase 3: AI Analysis & Annotation
- **Goal:** Batch annotate preprocessed records through the LLM to extract structured research metadata.
- **Key Tasks:**
  - Write multi-provider `LLMClient` with auto-failover, JSON correction, and rate limits tracking.
  - Structure system prompt matching enums, sentiment bounds, archetypes, and discovery checks.
  - Build `BatchAnalyzer` to send batch arrays (size 20) with progress tracking.
  - Save failed batches to `data/errors/` with `--retry-failed` recovery command support.
- **Checkpoint/Deliverables:**
  - Structured, validated annotations appended to `data/analyzed/reviews_analyzed.json`.

### 18.5 Phase 4: Aggregation & Insight Generation
- **Goal:** Compile review annotations into aggregate statistical insights.
- **Key Tasks:**
  - Write `Aggregator` to process annotations into 6 specific insight files answering the research questions.
  - Calculate theme pain scores and unmet needs opportunity scores.
  - Deterministically cluster similar unmet needs using string ratio similarity matching.
- **Checkpoint/Deliverables:**
  - Aggregate insight files saved: `themes.json`, `behaviors.json`, `repetition_causes.json`, `segments.json`, `unmet_needs.json`, and `summary.json`.

### 18.6 Phase 5: Backend API Layer
- **Goal:** Expose REST endpoints serving aggregated statistics, filtered reviews lists, background job triggers, and export files.
- **Key Tasks:**
  - Build FastAPI application and define strict Pydantic v2 schemas.
  - Implement filtering and pagination on `GET /api/reviews` and metrics endpoints.
  - Add `POST /api/scrape` (accepts limit parameter) and `POST /api/analyze` spawning subprocess tasks.
  - Build `GET /api/export/csv` and ReportLab PDF layout generation under `GET /api/export/pdf`.
- **Checkpoint/Deliverables:**
  - 14 working backend endpoints accessible through Swagger UI (`/docs`).

### 18.7 Phase 8: RAG Chatbot Integration
- **Goal:** Ingest document collections into vector stores and construct the retriever-synthesis chat flow.
- **Key Tasks:**
  - Initialize ChromaDB persistently on disk under `backend/data/vectorstore`.
  - Build ingestion script (`scripts/ingest_reviews.py`) chunking and embedding documents via `nomic-embed-text`.
  - Establish Dual Partitioning: index App Store/Play Store to **Memory 1**, Reddit/Community threads to **Memory 2**.
  - Develop `retriever.py` querying both vector stores for top-K matches using metadata filters.
  - Set up `chat_service.py` to synthesize retrieved context and user query inside Prompt 3 to output citations.
- **Checkpoint/Deliverables:**
  - `POST /api/chat` returns grounded chatbot answers alongside structured citations and source references.

### 18.8 Phase 6: Frontend Dashboard
- **Goal:** Build the React Single Page Application utilizing Zustand, Recharts, Axios, and TanStack Table.
- **Key Tasks:**
  - Create global sidebar/header navigation shell with system status indicators.
  - Establish Zustand global store slices managing API fetching, filtering, and job status.
  - Build pages: Dashboard (metrics charts), Theme Explorer (treemaps, drilldown), Reviews Browser (paginated table), Segments Comparison, and Chat (premium chatbot UI).
- **Checkpoint/Deliverables:**
  - Responsive, high-fidelity UI communicating with backend services on Vercel/localhost.

### 18.9 Phase 7: Export, Deployment & Polish
- **Goal:** Polish ReportLab PDF formatting, set up CI/CD actions, write pytest cases, and deploy.
- **Key Tasks:**
  - Format PDF layouts with branded headers, page numbers, and custom pull-quotes.
  - Deploy backend to Render (with Ollama service support) and frontend to Vercel.
  - Write Actions workflow verifying pytest suites and triggering Vercel builds on push.
- **Checkpoint/Deliverables:**
  - Deployed, production-ready system with automated testing and CI/CD pipelines.

---

*This architecture document reflects the current implementation state. As the platform evolves, new data sources (Twitter/X, Mastodon), streaming analysis (SSE), and production deployment configurations should be documented here.*

---
**Owner:** Growth Engineering · **Status:** Living Document
