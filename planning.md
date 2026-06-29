Provenance Guard: A backend api that can be used by creative sharing platforms to determine if text posts are written by AI or humans.

features:
    content submission endpoint: text based content. return structured response with attribution result, confidence score, transparency label

    multi-signal detection pipeline: 2 signals minimum

    confidence scoring with uncertainty: confidence score instead of binary label

    transparency label: label that would be displayed to reader on the platform. Communicate the attribution result in plain language and make the confidene level meaningful to a non-technical reader.
        typed description of all three label variants (high-confidence AI,, high-confidence human, uncertain)

        all text for each of these in readme

    appeals workflow: at minimum capture creator's reasoning, log the appeal alongside the original decision, update the content's status to under review. Don't need automated re-classification

    rate limiting: rate limiting on the endpoint. README documents the limits and reasoning

    audit log: Every decision including confidence score, signals used, and any appeals. Muse go into a structured audit log. document log in readme or GET /log output witha t least 3 entries visible


Detection signals:
    LLM-based classification: assess whether text reads as human or AI-generated. Check for semantic and stylistic coherence.

        can detect: style, semantics, and coherence.

        cannot detect: framing that leads to bias, structure.

    Stylometric heuristics: measure statistical properties that differ between human and AI writing. Things like sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity.

        can detect: sentence length variance, type-token ratio, punctuation density

        can't detect: meaning

transparency labels: 

    high-confidence AI: Our AI has determined this post to be AI with a high confidence level ([%])
    high-confidence human: Our AI detection system has determined this post to be human-made with a high confidence level([%])
    uncertain: Our AI detection system was unable to determine if this post was AI. confidence level [%]
    
false positive problem: confidence score should hopefully make it easier for an admin to determine a potential false positive.

---

## API Specification

**Version:** 0.1 (draft)  
**Base URL:** `http://localhost:8000` (development)  
**Format:** All requests and responses are `application/json`.

### Authentication

> **[ DECISION ]** How should the API authenticate callers?
> - Option A: Static API key in `Authorization: Bearer <key>` header
> - Option B: No auth (rate limiting by IP only, suitable for internal/demo use)
> - Option C: _______________

### Rate Limiting

Rate limiting applies to `POST /analyze`. Read endpoints (`GET /audit/log`) are not rate-limited.

| Endpoint        | Limit                        | Window   |
|-----------------|------------------------------|----------|
| `POST /analyze` | **[ DECISION: e.g. 60 ]** requests | per minute |
| `POST /appeals` | **[ DECISION: e.g. 10 ]** requests | per minute |

Limits are enforced per **[ DECISION: IP address / API key / both ]**.

When a limit is exceeded the API returns `429 Too Many Requests` with a `Retry-After` header indicating seconds until the window resets.

**Rationale:** `POST /analyze` is the computationally expensive path (LLM call + stylometric computation). Stricter limits here protect backend resources and prevent abuse of the classification pipeline.

### Confidence Thresholds

The raw confidence score (0.0–1.0) maps to a label variant as follows:

| Score range | Label variant |
|---|---|
| ≥ **[ DECISION: e.g. 0.75 ]** and attribution = `ai` | `high_confidence_ai` |
| ≥ **[ DECISION: same threshold ]** and attribution = `human` | `high_confidence_human` |
| < threshold (either direction) | `uncertain` |

### Signal Weights

| Signal | Weight | What it detects | What it cannot detect |
|---|---|---|---|
| `llm_classification` | **[ DECISION: e.g. 0.60 ]** | Style, semantics, coherence | Framing bias, structure |
| `stylometric` | **[ DECISION: e.g. 0.40 ]** | Sentence length variance, type-token ratio, punctuation density | Meaning |

> **[ DECISION ]** Should signal weights be hardcoded or configurable at request time?

### Endpoints

#### `POST /analyze`

Submit text content for AI/human attribution analysis.

**Request body**

```json
{
  "text": "string (required)",
  "content_id": "string (optional)"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | The text content to analyze. |
| `content_id` | string | No | Caller-provided identifier for idempotency. If omitted, the API mints a UUID. If provided and already seen, **[ DECISION: return the cached result / re-run and overwrite / return 409 Conflict ]**. |

**Response `200 OK`**

```json
{
  "content_id": "uuid",
  "attribution": "ai | human | uncertain",
  "confidence_score": 0.87,
  "transparency_label": {
    "variant": "high_confidence_ai | high_confidence_human | uncertain",
    "display_text": "Our AI detection system has determined this post to be AI-generated with a high confidence level (87%)."
  },
  "signals": {
    "llm_classification": {
      "result": "ai | human",
      "weight": 0.6
    },
    "stylometric": {
      "result": "ai | human",
      "sentence_length_variance": 12.3,
      "type_token_ratio": 0.42,
      "punctuation_density": 0.08,
      "weight": 0.4
    }
  },
  "analyzed_at": "2026-06-28T12:00:00Z"
}
```

**Error responses**

| Status | Condition |
|---|---|
| `400 Bad Request` | `text` is missing or empty |
| `422 Unprocessable Entity` | `text` is too short to analyze (below minimum length) |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Detection pipeline failure |

> **[ DECISION ]** Minimum text length to accept? (e.g., 50 characters, 20 words). Below this threshold classification is unreliable.

#### `POST /appeals`

Capture a creator's dispute against a prior attribution decision. Does not trigger automated re-classification. Sets the content status to `under_review`.

**Request body**

```json
{
  "content_id": "uuid (required)",
  "creator_reasoning": "string (required)"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `content_id` | string | Yes | The UUID returned by `POST /analyze`. |
| `creator_reasoning` | string | Yes | The creator's explanation of why the decision is incorrect. |

**Response `201 Created`**

```json
{
  "appeal_id": "uuid",
  "content_id": "uuid",
  "status": "under_review",
  "logged_at": "2026-06-28T12:05:00Z"
}
```

**Error responses**

| Status | Condition |
|---|---|
| `400 Bad Request` | Missing required fields |
| `404 Not Found` | `content_id` does not exist |
| `409 Conflict` | **[ DECISION ]** A prior appeal already exists for this `content_id`. Options: reject with 409, allow stacking (multiple appeals logged), overwrite. |

#### `GET /audit/log`

Returns a paginated list of all audit log entries — every analysis decision and every appeal.

**Query parameters**

| Param | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 50 | Max entries to return. |
| `offset` | integer | 0 | Pagination offset. |
| `content_id` | string | — | Filter to a single piece of content. |
| `event_type` | string | — | Filter to `analysis` or `appeal`. |

**Response `200 OK`**

```json
{
  "total": 142,
  "limit": 50,
  "offset": 0,
  "entries": [
    {
      "entry_id": "uuid",
      "content_id": "uuid",
      "event_type": "analysis | appeal",
      "attribution": "ai | human | uncertain",
      "confidence_score": 0.87,
      "signals_used": ["llm_classification", "stylometric"],
      "appeal": {
        "appeal_id": "uuid",
        "reasoning": "I wrote this myself.",
        "status": "under_review"
      },
      "timestamp": "2026-06-28T12:00:00Z"
    }
  ]
}
```

`appeal` is `null` on entries where `event_type` is `analysis` and no appeal has been filed.

### Data Models

#### `AttributionResult`

```
"ai" | "human" | "uncertain"
```

#### `LabelVariant`

```
"high_confidence_ai" | "high_confidence_human" | "uncertain"
```

#### `ContentStatus`

```
"decided" | "under_review"
```

#### `AuditEntry`

| Field | Type | Description |
|---|---|---|
| `entry_id` | UUID | Unique log entry identifier |
| `content_id` | UUID | The analyzed content |
| `event_type` | string | `analysis` or `appeal` |
| `attribution` | AttributionResult | Final attribution |
| `confidence_score` | float [0.0–1.0] | Weighted signal aggregate |
| `signals_used` | string[] | Names of signals that ran |
| `appeal` | object or null | Appeal detail if one exists |
| `timestamp` | ISO 8601 | When this entry was created |

### Open Decisions Summary

| # | Decision | Options |
|---|---|---|
| 1 | Authentication scheme | API key / no auth / other |
| 2 | Rate limit — `/analyze` req/min | e.g. 60 |
| 3 | Rate limit — `/appeals` req/min | e.g. 10 |
| 4 | Rate limit granularity | IP / API key / both |
| 5 | Confidence threshold for "high-confidence" | e.g. 0.75 |
| 6 | Signal weights (LLM vs stylometric) | e.g. 0.60 / 0.40 |
| 7 | Signal weights configurable at request time? | Yes / No (hardcoded) |
| 8 | Duplicate `content_id` behavior | Cache / re-run / 409 |
| 9 | Minimum text length | e.g. 50 chars / 20 words |
| 10 | Multiple appeals on same `content_id` | Stack / overwrite / 409 |

---

## Architecture

### Submission flow

```
Client
  |  POST /analyze · { text }
  v
/analyze Endpoint
  |              |
  | raw text     | raw text
  v              v
LLM            Stylometric
Classification  Analysis
  |              |
  | { result,    | { metrics,
  |   llm_score }|   style_score }
  +------+-------+
         |
         v
   Confidence Scorer
         |                    |
         | { attribution,     | { attribution,
         |   combined_score } |   combined_score,
         v                    |   signals }
  Transparency Label          v
    Generator            Audit Log
         |                    |
         | { variant,         | entry_id
         |   display_text }   |
         +--------+-----------+
                  |
                  v
           Response Builder
                  |
                  v
  200 OK · { content_id, attribution,
             confidence_score, label, signals }
```

### Appeal flow

```
Client
  |  POST /appeals · { content_id, creator_reasoning }
  v
/appeals Endpoint
  |
  | content_id
  v
Content Status Updater
  |
  | status: under_review
  v
/appeals Endpoint
  |
  | { content_id, reasoning, status: under_review }
  v
Audit Log
  |
  | { appeal_id, logged_at }
  v
Response Builder
  |
  v
201 Created · { appeal_id, content_id, status, logged_at }
```

### Narrative

The submission flow runs both detection signals in parallel against the raw text, then merges their weighted scores in the Confidence Scorer before passing the combined result downstream. The Transparency Label Generator and Audit Log both receive the scorer's output independently, so the audit record is written before the response is assembled. The appeal flow is deliberately thin: it updates the content's status to `under_review`, writes a log entry alongside the original decision, and returns immediately — no re-classification is triggered.

---

## AI Tool Plan

### M3 — Submission endpoint + first signal (LLM classification)

**Spec sections to provide:** Detection Signals (LLM classification entry), the `POST /analyze` endpoint definition from spec.md, and the Submission flow diagram above.

**What to ask the AI tool to generate:**
- A Flask app skeleton with a single `POST /analyze` route that accepts `{ text }` and returns the full response shape defined in spec.md
- A `classify_with_llm(text: str) -> dict` function that calls the Claude API, prompts it to assess whether the text reads as human or AI-generated, and returns `{ result: "ai"|"human", llm_score: float }`

**How to verify before wiring in:**
- Call `classify_with_llm()` directly in a Python REPL on 3–4 test inputs (a clearly AI-sounding excerpt, a clearly human one, and an ambiguous one)
- Confirm the return shape matches the spec and that scores are not uniformly the same value
- Only wire into the route once the function behaves correctly in isolation

---

### M4 — Second signal + confidence scoring

**Spec sections to provide:** Detection Signals (Stylometric heuristics entry), Confidence Thresholds section from spec.md, and the Submission flow diagram above.

**What to ask the AI tool to generate:**
- A `classify_with_stylometrics(text: str) -> dict` function that computes sentence length variance, type-token ratio, and punctuation density and returns `{ result: "ai"|"human", metrics: {...}, style_score: float }`
- A `compute_confidence(llm_result: dict, stylo_result: dict) -> dict` function that combines the two scores via weighted average and returns `{ attribution: "ai"|"human"|"uncertain", combined_score: float }`

**What to check:**
- Run both signals and the scorer against the same 3–4 test inputs from M3
- Confirm the combined score varies meaningfully between clearly AI and clearly human samples (not collapsing toward 0.5 on everything)
- Confirm that borderline inputs produce `uncertain` rather than a confident wrong answer

---

### M5 — Production layer (labels, appeals, audit log)

**Spec sections to provide:** Transparency Labels section, Appeals endpoint definition, Audit Log endpoint definition, and both flow diagrams above.

**What to ask the AI tool to generate:**
- A `generate_label(attribution: str, combined_score: float) -> dict` function that maps scorer output to the correct label variant and fills in the display text template with the rounded percentage
- The `POST /appeals` route: validates `content_id` exists, updates its status to `under_review`, writes an audit entry, and returns `201 Created`
- The `GET /audit/log` route with `limit`, `offset`, and `content_id` filter params

**How to verify:**
- Craft test inputs that force all three label variants (`high_confidence_ai`, `high_confidence_human`, `uncertain`) and confirm the correct display text is returned for each
- Submit an appeal for a known `content_id` and check that the status field updates and the audit log entry appears alongside the original analysis entry
- Hit `GET /audit/log` and confirm at least 3 entries are visible with the full fields defined in spec.md