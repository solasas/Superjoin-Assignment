#!/usr/bin/env bash
# Convenience launcher: runs the FastAPI app with uvicorn.
# Uses ./.venv if it exists (see README "Install"), otherwise whatever
# uvicorn is on PATH.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/backend:${PYTHONPATH:-}"

if [ -x ".venv/bin/uvicorn" ]; then
  UVICORN=".venv/bin/uvicorn"
else
  UVICORN="uvicorn"
fi

exec "$UVICORN" app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}" --reload
