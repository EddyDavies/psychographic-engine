# Deploy

The review page is served by a Cloudflare Worker backed by R2 storage.

## First-time setup

```bash
cd worker && pnpm install   # hardened config in worker/pnpm-workspace.yaml

# Create R2 buckets
pnpm exec wrangler r2 bucket create ad-review
pnpm exec wrangler r2 bucket create ad-review-dev

# Set OAuth secrets (used for Google Drive export)
pnpm exec wrangler secret put GOOGLE_CLIENT_ID
pnpm exec wrangler secret put GOOGLE_CLIENT_SECRET
```

## Deploy

```bash
cd worker && pnpm run deploy
```

## Local dev

```bash
cd worker && pnpm run dev
```

## Upload ads

Use `scripts/ad_set_builder.py` to package and upload ad sets to R2:

```bash
cd scripts && uv run python ad_set_builder.py \
  --folder ../clients/{client}/ads/statics/test-xxx-YYYY-MM-DD \
  --upload --csv
```
