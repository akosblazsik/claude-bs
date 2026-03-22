#!/usr/bin/env python3
"""
03_poll_status.py — Poll a batch until processing ends.

Reads:  batch_state.json (or --state <path>)
Updates: batch_state.json with final status and results_url.

Options:
    --interval   Polling interval in seconds (default: 30)
    --timeout    Maximum wait in seconds (default: 86400 = 24h)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import anthropic


def main():
    parser = argparse.ArgumentParser(description="Poll batch status.")
    parser.add_argument("--state", default="batch_state.json",
                        help="Path to batch state file")
    parser.add_argument("--interval", type=int, default=30,
                        help="Polling interval in seconds")
    parser.add_argument("--timeout", type=int, default=86400,
                        help="Maximum wait time in seconds")
    args = parser.parse_args()

    state_path = Path(args.state)
    if not state_path.exists():
        print(f"ERROR: State file not found: {args.state}", file=sys.stderr)
        print("Run 02_submit_batch.py first.", file=sys.stderr)
        sys.exit(1)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    batch_id = state["batch_id"]

    client = anthropic.Anthropic()
    start = time.time()

    print(f"Polling batch {batch_id} every {args.interval}s (timeout: {args.timeout}s)")

    while True:
        elapsed = time.time() - start
        if elapsed > args.timeout:
            print(f"TIMEOUT: {args.timeout}s exceeded.", file=sys.stderr)
            sys.exit(1)

        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts

        print(
            f"  [{elapsed:6.0f}s] status={batch.processing_status}"
            f"  processing={counts.processing}"
            f"  succeeded={counts.succeeded}"
            f"  errored={counts.errored}"
            f"  canceled={counts.canceled}"
            f"  expired={counts.expired}"
        )

        if batch.processing_status == "ended":
            state.update({
                "processing_status": "ended",
                "ended_at": str(batch.ended_at),
                "results_url": batch.results_url,
                "request_counts": {
                    "succeeded": counts.succeeded,
                    "errored": counts.errored,
                    "canceled": counts.canceled,
                    "expired": counts.expired,
                },
            })
            state_path.write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
            print(f"\nBatch ended. Results URL: {batch.results_url}")
            print(f"State updated: {args.state}")
            return

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
