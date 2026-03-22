#!/usr/bin/env bash
set -euo pipefail

# Multiagent Next.js Bootstrap
# Usage: ./bootstrap.sh [project-name]
#
# This script:
# 1. Creates a new directory (or uses current)
# 2. Copies the .claude/ config, CLAUDE.md, and all config files
# 3. Installs dependencies
# 4. Runs initial verification

PROJECT_NAME="${1:-.}"

if [ "$PROJECT_NAME" != "." ]; then
  mkdir -p "$PROJECT_NAME"
  cd "$PROJECT_NAME"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Copying project files ==="

# Copy all bootstrap files (excluding this script and docs/SPEC.md)
cp -r "$SCRIPT_DIR/.claude" .
cp "$SCRIPT_DIR/CLAUDE.md" .
cp "$SCRIPT_DIR/package.json" .
cp "$SCRIPT_DIR/tsconfig.json" .
cp "$SCRIPT_DIR/next.config.ts" .
cp "$SCRIPT_DIR/postcss.config.mjs" .
cp "$SCRIPT_DIR/vitest.config.ts" .
cp "$SCRIPT_DIR/biome.json" .
cp "$SCRIPT_DIR/components.json" .
cp "$SCRIPT_DIR/.gitignore" .
cp -r "$SCRIPT_DIR/app" .
cp -r "$SCRIPT_DIR/components" .
cp -r "$SCRIPT_DIR/lib" .
cp -r "$SCRIPT_DIR/tests" .
mkdir -p docs public

echo "=== Installing dependencies ==="
pnpm install

echo "=== Initializing git ==="
git init
git add -A
git commit -m "chore: bootstrap multiagent nextjs project"

echo "=== Verification ==="
pnpm typecheck 2>&1 | tail -5 || true
pnpm lint 2>&1 | tail -5 || true
pnpm test 2>&1 | tail -10 || true

echo ""
echo "=== Done ==="
echo "Project ready. Start Claude Code with:"
echo "  cd $(pwd)"
echo "  claude --model opus"
echo ""
echo "Available commands:"
echo "  /plan [feature]   — Architect plans a feature"
echo "  /build [spec]     — Builder implements from spec"
echo "  /review           — Reviewer verifies implementation"
