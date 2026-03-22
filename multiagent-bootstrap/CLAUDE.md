# Project Context

## Stack
- Next.js 15 (App Router, `app/` at project root)
- TypeScript in strict mode
- Tailwind CSS v4 + shadcn/ui
- pnpm as package manager
- Biome for formatting and linting (not ESLint, not Prettier)
- Vitest for unit tests, Playwright for E2E

## Commands
```
pnpm dev          # Start dev server
pnpm build        # Production build
pnpm typecheck    # tsc --noEmit
pnpm lint         # biome check
pnpm lint:fix     # biome check --write
pnpm test         # vitest run
pnpm test:e2e     # playwright test
```

## Architecture Rules

1. **App Router only.** `app/` directory at project root. No `pages/` directory. No `src/` wrapper.
2. **`app/` is for routing only.** Pages, layouts, route handlers, loading/error states. No shared components or utilities inside `app/`.
3. **Server Components by default.** Add `"use client"` only when the component requires browser APIs, event handlers, or hooks.
4. **shadcn/ui components** live in `components/ui/`. Never modify them directly — extend via wrapper components in `components/`.
5. **No barrel exports.** Import from specific files, not `index.ts` re-exports.
6. **Colocation.** Route-specific components live next to their `page.tsx` (e.g. `app/dashboard/_components/`). Shared components go in `components/`.
7. **Types.** Define types adjacent to usage. Shared types go in `lib/types.ts`. No `any`. No `@ts-ignore`.
8. **Naming.** Files: `kebab-case.tsx`. Components: `PascalCase`. Hooks: `use-kebab-case.ts`.
9. **Imports.** Use `@/*` alias which maps to project root. Example: `@/components/ui/button`, `@/lib/utils`.

## Agent Protocol

### Agents

| Agent | Role | Authority | Model |
|---|---|---|---|
| @orchestrator | Routes tasks, synthesizes results | Read + Write + Agent delegation | Opus |
| @platform-architect | Structural design (routes, layouts, boundaries, caching) | Read-only | Opus |
| @integration-engineer | Server actions, APIs, adapters, mutation flows | Read-only | Sonnet |
| @feature-implementer | Bounded, approved implementation | Read + Write + Edit + Bash | Sonnet |
| @reviewer | Quality gate (correctness, boundary integrity) | Read-only + Bash(test) | Sonnet |

### Routing rules

- route/layout/cache/auth/data-flow question → @platform-architect
- server actions/route handlers/adapters/API coupling → @integration-engineer
- bounded approved implementation → @feature-implementer
- all non-trivial implementation → @reviewer before approval

### Commands

- `/do [task]` — Entry point. Orchestrator classifies and routes.
- `/architect [question]` — Direct to platform architect.
- `/integrate [question]` — Direct to integration engineer.
- `/implement [spec]` — Direct to feature implementer.
- `/review [scope]` — Direct to reviewer.

### Workflow discipline

1. Non-trivial tasks go through orchestrator (or explicit specialist command).
2. Architecture and integration design must be approved before implementation.
3. Non-trivial implementations require review before completion.
4. Orchestrator synthesizes — does not implement directly unless trivial.

## Verification

Every implementation must pass before merge:
1. `pnpm typecheck` — zero errors
2. `pnpm lint` — zero errors
3. `pnpm test` — all passing
4. `pnpm build` — succeeds
