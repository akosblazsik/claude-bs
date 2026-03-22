Delegate this task to the @feature-implementer agent.

**Task:** $ARGUMENTS

Instruct the implementer to:
1. Read CLAUDE.md for project conventions.
2. If a spec or design exists in the conversation, follow it exactly.
3. Implement the smallest coherent change set.
4. Run `pnpm typecheck` and `pnpm lint` before reporting completion.
5. Report files changed and verification results.

After the implementer returns, suggest running `/review` to verify.
