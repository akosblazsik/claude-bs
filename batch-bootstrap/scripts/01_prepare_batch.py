#!/usr/bin/env python3
"""
01_prepare_batch.py — Build a batch payload from input.jsonl

Input:  A JSONL file where each line has:
        { "custom_id": "<unique_id>", "prompt": "<user_message>" }

Output: A JSON file containing the full batch request body,
        ready for submission to the Message Batches API.

Options:
    --input         Path to input JSONL (required)
    --output        Path to output JSON payload (default: batch_payload.json)
    --model         Model to use (default: claude-sonnet-4-5)
    --max-tokens    Max tokens per response (default: 1024)
    --system        Path to a shared system prompt file (optional)
    --cache         Enable prompt caching on system prompt (flag)
"""

import argparse
import json
import sys
from pathlib import Path


def build_request(custom_id: str, prompt: str, model: str,
                  max_tokens: int, system: list | None) -> dict:
    """Build a single batch request object."""
    params = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        params["system"] = system
    return {"custom_id": custom_id, "params": params}


def load_system_prompt(path: str | None, cache: bool) -> list | None:
    """Load and optionally cache-wrap a system prompt file."""
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8").strip()
    block = {"type": "text", "text": text}
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]


def main():
    parser = argparse.ArgumentParser(description="Prepare a batch payload.")
    parser.add_argument("--input", required=True, help="Path to input JSONL")
    parser.add_argument("--output", default="batch_payload.json",
                        help="Output payload path")
    parser.add_argument("--model", default="claude-sonnet-4-5",
                        help="Model identifier")
    parser.add_argument("--max-tokens", type=int, default=1024,
                        help="Max tokens per response")
    parser.add_argument("--system", default=None,
                        help="Path to shared system prompt")
    parser.add_argument("--cache", action="store_true",
                        help="Enable prompt caching on system prompt")
    args = parser.parse_args()

    system = load_system_prompt(args.system, args.cache)

    requests = []
    seen_ids = set()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    for line_num, line in enumerate(input_path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"ERROR: Line {line_num}: invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        cid = record.get("custom_id")
        prompt = record.get("prompt")

        if not cid or not prompt:
            print(f"ERROR: Line {line_num}: missing 'custom_id' or 'prompt'",
                  file=sys.stderr)
            sys.exit(1)

        if cid in seen_ids:
            print(f"ERROR: Line {line_num}: duplicate custom_id '{cid}'",
                  file=sys.stderr)
            sys.exit(1)

        seen_ids.add(cid)
        requests.append(build_request(cid, prompt, args.model,
                                      args.max_tokens, system))

    if not requests:
        print("ERROR: No requests found in input file.", file=sys.stderr)
        sys.exit(1)

    payload = {"requests": requests}

    # Validate size constraint (256 MB limit)
    payload_bytes = json.dumps(payload).encode("utf-8")
    size_mb = len(payload_bytes) / (1024 * 1024)
    if size_mb > 256:
        print(f"ERROR: Payload size {size_mb:.1f} MB exceeds 256 MB limit.",
              file=sys.stderr)
        sys.exit(1)

    if len(requests) > 100_000:
        print(f"ERROR: {len(requests)} requests exceeds 100,000 limit.",
              file=sys.stderr)
        sys.exit(1)

    Path(args.output).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Prepared {len(requests)} requests → {args.output} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
