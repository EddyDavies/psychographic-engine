# Deploy

The review page is served by a Cloudflare Worker backed by R2 storage.

## First-time setup

```bash
cd worker && npm install

# Create R2 buckets
wrangler r2 bucket create ad-review
wrangler r2 bucket create ad-review-dev

# Set OAuth secrets (used for Google Drive export)
wrangler secret put GOOGLE_CLIENT_ID
wrangler secret put GOOGLE_CLIENT_SECRET
```

## Deploy

```bash
cd worker && npx wrangler deploy
```

## Local dev

```bash
cd worker && npx wrangler dev
```

## Upload ads

Use `scripts/ad_set_builder.py` to package and upload ad sets to R2:

```bash
cd scripts && uv run python ad_set_builder.py \
  --folder ../clients/{client}/ads/statics/test-xxx-YYYY-MM-DD \
  --upload --csv
```
