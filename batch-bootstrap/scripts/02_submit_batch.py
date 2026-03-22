#!/usr/bin/env python3
"""
02_submit_batch.py — Submit a prepared payload to the Message Batches API.

Reads:  batch_payload.json (or --payload <path>)
Writes: batch_state.json  (batch ID + metadata for downstream scripts)

Requires: ANTHROPIC_API_KEY environment variable.
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic


def main():
    parser = argparse.ArgumentParser(description="Submit a batch.")
    parser.add_argument("--payload", default="batch_payload.json",
                        help="Path to prepared payload JSON")
    parser.add_argument("--state", default="batch_state.json",
                        help="Output state file for downstream scripts")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"ERROR: Payload file not found: {args.payload}", file=sys.stderr)
        print("Run 01_prepare_batch.py first.", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    requests = payload["requests"]

    print(f"Submitting {len(requests)} requests...")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    batch = client.messages.batches.create(requests=requests)

    state = {
        "batch_id": batch.id,
        "processing_status": batch.processing_status,
        "created_at": batch.created_at,
        "expires_at": batch.expires_at,
        "request_count": len(requests),
    }

    Path(args.state).write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8"
    )

    print(f"Batch submitted: {batch.id}")
    print(f"Status:          {batch.processing_status}")
    print(f"Expires at:      {batch.expires_at}")
    print(f"State written:   {args.state}")


if __name__ == "__main__":
    main()
