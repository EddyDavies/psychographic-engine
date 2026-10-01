# Psychographic Engine

Markdown knowledge base for creative strategy. AI agents browse it for brand context when writing copy, building briefs, or planning tests. This is a reference-only repo; it is not programmatically read by the meta-ads app.

## How This Repo Is Organized

Client data never lives on `main`. Each client gets its own branch:

- **`main`** holds only shared assets: prompt templates (`prompts/`), pipeline scripts (`scripts/`), and the blank client scaffold (`clients/_template/`).
- **`client/{name}`** branches (e.g. `client/acme`) contain everything from `main` plus a single `clients/{name}/` directory with that client's filled-in knowledge base.

Rules of the road:

- Never commit client data to `main`. If a script or prompt improvement happens on a client branch, cherry-pick or port it back to `main` so every client benefits.
- To pull shared improvements into a client branch, run `git merge main` from that branch.
- Never merge a client branch into `main`.

## Getting Started With a New Client

```bash
git checkout main && git pull
git checkout -b client/{client-name}
cp -r clients/_template clients/{client-name}
git add clients/{client-name}
git commit -m "Scaffold {client-name} client"
git push -u origin client/{client-name}
```

Then fill in the scaffold, in this order:

1. Fill in `brand/guidelines/voice.md` and `brand/guidelines/visual-identity.md`
2. Add brand no-gos to `brand/no-gos/no-gos.md`
3. Import any existing client material from Google Drive (see below)
4. Run the `prompts/research/desire-research.md` prompt to identify desires
5. Run `prompts/research/review-mining.md` to extract customer language
6. Populate `products/` with one file per product
7. Build avatars from research (core avatars first, then sub-avatars)
8. Derive angles from avatars; each sub-avatar gets `angle-{slug}.md` files
9. Document shared mechanisms in `products/shared-mechanisms.md`

## How It Connects to meta-ads

The [meta-ads](../meta-ads) app stores ad records, metrics, renders, and generated copy. This repo stores the strategic context that informs those outputs.

**Decision rule:** If it changes per-ad-run, it goes in the DB. If it's stable strategic context, it goes here.

See [DATABASE-MAPPING.md](DATABASE-MAPPING.md) for the full field-level mapping between this repo and the meta-ads database.

## Repo Structure

```
prompts/           Reusable AI prompt templates for research and testing workflows
scripts/           Ad generation, review, and import tooling
clients/_template/ Copy this folder to onboard a new client (on a client branch)
clients/{name}/    Per-client directory, only present on that client's branch
```

Within each client directory:

| Directory    | Purpose                                                    |
|--------------|------------------------------------------------------------|
| `brand/`     | Voice, visual identity, no-gos                             |
| `products/`  | Product knowledge with Evolve framework sections            |
| `offers/`    | Offer/bundle positioning                                   |
| `avatars/`   | Psychographic portraits using Core 5 framework              |
| `angles/`    | Strategic angles with hooks and test status                  |
| `concepts/`  | Marketing frameworks, formats (static/video/email)          |
| `testing/`   | Test learnings and next directions                          |
| `research/`  | Raw research output                                        |
| `ads/`       | Generated ad creatives (gitignored)                        |
| `emails/`    | Generated email creatives                                  |

## Importing Context From Google Drive

If a client keeps briefs, decks, docs, or spreadsheets in Drive, pull that material into the repo first so agents can browse it alongside the curated knowledge base.

```bash
scripts/run-drive-import.sh \
  --folder "https://drive.google.com/drive/folders/DRIVE_FOLDER_ID" \
  --client {client-name}
```

This writes into `clients/{client}/research/drive-imports/{folder-name}/` and generates:

- `README.md` with the Drive source and rerun command
- `manifest.json` with Drive IDs, source URLs, and import status
- exported files for supported Google Workspace docs plus raw downloads for standard files

Notes:

- The wrapper uses `uv run --with ...` so you do not need a local Python env for the Google client libraries.
- The script asks for additional readonly Drive scope the first time you use it.
- Google Docs and Slides are exported to Markdown-wrapped plain text.
- Google Sheets are exported as CSV for the first tab only.
- Reruns overwrite matching Drive IDs but do not prune files removed from Drive.
- Imported material is a raw mirror; move distilled content into `brand/`, `products/`, `avatars/`, or `strategy/` once reviewed.

## Conventions

- **Directory names:** kebab-case, lowercase filenames
- **Batch naming:** `test-{batch}-{YYYY-MM-DD}`
- **Core avatar naming:** `core-{descriptive-name}`
- **Sub-avatar naming:** `sub-{descriptive-name}`
- **Rule of One:** One avatar, one desire, one message per ad

## Working With AI Agents

- Check out the client's branch first; `main` has no client data
- Read `products/` + `avatars/` for context before generating copy
- Reference `avatars/core-{name}/ranked-angles.md` for prioritized angles
- Check `testing/learnings.md` before proposing repeat tests
- Check `testing/creative-tracker.csv` to avoid duplicating combinations
- Use `concepts/marketing-frameworks.md` to match framework to awareness level

## Ad Review Worker

A Cloudflare Worker (`worker/`) serves the ad review UI. It reads generated ad batches from R2 and displays them for review. See [DEPLOY.md](DEPLOY.md) for deployment details.

### Setup

```bash
# Worker (Node.js 22+)
cd worker && npm install

# Python scripts (requires uv: https://docs.astral.sh/uv/)
cd scripts && uv sync
```

Copy `.env.example` to `.env` in the project root and fill in the Cloudflare, OpenRouter, R2, and Google Drive keys.

### Deploy the worker

```bash
cd worker && npx wrangler deploy
```

Node.js can't reach Cloudflare through NordVPN; disconnect the VPN before running wrangler commands.

### Sync knowledge to R2

```bash
cd scripts && uv run python sync-knowledge.py --client {client} --delete
cd scripts && uv run python sync-knowledge.py --client {client} --watch   # auto-sync on changes
```

### Generate ads

```bash
cd scripts && uv run python generate-ads.py \
  --client {client} \
  --count N \                          # must be multiple of 3
  --sub-avatar sub-NAME \              # repeatable
  --messaging SLUG [SLUG ...] \        # messaging concepts
  --workers 4 \                        # parallel generation (default 1)
  --upload-r2                          # push to R2 so the review UI sees them
```

Other flags: `--dry-run` (copy only, no images), `--date YYYY-MM-DD`, `--skip N`

### Package for Google Drive

```bash
cd scripts && uv run python ad_set_builder.py \
  --folder ../clients/{client}/ads/statics/test-xxx-YYYY-MM-DD \
  --upload --csv
```

### Local dev

```bash
cd worker && npx wrangler dev    # http://localhost:8787
```

### R2 bucket layout

```
ad-review/
├── knowledge/               Synced client knowledge + prompts
│   ├── {client}/
│   └── prompts/
└── batches/                 Generated ad batches
    └── test-xxx-YYYY-MM-DD/
        ├── manifest.json
        ├── *-copy.md
        ├── *_9x16.png
        └── *_1x1.png
```

### Troubleshooting

- **wrangler fetch failed / ETIMEDOUT:** disconnect NordVPN. Node.js TCP to Cloudflare times out through the VPN even though curl works.
- **sync-knowledge.py R2 error:** check `.env` has `CF_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
- **"No batches found" in review UI:** generate ads with `--upload-r2`, or the batch hasn't been pushed to R2 yet.
