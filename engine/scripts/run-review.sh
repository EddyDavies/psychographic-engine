#!/usr/bin/env bash
# Launch the ad review server with all dependencies
cd "$(dirname "$0")/../.." || exit 1
exec uv run \
  --with fastapi \
  --with uvicorn \
  --with httpx \
  python engine/scripts/review-server.py "$@"
