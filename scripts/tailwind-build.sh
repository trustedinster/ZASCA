#!/usr/bin/env bash
# ============================================================================
# ZASCA - Tailwind CSS v4 Build Script
# ============================================================================
# Usage:
#   ./scripts/tailwind-build.sh          # One-time build
#   ./scripts/tailwind-build.sh --watch  # Watch mode (auto-rebuild on changes)
# ============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

TAILWIND_BIN="./static/vendor/tailwindcss"
INPUT_CSS="./static/src/tailwind.css"
OUTPUT_CSS="./static/css/provider.css"
TAILWIND_VERSION="v4.2.4"

detect_platform() {
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"
    case "$os" in
        linux)  os="linux" ;;
        darwin) os="macos" ;;
        *) echo "[ERROR] Unsupported OS: $os"; exit 1 ;;
    esac
    case "$arch" in
        x86_64|amd64) arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "[ERROR] Unsupported architecture: $arch"; exit 1 ;;
    esac
    echo "tailwindcss-${os}-${arch}"
}

download_tailwind() {
    local platform filename url
    platform="$(detect_platform)"
    filename="$platform"
    url="https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${filename}"

    echo "[INFO] Downloading Tailwind CSS CLI ${TAILWIND_VERSION}..."
    echo "  Platform: $platform"
    echo "  URL: $url"

    mkdir -p "$(dirname "$TAILWIND_BIN")"
    if command -v curl &>/dev/null; then
        curl -fSL -o "$TAILWIND_BIN" "$url"
    elif command -v wget &>/dev/null; then
        wget -O "$TAILWIND_BIN" "$url"
    else
        echo "[ERROR] Neither curl nor wget found. Please install one and retry."
        exit 1
    fi

    chmod +x "$TAILWIND_BIN"
    echo "[INFO] Tailwind CSS CLI downloaded successfully."
}

if [[ ! -x "$TAILWIND_BIN" ]]; then
    echo "[WARN] Tailwind CSS CLI not found at: $TAILWIND_BIN"
    read -rp "Download it now from GitHub? [Y/n] " answer
    case "${answer:-Y}" in
        [yY]|[yY][eE][sS]|"") download_tailwind ;;
        *) echo "[ERROR] Cannot build without Tailwind CSS CLI. Exiting."; exit 1 ;;
    esac
fi

mkdir -p "$(dirname "$OUTPUT_CSS")"

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
