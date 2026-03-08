#!/usr/bin/env bash
# Cloud District Club — Production Frontend Build Script
# Run this before starting FastAPI in any production environment.
# Usage: bash scripts/build.sh
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

# --- Generate build version: YYYY-MM-DD-<commit-count> ---
TODAY=$(date +%Y-%m-%d)
COMMIT_COUNT=$(git -C "$REPO_ROOT" rev-list --count HEAD 2>/dev/null || echo "1")
export EXPO_PUBLIC_BUILD_VERSION="${TODAY}-${COMMIT_COUNT}"

echo "============================================="
echo "  Cloud District Club — Frontend Build"
echo "  Version : $EXPO_PUBLIC_BUILD_VERSION"
echo "  Target  : $FRONTEND_DIR/dist"
echo "============================================="

cd "$FRONTEND_DIR"

# Clean previous build
rm -rf dist

# Build
npx expo export --platform web

echo ""
echo "Build complete: $EXPO_PUBLIC_BUILD_VERSION"
echo "Output: $FRONTEND_DIR/dist"
