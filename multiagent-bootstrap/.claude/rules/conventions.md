---
description: Core project conventions. Always active.
---

## Import Rules
- Never use barrel exports (index.ts re-exports).
- Import shadcn components from `@/components/ui/[name]`.
- Import utilities from `@/lib/utils`.
- `app/` directory is for routing only. Never import shared code from `app/`.

## Component Rules
- Server Components by default. Justify every `"use client"`.
- Props must be typed with explicit interfaces, not inline types.
- No default exports except for page.tsx, layout.tsx, and route handlers.

## File Rules
- One component per file.
- Test files mirror source structure: `components/foo.tsx` → `tests/components/foo.test.tsx`.
- No files larger than 300 lines. Split if approaching this limit.

## Commit Rules
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- One logical change per commit.
