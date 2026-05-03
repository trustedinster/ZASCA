#!/usr/bin/env bash
# ============================================================================
# ZASCA - Tailwind CSS v4 Build Script
# ============================================================================
# Usage:
#   ./scripts/tailwind-build.sh          # One-time build
#   ./scripts/tailwind-build.sh --watch  # Watch mode (auto-rebuild on changes)
# ============================================================================

set -euo pipefail

# Project root (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

TAILWIND_BIN="./static/vendor/tailwindcss"
INPUT_CSS="./static/src/tailwind.css"
OUTPUT_CSS="./static/css/provider.css"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_CSS")"

# Verify the Tailwind binary exists and is executable
if [[ ! -x "$TAILWIND_BIN" ]]; then
    echo "[ERROR] Tailwind CSS CLI not found or not executable at: $TAILWIND_BIN"
    exit 1
fi

# Build command
if [[ "${1:-}" == "--watch" ]]; then
    echo "[INFO] Starting Tailwind CSS in watch mode..."
    echo "  Input:  $INPUT_CSS"
    echo "  Output: $OUTPUT_CSS"
    "$TAILWIND_BIN" -i "$INPUT_CSS" -o "$OUTPUT_CSS" --watch
else
    echo "[INFO] Building Tailwind CSS (one-time)..."
    echo "  Input:  $INPUT_CSS"
    echo "  Output: $OUTPUT_CSS"
    "$TAILWIND_BIN" -i "$INPUT_CSS" -o "$OUTPUT_CSS"
    echo "[INFO] Build complete."
fi
