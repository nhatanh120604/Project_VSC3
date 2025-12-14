#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=7860}"

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
