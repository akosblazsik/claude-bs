#!/usr/bin/env python3
"""
05_cancel_batch.py — Cancel a batch that is currently processing.

Reads:  batch_state.json (or --state <path>)
Updates: batch_state.json with cancellation status.

After cancellation, the batch transitions to 'canceling' then 'ended'.
Partial results may be available for requests processed before cancellation.
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic


def main():
    parser = argparse.ArgumentParser(description="Cancel a batch.")
    parser.add_argument("--state", default="batch_state.json",
                        help="Path to batch state file")
    parser.add_argument("--batch-id", default=None,
                        help="Override: cancel this batch ID directly")
    args = parser.parse_args()

    if args.batch_id:
        batch_id = args.batch_id
    else:
        state_path = Path(args.state)
        if not state_path.exists():
            print(f"ERROR: State file not found: {args.state}", file=sys.stderr)
            sys.exit(1)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        batch_id = state["batch_id"]

    client = anthropic.Anthropic()

    print(f"Canceling batch {batch_id}...")
    batch = client.messages.batches.cancel(batch_id)

    print(f"Status: {batch.processing_status}")

    # Update state file if it exists
    state_path = Path(args.state)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["processing_status"] = batch.processing_status
        state["cancel_initiated_at"] = str(batch.cancel_initiated_at)
        state_path.write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )
        print(f"State updated: {args.state}")


if __name__ == "__main__":
    main()
