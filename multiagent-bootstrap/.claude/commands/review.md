Delegate this task to the @reviewer agent.

**Review scope:** $ARGUMENTS

If no arguments provided, instruct the reviewer to:
1. Run `git diff` to identify recently changed files.
2. Run the full verification suite: typecheck → lint → test → build.
3. Inspect boundaries, flows, and state handling.
4. Classify issues as Critical / Warning / Suggestion.
5. Return verdict: Approve / Request Changes / Escalate.

After the reviewer returns, present findings.
If Approve: confirm readiness to commit.
If Request Changes: summarize the smallest repair path.
If Escalate: flag for human decision.
