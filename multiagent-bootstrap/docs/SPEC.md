# Multiagent Next.js/shadcn Bootstrap — Technical Specification

## 1. Purpose

Bootstrap a Next.js + shadcn/ui project configured for **multiagent development with Claude Code**.
Each agent operates under explicit authority boundaries via subagent definitions, scoped permissions, and deterministic hooks.

## 2. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Next.js 15 (App Router) | File-based routing = clear module boundaries for agent decomposition |
| UI | shadcn/ui + Tailwind v4 | Copy-paste component model = no hidden runtime dependencies |
| Package manager | pnpm | Strict dependency resolution, workspace-ready |
| Type system | TypeScript strict mode | Agent output must be statically verifiable |
| Linting | Biome | Single binary, replaces ESLint + Prettier with zero config drift |
| Testing | Vitest + Playwright | Unit + E2E, both runnable from hooks |
| State | Zustand (when needed) | Minimal API surface, no provider ceremony |

## 3. Agent Topology

Five subagents. The orchestrator is the default session agent (set in `settings.json`).
It classifies tasks and routes to specialists. Only the feature-implementer has write access.

```
Human (you)
  └── Claude Code (@orchestrator — default agent)
        ├── @platform-architect     — Read-only. Structural design.
        ├── @integration-engineer   — Read-only. API/mutation/adapter design.
        ├── @feature-implementer    — Write access. Bounded implementation.
        └── @reviewer               — Read-only + Bash(test). Quality gate.
```

### 3.1 Authority Boundaries

| Agent | Read | Write | Edit | Bash | Agent | Model |
|---|---|---|---|---|---|---|
| orchestrator | ✅ all | ✅ | ✅ | ✅ | ✅ delegates | opus |
| platform-architect | ✅ all | ❌ | ❌ | ❌ | ❌ | opus |
| integration-engineer | ✅ all | ❌ | ❌ | ❌ | ❌ | sonnet |
| feature-implementer | ✅ all | ✅ app/, components/, lib/, tests/ | ✅ same | ✅ pnpm, npx, git status/diff | ❌ | sonnet |
| reviewer | ✅ all | ❌ | ❌ | ✅ pnpm test/lint/typecheck/build, git diff | ❌ | sonnet |

### 3.2 Routing Rules

- route/layout/cache/auth/data-flow → @platform-architect
- server actions/route handlers/adapters/API coupling → @integration-engineer
- bounded approved implementation → @feature-implementer
- all non-trivial implementation → @reviewer before approval

### 3.3 Default Workflow

1. You describe a task (or use `/do [task]`).
2. Orchestrator classifies: architecture / integration / implementation / review.
3. Orchestrator delegates to appropriate specialist(s).
4. Design outputs require your approval before implementation.
5. Non-trivial implementations go through @reviewer before completion.
6. Orchestrator synthesizes results and reports back.

### 3.4 Direct Commands

| Command | Target | Use when |
|---|---|---|
| `/do [task]` | @orchestrator | Default. Let orchestrator route. |
| `/architect [question]` | @platform-architect | You know it's a structural question. |
| `/integrate [question]` | @integration-engineer | You know it's an API/mutation question. |
| `/implement [spec]` | @feature-implementer | Spec is approved, ready to build. |
| `/review [scope]` | @reviewer | Implementation done, verify it. |

## 4. File Structure

```
.
├── .claude/
│   ├── settings.json          # Permissions, hooks, model config, default agent
│   ├── settings.local.json    # Local overrides (gitignored)
│   ├── agents/
│   │   ├── orchestrator.md          # Task router and synthesizer
│   │   ├── platform-architect.md    # Structural design (read-only)
│   │   ├── integration-engineer.md  # API/mutation design (read-only)
│   │   ├── feature-implementer.md   # Bounded implementation (write)
│   │   └── reviewer.md             # Quality gate (read + test)
│   ├── commands/
│   │   ├── do.md              # /do — routes through orchestrator
│   │   ├── architect.md       # /architect — direct to architect
│   │   ├── integrate.md       # /integrate — direct to integration
│   │   ├── implement.md       # /implement — direct to implementer
│   │   └── review.md          # /review — direct to reviewer
│   └── rules/
│       └── conventions.md     # Always-loaded project rules
├── CLAUDE.md                  # Project root context
├── .mcp.json                  # MCP server config (if needed)
├── biome.json                 # Linting/formatting config
├── tsconfig.json
├── package.json
├── next.config.ts
├── app/                       # App Router — routing only
│   ├── layout.tsx             # Root layout (required, defines <html>/<body>)
│   ├── page.tsx               # Home route
│   ├── globals.css
│   ├── not-found.tsx          # Custom 404
│   └── [feature]/             # Nested routes as needed
│       ├── layout.tsx         # Optional nested layout
│       └── page.tsx
├── components/                # Shared components
│   └── ui/                    # shadcn components (do not modify directly)
├── lib/                       # Shared utilities and types
│   ├── utils.ts               # shadcn cn() utility
│   └── types.ts               # Shared type definitions
├── tests/
│   └── example.test.ts
├── public/                    # Static assets (must remain at root)
└── docs/
    └── SPEC.md                # This file
```

**Layout rationale:** `app/` is purely for routing (pages, layouts, route handlers).
All shared code (`components/`, `lib/`) lives at the project root as siblings.
No `src/` directory — Next.js ignores `src/app` when `app/` exists at root.

## 5. Hook Contracts

| Event | Matcher | Action |
|---|---|---|
| PostToolUse | Write\|Edit\|MultiEdit | Run `pnpm biome check --write` on changed file |
| SessionStart | * | Run `pnpm typecheck` (first 20 lines), inject project health |
| PreToolUse | Bash | Block `rm -rf`, `git push --force`, `git reset --hard` |

## 6. Lifecycle

### 6.1 Bootstrap (you run once)
```bash
pnpm create next-app@latest . --typescript --tailwind --eslint=false --app --no-src-dir --import-alias "@/*"
pnpm add -D @biomejs/biome vitest @vitejs/plugin-react playwright @playwright/test
pnpm dlx shadcn@latest init
```

### 6.2 Then copy the `.claude/` directory and `CLAUDE.md` from this bootstrap into your project root.

### 6.3 Start Claude Code
```bash
claude --model opus
```

## 7. Non-Goals

- No CI/CD configuration (project-specific).
- No database layer (project-specific).
- No authentication (project-specific).
- No agent teams / experimental swarms (unstable, unnecessary for most work).
- No third-party orchestration frameworks (overhead exceeds value at this scale).
