# Claude Batch Processing — Reference Manual

Version 1.0 — March 2026
Covers: API lifecycle, schema, pricing, prompt caching, error handling, bootstrap scripts.

---

## 1. Overview

The Message Batches API processes large volumes of Claude Messages requests asynchronously. Requests are submitted in a single batch and processed concurrently. Results are available when all requests complete or after 24 hours, whichever comes first.

### 1.1 When to Use Batch Processing

- Large-scale evaluations (thousands of test cases)
- Content moderation over user-generated datasets
- Bulk classification, extraction, or summarization
- Any workload where real-time response is not required

### 1.2 Key Properties

| Property | Value |
|----------|-------|
| Cost | 50% of standard API prices |
| Max requests per batch | 100,000 |
| Max payload size | 256 MB |
| Processing SLA | 24 hours (most complete in < 1 hour) |
| Result availability | 29 days from batch creation |
| Scope | Workspace-isolated |
| ZDR eligibility | Not eligible |

---

## 2. API Lifecycle

The batch lifecycle follows a strict state machine with explicit transitions. There is no implicit behavior.

### 2.1 State Machine

```
                     ┌─────────────┐
         POST create │             │
        ────────────▶│ in_progress │
                     │             │
                     └──────┬──────┘
                            │
               ┌────────────┼────────────┐
               │ all requests resolved   │ POST cancel
               ▼                         ▼
        ┌────────────┐          ┌─────────────┐
        │   ended    │◀─────── │  canceling   │
        │ (terminal) │ drain   │              │
        └────────────┘         └──────────────┘
```

| State | Meaning | Transitions To |
|-------|---------|----------------|
| `in_progress` | Batch created, requests being processed | `ended`, `canceling` |
| `canceling` | Cancel requested, draining in-flight requests | `ended` |
| `ended` | All requests resolved (success/error/cancel/expire) | Terminal |

### 2.2 Request Result Types

Each request within a batch resolves to exactly one of four terminal states:

| Result | Description | Billed |
|--------|-------------|--------|
| `succeeded` | Request completed, message returned | Yes |
| `errored` | Validation or server error, no message | No |
| `canceled` | Batch canceled before request was sent | No |
| `expired` | 24h elapsed before request was sent | No |

### 2.3 Pipeline Steps

1. **Prepare** — Build the payload (validate inputs, enforce uniqueness of `custom_id`)
2. **Submit** — POST to `/v1/messages/batches`, receive batch ID
3. **Poll** — GET batch status until `processing_status == "ended"`
4. **Fetch** — Stream results from `results_url` as JSONL

Optional: **Cancel** — POST to `/v1/messages/batches/{id}/cancel` at any time before completion.

---

## 3. Endpoints

| Operation | Method | Path |
|-----------|--------|------|
| Create batch | POST | `/v1/messages/batches` |
| Retrieve batch | GET | `/v1/messages/batches/{batch_id}` |
| List batches | GET | `/v1/messages/batches` |
| Retrieve results | GET | `{results_url}` (from batch object) |
| Cancel batch | POST | `/v1/messages/batches/{batch_id}/cancel` |

All endpoints require headers:

```
x-api-key: $ANTHROPIC_API_KEY
anthropic-version: 2023-06-01
content-type: application/json  (POST only)
```

---

## 4. Pricing

All batch usage is billed at 50% of standard API prices. Errored, canceled, and expired requests are not billed.

| Model | Batch Input / MTok | Batch Output / MTok |
|-------|--------------------|---------------------|
| Claude Opus 4.6 | $2.50 | $12.50 |
| Claude Opus 4.5 | $2.50 | $12.50 |
| Claude Opus 4.1 | $7.50 | $37.50 |
| Claude Opus 4 | $7.50 | $37.50 |
| Claude Sonnet 4.6 | $1.50 | $7.50 |
| Claude Sonnet 4.5 | $1.50 | $7.50 |
| Claude Sonnet 4 | $1.50 | $7.50 |
| Claude Haiku 4.5 | $0.50 | $2.50 |
| Claude Haiku 3.5 | $0.40 | $2.00 |
| Claude Haiku 3 | $0.125 | $0.625 |

### 4.1 Cost Stacking with Prompt Caching

Prompt caching discounts stack with batch pricing:

| Token Type | Standard | Batch (50%) | Batch + Cache Read (5%) | Batch + Cache Write (125%) |
|------------|----------|-------------|-------------------------|----------------------------|
| Input | 1.0x | 0.5x | 0.05x | 0.625x |

Cache hits in batches are best-effort. Typical hit rates: 30–98% depending on traffic patterns.

---

## 5. Prompt Caching in Batches

To use prompt caching, include identical `cache_control` blocks in every request in the batch. The shared content (typically a system prompt or large reference document) is marked with `cache_control: {"type": "ephemeral"}`.

### 5.1 Maximizing Cache Hits

1. Use identical `cache_control` blocks across all requests in the batch.
2. Use the 1-hour cache duration (TTL) for better hit rates on batches taking > 5 minutes.
3. Place cacheable content at the start of the system prompt; variable content after.
4. The prepare script (`01_prepare_batch.py`) supports `--cache` flag for this.

### 5.2 Example: Cached System Prompt

```json
{
  "custom_id": "req-001",
  "params": {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": [
      {
        "type": "text",
        "text": "You are an analyst. <large reference document here>",
        "cache_control": {"type": "ephemeral"}
      }
    ],
    "messages": [
      {"role": "user", "content": "Summarize section 3."}
    ]
  }
}
```

Every request in the batch must include the identical system block for cache hits.

---

## 6. Supported Features in Batches

Any valid Messages API request can be batched:

- Vision (image content blocks)
- Tool use (function calling)
- System messages (with or without caching)
- Multi-turn conversations
- Extended thinking
- Beta features

Different request types can be mixed within a single batch.

---

## 7. Bootstrap Scripts Reference

The bootstrap package includes five scripts forming an explicit pipeline. Each reads from and writes to well-defined files. There is no hidden state.

### 7.1 Data Flow

```
input.jsonl
    │
    ▼
01_prepare_batch.py  ──▶  batch_payload.json
    │
    ▼
02_submit_batch.py   ──▶  batch_state.json
    │
    ▼
03_poll_status.py    ──▶  batch_state.json (updated)
    │
    ▼
04_fetch_results.py  ──▶  results.jsonl
```

### 7.2 01_prepare_batch.py

Transforms a simplified input JSONL into the full API payload. Validates unique `custom_id` values, enforces size limits (100K requests, 256 MB), and optionally attaches a shared system prompt with caching.

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | (required) | Path to input JSONL |
| `--output` | `batch_payload.json` | Output payload path |
| `--model` | `claude-sonnet-4-5` | Model identifier |
| `--max-tokens` | `1024` | Max tokens per response |
| `--system` | None | Path to shared system prompt file |
| `--cache` | False | Enable prompt caching on system prompt |

### 7.3 02_submit_batch.py

Reads the prepared payload, submits to the API via the Python SDK, and writes `batch_state.json` with the batch ID and metadata.

| Flag | Default | Description |
|------|---------|-------------|
| `--payload` | `batch_payload.json` | Path to prepared payload |
| `--state` | `batch_state.json` | Output state file |

### 7.4 03_poll_status.py

Polls the batch status at a configurable interval. Updates `batch_state.json` when processing ends. Exits with error code on timeout.

| Flag | Default | Description |
|------|---------|-------------|
| `--state` | `batch_state.json` | Path to batch state file |
| `--interval` | `30` | Polling interval (seconds) |
| `--timeout` | `86400` | Max wait time (seconds) |

### 7.5 04_fetch_results.py

Streams results from the API and writes a flattened JSONL. Each output line contains: `custom_id`, `status`, `text` (if succeeded), `model`, `stop_reason`, `input_tokens`, `output_tokens`, and `error` (if errored).

| Flag | Default | Description |
|------|---------|-------------|
| `--state` | `batch_state.json` | Path to batch state file |
| `--output` | `results.jsonl` | Output JSONL file |

### 7.6 05_cancel_batch.py

Cancels an in-flight batch. Accepts either `--state` (reads `batch_id` from file) or `--batch-id` (direct override). Updates state file.

| Flag | Default | Description |
|------|---------|-------------|
| `--state` | `batch_state.json` | Path to batch state file |
| `--batch-id` | None | Override: cancel this batch ID directly |

---

## 8. Input Format

The input JSONL file (`examples/input.jsonl`) uses a simplified schema. Each line:

```json
{"custom_id": "task-001", "prompt": "Your user message here"}
```

| Field | Type | Rule |
|-------|------|------|
| `custom_id` | string | Must be unique across the batch |
| `prompt` | string | The user message content |

The prepare script wraps these into the full API schema, adding model, max_tokens, and optional system prompt.

---

## 9. Error Handling

### 9.1 Validation Errors

Parameter validation is asynchronous. Invalid requests in a batch are reported as `errored` results after the batch ends, not at submission time. Always dry-run a sample request against the synchronous Messages API before batching.

### 9.2 Result Error Types

| Error Type | Meaning | Action |
|------------|---------|--------|
| `invalid_request` | Malformed params (bad model, schema violation) | Fix request body, resubmit |
| `server_error` | Transient internal error | Retry request directly |

### 9.3 HTTP-Level Errors

| Code | Meaning |
|------|---------|
| 413 | Payload exceeds 256 MB |
| 429 | Rate limit (batch creation or queued requests) |
| 401 | Invalid or missing API key |

The failure of one request in a batch does not affect processing of other requests.

---

## 10. Best Practices

### 10.1 Naming

Use structured `custom_id` values that encode task type and sequence: `classify-001`, `summarize-042`, `extract-017`. This makes result matching and error triage deterministic.

### 10.2 Validation

Always dry-run at least one request against the synchronous Messages API before submitting a batch. Batch validation is asynchronous; errors surface only after full processing.

### 10.3 Chunking

For datasets larger than 100,000 requests, split into multiple batches. Each batch operates independently. Design your `custom_id` scheme to include a batch prefix for traceability.

### 10.4 Retry Strategy

For `errored` results with `server_error` type, resubmit the request in a new batch. For `invalid_request` errors, fix the params before resubmitting. Expired requests can be retried directly.

### 10.5 Monitoring

Poll at reasonable intervals (30–60 seconds). The `request_counts` object on the batch shows real-time progress across all five states: `processing`, `succeeded`, `errored`, `canceled`, `expired`.

---

## 11. Governance and Isolation

### 11.1 Workspace Scope

Batches are scoped to the Workspace of the API key that created them. No cross-workspace access. Batch results are visible in the Console to users with appropriate Workspace permissions.

### 11.2 Data Retention

Results are available for 29 days from batch creation (not from processing end). After that, batch metadata remains visible but results are no longer downloadable.

### 11.3 Rate Limits

Batch API rate limits are separate from standard Messages API rate limits. Batch creation and queued request counts have their own limits. Processing may slow under high demand; excess requests expire after 24 hours.

---

## 12. Reference Links

| Resource | URL |
|----------|-----|
| Batch Processing Guide | `platform.claude.com/docs/en/build-with-claude/batch-processing` |
| Create Batch API | `platform.claude.com/docs/en/api/creating-message-batches` |
| Retrieve Batch API | `platform.claude.com/docs/en/api/retrieving-message-batches` |
| List Batches API | `platform.claude.com/docs/en/api/listing-message-batches` |
| Cancel Batch API | `platform.claude.com/docs/en/api/canceling-message-batches` |
| Batch Results API | `platform.claude.com/docs/en/api/retrieving-message-batch-results` |
| Pricing | `platform.claude.com/docs/en/about-claude/pricing` |
| Rate Limits | `platform.claude.com/docs/en/api/rate-limits` |
| Prompt Caching | `platform.claude.com/docs/en/build-with-claude/prompt-caching` |
