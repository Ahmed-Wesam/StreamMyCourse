#!/usr/bin/env bash
# Thin wrapper for scripts/delete-user.py (mega-plan operator entrypoint).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python "$ROOT/scripts/delete-user.py" "$@"
