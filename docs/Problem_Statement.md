# AI-Powered Music Discovery Review Engine
## Product Specification & System Architecture
**Team:** Growth · **Role:** Product Manager · **Version:** 1.0  
**Date:** June 2026

---

## 1. Executive Summary

Spotify has mastered acquisition and retention but faces a compounding stagnation problem: users increasingly retreat into familiar listening loops rather than discovering new music. While our recommendation algorithms are technically sophisticated, the *perceived* discovery experience is broken in ways our internal metrics don't fully capture.

This document defines a **real-time, zero-storage AI review analysis system** that synthesises user feedback at scale — from App Store reviews, Reddit threads, community forums, and social media — to surface the precise friction points, behavioural patterns, and unmet needs preventing meaningful music discovery.

---

## 2. The Core Problem

> **Users have access to 100 million songs. Most listen to the same 50.**

This is not a catalogue problem. It is a **trust, friction, and intent-alignment problem** — and we cannot solve it without first understanding *why* it persists at the individual user level.

Internal data tells us *what* users do. User-generated feedback tells us *why* they feel the way they do. Today, this feedback is:

- Fragmented across dozens of platforms
- Manually reviewed at low volume
- Never synthesised in real time
- Not connected back to product decisions

The AI Review Discovery Engine closes this gap.

---

## 3. Strategic Goals

| Goal | Description |
|------|-------------|
| **Surface unmet needs** | Identify discovery frustrations not captured by behavioural data |
| **Segment by user type** | Distinguish casual listeners, power users, genre explorers, mood listeners |
| **Detect emerging signals** | Catch new friction patterns before they crystallise into churn |
| **Prioritise product bets** | Rank discovery feature investments by frequency and severity of user pain |
| **Operate in real time** | No data stored, no PII risk, analysis on-the-fly |

---

## 4. Research Questions This System Must Answer

### 4.1 Discovery Friction
- Why do users fail to engage with Discover Weekly, Radio, or AI DJ recommendations?
- At what point in the discovery flow do users abandon and return to familiar tracks?
- What language do users use to describe "bad" recommendations?

### 4.2 Recommendation Quality
- What are the most common frustrations with Spotify's recommendation system?
- How do users describe the difference between a recommendation that feels "right" vs "random"?
- Which recommendation surfaces (Radio, Blend, Discover Weekly, Mixes) generate the most complaints?

### 4.3 Listening Behaviour Intent
- What moods, contexts, and goals drive users toward repeat listening?
- When users want to discover, what are they actually seeking? (Similar artists? New genres? Specific energy?)
- How do users describe what they *wish* Spotify could do that it currently cannot?

### 4.4 Repetitive Listening Drivers
- What causes users to repeatedly listen to the same content?
- Is repeat listening driven by comfort, mistrust of recommendations, or lack of awareness of features?
- Do users know discovery features exist? If so, why don't they use them?

### 4.5 User Segment Differences
- How do discovery challenges differ between new users, long-term subscribers, free vs premium?
- Are there genre-specific discovery failures (e.g., classical, jazz, non-English music)?
- Do users in different markets describe discovery differently?

### 4.6 Unmet Needs
- What features do users explicitly request that do not yet exist?
- What competitor features are mentioned positively in Spotify reviews?
- What emotional language surrounds failed discovery attempts?

---

## 5. Data Sources

The system ingests from four primary public feedback surfaces. No authentication or data storage is required — all processing is ephemeral.

### 5.1 App Store Reviews (Apple)
- **Source:** Apple App Store public review API
- **Signal type:** Short-form sentiment, star ratings, specific feature callouts
- **Why valuable:** Captures casual users at a moment of strong emotion (frustration or delight)

### 5.2 Play Store Reviews (Google)
- **Source:** Google Play Store scraping (public data)
- **Signal type:** Similar to App Store but skews slightly different device/demographic
- **Why valuable:** Android users often have distinct behaviours and different feature exposure

### 5.3 Reddit Discussions
- **Source:** Reddit API (public posts and comments)
- **Subreddits:** r/spotify, r/music, r/ifyoulikeblank, r/musicrecommendations, r/listentothis
- **Signal type:** Long-form, nuanced, community-validated (upvotes signal consensus)
- **Why valuable:** Power users articulate sophisticated unmet needs; threads reveal feature awareness gaps

### 5.4 Community Forums
- **Source:** Spotify Community (community.spotify.com — public)
- **Signal type:** Feature requests, bug reports, use-case descriptions
- **Why valuable:** Structured, categorised feedback; "Idea Exchange" posts represent explicit product requests with vote counts

---

## 6. System Architecture

### 6.1 Principles
- **Real-time only:** All analysis occurs in-memory per request. Nothing is persisted.
- **Zero PII storage:** Usernames, handles, and identifiers are stripped before analysis.
- **Client-side query:** The user defines what they want to analyse; results are returned and discarded.
- **Stateless backend:** Each query is fully independent.

### 6.2 High-Level Data Flow & Prompts

The system splits preprocessing and analysis into two distinct parallel tracks depending on the text structure (individual reviews vs. discussion threads), feeds them through an LLM using internal prompts, and populates two separate Retrieval-Augmented Generation (RAG) memories.

```
       Play Store / App Store              Reddit / Spotify Community
             │                                     │
             ▼                                     ▼
┌───────────────────────────┐         ┌───────────────────────────┐
│     PRE-LLM Filters 1     │         │     PRE-LLM Filters 2     │
│  - Clean metadata         │         │  - Chunk each thread as   │
│  - Remove duplicates      │         │    a single chunk         │
│  - Remove only emojis     │         └────────────┬──────────────┘
│  - Remove < 20 chars      │                      │
│  - Remove non-English     │                      │
│  - Keyword density filter │                      │
│  - Chunking               │                      │
└────────────┬──────────────┘                      │
             │                                     │
             ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                           LLM ENGINE                            │
│                                                                 │
│  [Prompt 1: Internal]                                           │
│  - "Your review analysis system should help answer questions    │
│     such as..." (the 6 core research questions)                 │
│                                                                 │
│  [Prompt 2: Internal]                                           │
│  - "Make 2 rag memory, for each of the two data types from      │
│     each of the filters"                                        │
└────────────┬─────────────────────────────────────┬──────────────┘
             │                                     │
             ▼                                     ▼
┌───────────────────────────┐         ┌───────────────────────────┐
│         Memory 1          │         │         Memory 2          │
│   (Individual Reviews)    │         │    (Discussion Threads)   │
└────────────┬──────────────┘         └────────────┬──────────────┘
             │                                     │
             └─────────────────┬───────────────────┘
                               │ (Retrieved contexts)
                               ▼
                    ┌─────────────────────┐
                    │     User Prompt     │
                    │   for RAG Chatbot   │
                    └──────────┬──────────┘
                               │ 
                               ▼
                    ┌─────────────────────┐
                    │ [Prompt 3: Internal]│
                    │ Synthesizes prompt  │
                    │ & RAG memories      │
                    └──────────┬──────────┘
                               │ LLM
                               ▼
                    ┌─────────────────────┐
                    │   Chatbot Output    │
                    └─────────────────────┘
```

### 6.3 Prompt and Memory Taxonomy

#### 6.3.1 Prompt 1: Core Research System Prompt (Internal)
Instructs the LLM during review annotation:
> **Your review analysis system should help answer questions such as:**
> - Why do users struggle to discover new music?
> - What are the most common frustrations with recommendations?
> - What listening behaviors are users trying to achieve?
> - What causes users to repeatedly listen to the same content?
> - Which user segments experience different discovery challenges?
> - What unmet needs emerge consistently across reviews?

#### 6.3.2 Prompt 2: RAG Memory Partitioning Prompt (Internal)
Instructs the system to:
> **Make 2 rag memory, for each of the two data types from each of the filters**

Specifically, it partitions preprocessed data based on its source track pipeline:
- **Memory 1 (Individual Reviews):** Formed from App Store and Play Store reviews (PRE-LLM filters 1: clean metadata, remove duplicate, remove only emoji, remove <20 char, remove non-english, keyword density, chunking).
- **Memory 2 (Discussion Threads):** Formed from Reddit and Spotify Community forum threads (PRE-LLM filters 2: chunk each thread as one single chunk).

#### 6.3.3 Prompt 3: Chatbot Synthesis Prompt (Internal)
Acts as the final synthesis stage in the chatbot flow:
1. The **User Prompt for RAG Chatbot** queries both **Memory 1** (individual reviews) and **Memory 2** (discussion threads) in parallel.
2. The retrieved contexts from both memories and the original user prompt are combined into the **Prompt 3: internal** synthesis template.
3. This prompt is sent to the **LLM**, which outputs the final **Chatbot Output** with clear citations (e.g., `[Play Store #1]` vs `[Reddit #3]`).

---


## 7. Discovery Theme Taxonomy

The AI classifies all feedback against the following taxonomy. This taxonomy should be editable in the web app UI.

### 7.1 Algorithmic Trust
- Recommendations feel random or irrelevant
- Algorithm feels "broken" after skipping or disliking
- Recommendations too similar to what user already knows
- Recommendations too foreign / not understanding taste

### 7.2 Feature Awareness
- User unaware discovery features exist
- User tried feature once, didn't like result, never returned
- Feature is hard to find in navigation
- Feature exists but workflow is unintuitive

### 7.3 Control & Customisation
- Cannot tell Spotify "more like this" meaningfully
- Cannot tell Spotify "never play this again" at genre level
- No way to express mood or context intent
- Playlist curation feels out of user control

### 7.4 Discovery Fatigue
- Too many recommendations, paralysis of choice
- Not enough time/energy to vet recommendations
- Discovery requires too much active effort
- Passive listening defaults to familiar because it's "safe"

### 7.5 Context Mismatch
- Recommendations ignore time of day / activity context
- Workout recommendations feel wrong
- Focus/work playlists feel generic
- Social / party context not well served

### 7.6 Taste Evolution
- Algorithm stuck on who user was, not who they are now
- Holiday/travel listening permanently "corrupts" recommendations
- Can't separate different moods or personas within one account
- Family/shared account pollutes individual taste model

### 7.7 Competitive Gaps
- Apple Music Radio mentioned positively
- YouTube rabbit-hole discovery mentioned positively
- Bandcamp / SoundCloud for niche discovery mentioned
- AI DJ compared unfavourably to competitors

---

## 8. Web App Feature Specification

### 8.1 Core Views

**Query Builder**
- Input: Topic / question to investigate (free text)
- Source selector: Toggle which platforms to include
- Date range: Last 7 / 30 / 90 days (affects API query window)
- Segment filter: Focus on specific user type signals

**Results Dashboard**
- Theme breakdown (ranked by frequency)
- Sentiment distribution per theme
- Representative quote panel (verbatim, anonymised)
- Unmet needs list (extracted and ranked)
- Competitive mentions tracker
- Anomaly alerts (themes spiking vs. baseline)

**Insight Narrative**
- AI-generated executive summary of findings
- "Top 3 things we learned" synthesis
- Suggested product hypotheses generated from findings

### 8.2 Real-Time Constraints

| Constraint | Approach |
|-----------|---------|
| No data storage | All state lives in browser session only |
| No PII | Strip before sending to AI; never log usernames |
| Rate limiting | Queue requests; show progress indicators |
| API cost control | Batch reviews before AI calls; summarise first, then analyse |
| Latency | Show progressive results as sources complete, not all-at-once |

### 8.3 Technology Recommendations

**Frontend**
- React (component-driven dashboard)
- Tailwind CSS (rapid UI development)
- Recharts or D3 (theme frequency visualisation)

**Backend / API Layer**
- Node.js or Python (FastAPI)
- Parallel fetch across sources using Promise.all / asyncio
- Claude API (Anthropic) as the AI analysis engine
- Server-sent events (SSE) for progressive result streaming

**Data Fetching**
- Reddit: Official Reddit API (free, public)
- App Store: apple-app-store-scraper (npm) or equivalent
- Play Store: google-play-scraper (npm)
- Spotify Community: Public HTTP scraping
- Social: Twitter/X v2 API (public search endpoint)

---

## 9. Prioritisation Framework for Insights

Not all themes are equal. The system should score each theme using:

```
Insight Priority Score =
  (Frequency × 0.4) +
  (Emotional Intensity × 0.3) +
  (Specificity × 0.2) +
  (Competitive Risk × 0.1)
```

**Frequency** — How often does this theme appear across sources?  
**Emotional Intensity** — How strong is the frustration/delight signal?  
**Specificity** — Is this actionable, or too vague to build against?  
**Competitive Risk** — Does this theme reference a competitor doing it better?

Themes scoring above 0.7 surface as **Critical Insights** in the dashboard.

---

## 10. Hypotheses to Validate

The system should be designed to test — and update — the following product hypotheses:

| # | Hypothesis |
|---|-----------|
| H1 | Users who engage with Discover Weekly in their first 30 days have higher 12-month retention |
| H2 | The primary driver of repeat listening is mistrust of AI recommendations, not preference for familiarity |
| H3 | Discovery failure is disproportionately reported by users with diverse taste profiles (multi-genre listeners) |
| H4 | Users do not know they can influence their taste profile; they assume the algorithm is fixed |
| H5 | Collaborative/social discovery is an underserved need that competitors are not fully addressing either |
| H6 | Context-aware recommendations (activity, time, mood) are the most consistently requested missing feature |

---

## 11. Privacy & Ethics

- **No user data is stored** at any point in the pipeline
- All usernames and handles are **stripped in pre-processing** before AI analysis
- The system analyses **themes and patterns**, never individuals
- No review content is logged, cached, or retained beyond the active session
- The system operates on **publicly available data only**
- No authentication is performed on behalf of any user

---

## 12. Success Metrics for the System Itself

| Metric | Target |
|--------|--------|
| Analysis latency (first result) | < 8 seconds |
| Theme extraction accuracy | > 85% vs. manual review |
| Coverage (reviews processed per query) | 200–500 reviews |
| Novel theme detection rate | At least 1 new theme per 50 queries |
| PM time-to-insight vs. manual | 10× faster |

---

## 13. What This System Is NOT

To maintain focus, the following are explicitly out of scope:

- **Not a social listening platform** (no competitive benchmarking vs. Apple Music at scale)
- **Not a quantitative analytics tool** (does not replace internal Spotify data / Looker dashboards)
- **Not a review management tool** (no response to reviews, no ticketing integration)
- **Not a longitudinal tracker** (no stored baselines, no trend-over-time charts)
- **Not an ML training pipeline** (outputs are insights for humans, not model training data)

---

## 14. Immediate Next Steps

1. **Confirm API access** — Validate Reddit API key, App Store scraper, Twitter/X API tier
2. **Build source fetchers** — Parallel, rate-limited fetchers for all 5 sources
3. **Design pre-processing** — PII strip, language filter, deduplication logic
4. **Prompt engineering** — Develop and test AI analysis prompt against real review batches
5. **Build MVP dashboard** — Theme frequency chart, quote panel, unmet needs list
6. **Internal pilot** — Run against 500 recent Spotify reviews; validate theme taxonomy
7. **PM workflow test** — Answer all 6 research questions from Section 4 using the tool

---

*This document is a living specification. As the web app is built and tested, the taxonomy, scoring model, and source list should be iterated based on what generates the most actionable insights.*

---
**Owner:** Growth PM · **Status:** Ready for Engineering Handoff
