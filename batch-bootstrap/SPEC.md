# Claude Batch Processing — Technical Specification

Version 1.0 — March 2026
Classification: Technical reference. Not a tutorial.

---

## S1. Scope

This specification defines the contract between a client and the Anthropic Message Batches API (`/v1/messages/batches`). It covers request/response schemas, state transitions, invariants, error taxonomy, and the contracts of the bootstrap scripts shipped with this package.

Where this document and the MANUAL.md overlap, this document is authoritative on formal constraints; the manual is authoritative on usage guidance.

---

## S2. Definitions

| Term | Definition |
|------|-----------|
| **Batch** | An immutable collection of 1–100,000 Message requests submitted as a single unit. |
| **Request** | A single Messages API call within a batch, identified by `custom_id`. |
| **Result** | The terminal outcome of a request: `succeeded`, `errored`, `canceled`, or `expired`. |
| **Workspace** | An Anthropic organizational unit that scopes API keys, batches, and billing. |
| **Processing** | The period between batch creation and batch end during which requests are executed. |
| **Payload** | The JSON body submitted to `POST /v1/messages/batches`. |
| **State file** | `batch_state.json` — the local file carrying batch ID and status between pipeline stages. |
| **MTok** | One million tokens. Billing unit. |

---

## S3. API Contract

### S3.1 Base URL

```
https://api.anthropic.com/v1/messages/batches
```

### S3.2 Authentication

All requests MUST include:

```
x-api-key: <ANTHROPIC_API_KEY>
anthropic-version: 2023-06-01
```

The API key MUST belong to the Workspace that owns the batch. Cross-workspace access is prohibited.

### S3.3 Endpoints

| ID | Method | Path | Idempotent | Body |
|----|--------|------|------------|------|
| E1 | POST | `/v1/messages/batches` | No | `BatchCreateRequest` |
| E2 | GET | `/v1/messages/batches/{batch_id}` | Yes | None |
| E3 | GET | `/v1/messages/batches` | Yes | None (query params) |
| E4 | GET | `{results_url}` | Yes | None |
| E5 | POST | `/v1/messages/batches/{batch_id}/cancel` | Yes | None |

---

## S4. Schema Definitions

### S4.1 BatchCreateRequest

```
BatchCreateRequest {
  requests: BatchRequestItem[1..100000]
}
```

Constraint: `sizeof(JSON(BatchCreateRequest)) <= 256 MB`.

### S4.2 BatchRequestItem

```
BatchRequestItem {
  custom_id: string        // REQUIRED. Unique within batch.
  params:    MessageParams  // REQUIRED. Standard Messages API parameters.
}
```

**Invariant:** For all items `i`, `j` in `requests`: `i.custom_id != j.custom_id` when `i != j`.

### S4.3 MessageParams

```
MessageParams {
  model:      string                 // REQUIRED. Active model identifier.
  max_tokens: integer                // REQUIRED. >= 1.
  messages:   MessageBlock[]         // REQUIRED. Non-empty.
  system:     SystemBlock[]          // OPTIONAL.
  tools:      ToolDefinition[]       // OPTIONAL.
  metadata:   object                 // OPTIONAL.
  stop_sequences: string[]           // OPTIONAL.
  temperature:    float              // OPTIONAL. [0.0, 1.0].
  top_p:          float              // OPTIONAL. (0.0, 1.0).
  top_k:          integer            // OPTIONAL. >= 1.
}
```

`MessageParams` accepts any field valid in a synchronous `POST /v1/messages` request. Validation is **asynchronous** — invalid params produce `errored` results, not submission-time errors.

### S4.4 SystemBlock (with optional caching)

```
SystemBlock {
  type:          "text"              // REQUIRED.
  text:          string              // REQUIRED.
  cache_control: CacheControl        // OPTIONAL.
}

CacheControl {
  type: "ephemeral"                  // REQUIRED if present.
}
```

### S4.5 Batch (response object)

```
Batch {
  id:                  string        // Format: "msgbatch_..."
  type:                "message_batch"
  processing_status:   ProcessingStatus
  request_counts:      RequestCounts
  created_at:          string        // RFC 3339
  expires_at:          string        // RFC 3339. created_at + 24h.
  ended_at:            string | null // RFC 3339. Set when status == "ended".
  cancel_initiated_at: string | null // RFC 3339. Set when cancel requested.
  results_url:         string | null // Set when status == "ended".
}

ProcessingStatus = "in_progress" | "canceling" | "ended"

RequestCounts {
  processing: integer  // >= 0
  succeeded:  integer  // >= 0
  errored:    integer  // >= 0
  canceled:   integer  // >= 0
  expired:    integer  // >= 0
}
```

**Invariant:** `processing + succeeded + errored + canceled + expired == len(requests)` at all times.

**Invariant:** When `processing_status == "ended"`: `processing == 0`.

### S4.6 BatchResultItem (JSONL record)

```
BatchResultItem {
  custom_id: string
  result:    ResultVariant
}

ResultVariant =
  | { type: "succeeded", message: Message }
  | { type: "errored",   error:   APIError }
  | { type: "canceled" }
  | { type: "expired" }
```

`Message` conforms to the standard Messages API response schema.

`APIError` conforms to the standard error shape:

```
APIError {
  type:    "invalid_request_error" | "api_error"
  message: string
}
```

### S4.7 Result JSONL File

- Format: newline-delimited JSON. Each line is a valid `BatchResultItem`.
- Ordering: **unspecified**. Results MAY appear in any order.
- Encoding: UTF-8.
- Availability: 29 days from `created_at`.

---

## S5. State Machine — Formal Definition

### S5.1 States

```
S = { in_progress, canceling, ended }
```

### S5.2 Initial State

```
s₀ = in_progress
```

### S5.3 Transitions

```
T1: in_progress → ended       [all requests resolved]
T2: in_progress → canceling   [cancel requested via E5]
T3: canceling   → ended       [all in-flight requests drained]
```

### S5.4 Terminal State

```
S_terminal = { ended }
```

No transitions exist from `ended`. The state is permanent.

### S5.5 Timing Constraints

- `expires_at = created_at + 24h`. If `processing_status != "ended"` at `expires_at`, remaining `processing` requests transition to `expired` and the batch moves to `ended`.
- `results_url` is non-null if and only if `processing_status == "ended"`.
- `ended_at` is non-null if and only if `processing_status == "ended"`.

---

## S6. Bootstrap Pipeline — Formal Contracts

### S6.1 Pipeline Topology

```
[01_prepare] → [02_submit] → [03_poll] → [04_fetch]
                                  ↘
                              [05_cancel]
```

Execution is strictly sequential. No script may be invoked out of order except `05_cancel`, which may be invoked at any point after `02_submit`.

### S6.2 Artifact Definitions

| Artifact | Producer | Consumer(s) | Format |
|----------|----------|-------------|--------|
| `input.jsonl` | User | 01 | JSONL (§S6.3) |
| `system_prompt.txt` | User | 01 | UTF-8 text |
| `batch_payload.json` | 01 | 02 | JSON (§S4.1) |
| `batch_state.json` | 02, 03, 05 | 03, 04, 05 | JSON (§S6.4) |
| `results.jsonl` | 04 | User | JSONL (§S6.5) |

### S6.3 Input JSONL Schema

Each line:

```
InputRecord {
  custom_id: string  // REQUIRED. Unique across file.
  prompt:    string  // REQUIRED. Non-empty.
}
```

**Preconditions enforced by 01:**

- File exists and is non-empty.
- Every line is valid JSON.
- Every record has both `custom_id` and `prompt`.
- No duplicate `custom_id` values.
- Total request count <= 100,000.
- Serialized payload size <= 256 MB.

**Postcondition:** `batch_payload.json` conforms to `BatchCreateRequest` (§S4.1).

### S6.4 State File Schema

```
BatchState {
  batch_id:          string           // Set by 02.
  processing_status: string           // Set by 02, updated by 03/05.
  created_at:        string           // Set by 02.
  expires_at:        string           // Set by 02.
  request_count:     integer          // Set by 02.
  ended_at:          string | absent  // Set by 03.
  results_url:       string | absent  // Set by 03.
  request_counts:    object | absent  // Set by 03.
  cancel_initiated_at: string | absent // Set by 05.
}
```

**Invariant:** `batch_id` is immutable after creation by 02.

### S6.5 Output JSONL Schema

Each line:

```
OutputRecord {
  custom_id:     string
  status:        "succeeded" | "errored" | "canceled" | "expired"
  text:          string | absent   // Present iff status == "succeeded"
  model:         string | absent   // Present iff status == "succeeded"
  stop_reason:   string | absent   // Present iff status == "succeeded"
  input_tokens:  integer | absent  // Present iff status == "succeeded"
  output_tokens: integer | absent  // Present iff status == "succeeded"
  error:         object | absent   // Present iff status == "errored"
}
```

### S6.6 Script Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing file, validation failure, timeout, API error) |

All error messages are written to stderr. Successful output summaries are written to stdout.

### S6.7 Script Preconditions and Postconditions

**01_prepare_batch.py**

| | Condition |
|-|-----------|
| PRE | `--input` file exists, is valid JSONL per §S6.3 |
| POST | `--output` file exists, conforms to §S4.1 |
| POST | `len(requests) >= 1 AND len(requests) <= 100,000` |
| POST | `sizeof(payload) <= 256 MB` |

**02_submit_batch.py**

| | Condition |
|-|-----------|
| PRE | `--payload` file exists, conforms to §S4.1 |
| PRE | `ANTHROPIC_API_KEY` is set and valid |
| POST | `--state` file exists, conforms to §S6.4 |
| POST | `batch_state.processing_status == "in_progress"` |

**03_poll_status.py**

| | Condition |
|-|-----------|
| PRE | `--state` file exists, contains valid `batch_id` |
| POST (success) | `batch_state.processing_status == "ended"` |
| POST (success) | `batch_state.results_url` is non-null |
| POST (timeout) | Exit code 1, state file unchanged |

**04_fetch_results.py**

| | Condition |
|-|-----------|
| PRE | `--state` file exists, `processing_status == "ended"` |
| POST | `--output` file exists, conforms to §S6.5 |
| POST | Number of output lines == sum of `request_counts` values |

**05_cancel_batch.py**

| | Condition |
|-|-----------|
| PRE | Batch exists and `processing_status != "ended"` |
| POST | `batch_state.processing_status ∈ {"canceling", "ended"}` |

---

## S7. Error Taxonomy

### S7.1 Submission-Time Errors (HTTP)

| HTTP Code | Error Type | Cause | Recovery |
|-----------|-----------|-------|----------|
| 400 | `invalid_request_error` | Malformed top-level JSON | Fix payload structure |
| 401 | `authentication_error` | Invalid/missing API key | Provide valid key |
| 403 | `permission_error` | Key lacks batch permissions | Check Workspace permissions |
| 413 | `request_too_large` | Payload > 256 MB | Split into smaller batches |
| 429 | `rate_limit_error` | Too many batch creations or queued requests | Backoff and retry |
| 500 | `api_error` | Internal server error | Retry with backoff |

### S7.2 Per-Request Errors (in results)

| Result Type | Error Type | Cause | Recovery |
|-------------|-----------|-------|----------|
| `errored` | `invalid_request_error` | Invalid params (bad model, missing field) | Fix and resubmit |
| `errored` | `api_error` | Transient processing failure | Retry directly |
| `expired` | N/A | 24h elapsed before execution | Resubmit in new batch |
| `canceled` | N/A | User-initiated cancellation | Resubmit if needed |

### S7.3 Error Isolation

**Invariant:** The result of request `i` is independent of the result of request `j` for all `i != j`. A single request failure does not affect any other request in the batch.

---

## S8. Rate Limits

### S8.1 Separation

Batch API rate limits are separate from synchronous Messages API rate limits. Batch processing does not consume standard API quota.

### S8.2 Limit Types

| Limit | Scope | Effect |
|-------|-------|--------|
| Batch creation rate | Per Workspace | 429 on excess POST /v1/messages/batches |
| Queued request count | Per Workspace | 429 when too many requests are in `processing` state |
| Throughput | Global | Slower processing, potential request expiration |

### S8.3 Spend Limits

Due to high throughput and concurrent processing, batches may slightly exceed a Workspace's configured spend limit. This is a known behavior, not a bug.

---

## S9. Data Governance

### S9.1 Isolation Model

```
Workspace A ──┐
              ├── No shared visibility
Workspace B ──┘
```

- Batches created by Workspace A's API key are invisible to Workspace B.
- Results are accessible only to keys in the creating Workspace, or Console users with appropriate permissions.

### S9.2 Retention Schedule

| Artifact | Retention |
|----------|-----------|
| Batch metadata | Indefinite (viewable after results expire) |
| Batch results | 29 days from `created_at` |

After 29 days, `results_url` returns 404. Batch metadata (`id`, `request_counts`, timestamps) remains accessible.

### S9.3 ZDR Exclusion

The Message Batches API is **not** eligible for Zero Data Retention. Data is retained according to the standard retention policy.

---

## S10. Invariants Summary

For reference, all invariants stated in this document:

| ID | Invariant |
|----|-----------|
| INV-1 | `∀ i,j ∈ requests: i ≠ j → i.custom_id ≠ j.custom_id` |
| INV-2 | `Σ(request_counts) == len(requests)` at all times |
| INV-3 | `processing_status == "ended" → request_counts.processing == 0` |
| INV-4 | `processing_status == "ended" ↔ results_url ≠ null` |
| INV-5 | `processing_status == "ended" ↔ ended_at ≠ null` |
| INV-6 | `result(i)` is independent of `result(j)` for all `i ≠ j` |
| INV-7 | `batch_state.batch_id` is immutable after creation |
| INV-8 | Result ordering in JSONL is unspecified |
| INV-9 | `expires_at == created_at + 24h` |
| INV-10 | `ended` is a terminal state with no outgoing transitions |

---

## S11. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-22 | Initial specification |
