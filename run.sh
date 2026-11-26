#!/usr/bin/env bash
# HAM launcher — creates/activates venv and installs dependencies if needed

set -euo pipefail

# Resolve project directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"
ENTRY_POINT="ham_gui.py"

# Create venv if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    PYTHON=""
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            PYTHON="$cmd"
            break
        fi
    done
    if [[ -z "$PYTHON" ]]; then
        echo "Error: python not found. Install Python from https://python.org" >&2
        exit 1
    fi
    if ! "$PYTHON" -m venv "$VENV_DIR"; then
        echo "Error: Failed to create venv." >&2
        exit 1
    fi
fi

# Activate venv
ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
if [[ -f "$ACTIVATE_SCRIPT" ]]; then
    # shellcheck disable=SC1090
    source "$ACTIVATE_SCRIPT"
else
    echo "Error: cannot find venv activate script" >&2
    exit 1
fi

# Install/update dependencies if requirements.txt is newer than the marker
MARKER="$VENV_DIR/.deps_installed"
if [[ ! -f "$MARKER" || "$REQUIREMENTS" -nt "$MARKER" ]]; then
    echo "Installing dependencies..."
    if ! python -m pip install --upgrade pip -q; then
        echo "Error: Failed to upgrade pip." >&2
        exit 1
    fi
    if ! python -m pip install -r "$REQUIREMENTS" -q; then
        echo "Error: Failed to install dependencies from $REQUIREMENTS." >&2
        exit 1
    fi
    touch "$MARKER"
fi

# Launch the application, passing through any command-line arguments
exec python "$ENTRY_POINT" "$@"
