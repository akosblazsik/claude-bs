# Claude Batch Processing Bootstrap

Reproducible scaffold for the Anthropic Message Batches API.

## Prerequisites

- Python 3.9+
- `pip install anthropic`
- Environment variable: `ANTHROPIC_API_KEY`

## Structure

```
batch-bootstrap/
├── README.md                ← You are here
├── MANUAL.md                ← Full reference manual
├── SPEC.md                  ← Technical specification
├── scripts/
│   ├── 01_prepare_batch.py  ← Build batch payload from input.jsonl
│   ├── 02_submit_batch.py   ← Submit to API, write batch_id
│   ├── 03_poll_status.py    ← Poll until ended
│   ├── 04_fetch_results.py  ← Stream results → output.jsonl
│   └── 05_cancel_batch.py   ← Cancel in-flight batch
└── examples/
    ├── input.jsonl           ← Example input (one request per line)
    └── system_prompt.txt     ← Shared system prompt for caching
```

## Lifecycle

```
prepare → submit → poll → fetch
                     ↘ cancel (optional)
```

Each script reads/writes to well-defined files. No implicit state.

## Quick Start

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# 1. Edit examples/input.jsonl with your prompts
# 2. Run the pipeline:
python scripts/01_prepare_batch.py --input examples/input.jsonl --output batch_payload.json
python scripts/02_submit_batch.py --payload batch_payload.json
python scripts/03_poll_status.py
python scripts/04_fetch_results.py --output results.jsonl
```

## Documentation

| Document | Purpose |
|----------|---------|
| [MANUAL.md](MANUAL.md) | API reference, pricing, caching, error handling, script usage |
| [SPEC.md](SPEC.md) | Formal technical specification: schemas, state machine, contracts, invariants |
