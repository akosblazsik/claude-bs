#!/usr/bin/env python3
"""
04_fetch_results.py — Stream batch results to a JSONL file.

Reads:  batch_state.json (or --state <path>)
Writes: results.jsonl     (or --output <path>)

Each output line is a JSON object:
{
    "custom_id": "...",
    "status": "succeeded|errored|canceled|expired",
    "text": "...",           // assistant response (if succeeded)
    "model": "...",          // model used (if succeeded)
    "input_tokens": N,       // usage (if succeeded)
    "output_tokens": N,      // usage (if succeeded)
    "error": {...}           // error object (if errored)
}
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic


def extract_result(item: dict) -> dict:
    """Flatten a single batch result into a clean output record."""
    custom_id = item["custom_id"]
    result = item["result"]
    status = result["type"]

    record = {"custom_id": custom_id, "status": status}

    if status == "succeeded":
        msg = result["message"]
        # Extract text from content blocks
        texts = [
            block["text"]
            for block in msg.get("content", [])
            if block.get("type") == "text"
        ]
        record["text"] = "\n".join(texts)
        record["model"] = msg.get("model", "")
        record["stop_reason"] = msg.get("stop_reason", "")
        usage = msg.get("usage", {})
        record["input_tokens"] = usage.get("input_tokens", 0)
        record["output_tokens"] = usage.get("output_tokens", 0)
    elif status == "errored":
        record["error"] = result.get("error", {})
    # canceled and expired have no additional data

    return record


def main():
    parser = argparse.ArgumentParser(description="Fetch batch results.")
    parser.add_argument("--state", default="batch_state.json",
                        help="Path to batch state file")
    parser.add_argument("--output", default="results.jsonl",
                        help="Output JSONL file")
    args = parser.parse_args()

    state_path = Path(args.state)
    if not state_path.exists():
        print(f"ERROR: State file not found: {args.state}", file=sys.stderr)
        sys.exit(1)

    state = json.loads(state_path.read_text(encoding="utf-8"))

    if state.get("processing_status") != "ended":
        print("ERROR: Batch has not ended yet. Run 03_poll_status.py first.",
              file=sys.stderr)
        sys.exit(1)

    batch_id = state["batch_id"]
    client = anthropic.Anthropic()

    print(f"Streaming results for batch {batch_id}...")

    counts = {"succeeded": 0, "errored": 0, "canceled": 0, "expired": 0}

    with open(args.output, "w", encoding="utf-8") as f:
        for item in client.messages.batches.results(batch_id):
            # The SDK yields objects; convert to dict
            item_dict = json.loads(item.model_dump_json())
            record = extract_result(item_dict)
            counts[record["status"]] = counts.get(record["status"], 0) + 1
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    total = sum(counts.values())
    print(f"\nFetched {total} results → {args.output}")
    for status, count in counts.items():
        if count > 0:
            print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
