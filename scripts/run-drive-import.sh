#!/usr/bin/env bash
# Launch the Drive importer with its Google API dependencies.
cd "$(dirname "$0")/.." || exit 1
exec uv run \
  --with google-api-python-client \
  --with google-auth-oauthlib \
  --with google-auth-httplib2 \
  python scripts/import-drive-context.py "$@"
