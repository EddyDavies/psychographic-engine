#!/usr/bin/env bash
# Launch the ad review server with all dependencies
cd "$(dirname "$0")/.." || exit 1
exec uv run \
  --with fastapi \
  --with uvicorn \
  --with httpx \
  --with google-api-python-client \
  --with google-auth-oauthlib \
  --with google-auth-httplib2 \
  python scripts/review-server.py "$@"
