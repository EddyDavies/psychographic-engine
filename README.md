# Psychographic Engine

Markdown knowledge base for creative strategy. AI agents browse it for brand context when writing copy, building briefs, or planning tests. This is a reference-only repo; it is not programmatically read by the meta-ads app.

## Using This Template

This repo is a template. It ships the method (prompts, scripts, frameworks) and a blank client scaffold (`clients/_template/`), but no client data.

Client knowledge bases hold confidential material (reviews, briefs, offers, test results), so keep them out of public forks:

1. Create your own **private** copy: use GitHub's "Use this template" button, or clone this repo and push it to a new private repository.
2. Add one `clients/{name}/` directory per client inside that private copy.
3. To pick up method improvements later, add this repo as a remote and merge from it:

```bash
git remote add upstream https://github.com/EddyDavies/psychographic-engine.git
git fetch upstream && git merge upstream/main
```

If you improve a prompt, script or framework doc and want to send it back, open a pull request against this repo from a branch that contains no `clients/{name}/` data.

## Getting Started With a New Client

```bash
cp -r clients/_template clients/{client-name}
git add clients/{client-name}
git commit -m "Scaffold {client-name} client"
```

Then fill in the scaffold, in this order:

1. Fill in `brand/guidelines/voice.md` and `brand/guidelines/visual-identity.md`
2. Add brand no-gos to `brand/no-gos/no-gos.md`
3. Import any existing client material from Google Drive (see below)
4. Run the `prompts/research/desire-research.md` prompt to identify desires
5. Run `prompts/research/review-mining.md` to extract customer language
6. Populate `products/` with one file per product
7. Build avatars from research (core avatars first, then sub-avatars)
8. Derive angles with `prompts/angles/generate-angles.md`; each sub-avatar gets `angle-{slug}.md` files with frontmatter
9. Document shared mechanisms in `products/shared-mechanisms.md`

## How It Connects to meta-ads

A separate ads app (meta-ads, not included here) stores ad records, metrics, renders, and generated copy. This repo stores the strategic context that informs those outputs.

**Decision rule:** If it changes per-ad-run, it goes in the DB. If it's stable strategic context, it goes here.

See [DATABASE-MAPPING.md](DATABASE-MAPPING.md) for the full field-level mapping between this repo and the meta-ads database.

## Repo Structure

```
prompts/           Reusable AI prompt templates for research and testing workflows
scripts/           Ad generation, review, import tooling, and check-knowledge.py (frontmatter and tracker checker)
clients/_template/ Copy this folder to onboard a new client
clients/{name}/    Per-client directory (keep these in your private copy)
```

Within each client directory:

| Directory    | Purpose                                                    |
|--------------|------------------------------------------------------------|
| `brand/`     | Voice, visual identity, no-gos                             |
| `products/`  | Product knowledge with Evolve framework sections            |
| `offers/`    | Offer/bundle positioning                                   |
| `avatars/`   | Psychographic portraits using Core 5 framework              |
| `angles/`    | Archive of pre-Evolve angles; new angles live under avatars  |
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

- Work inside the client's `clients/{name}/` directory in your private copy
- Read `products/` + `avatars/` for context before generating copy
- Reference `avatars/core-{name}/ranked-angles.md` for prioritized angles
- Check `testing/learnings.md` before proposing repeat tests
- Check `testing/creative-tracker.csv` to avoid duplicating combinations
- Run `uv run python scripts/check-knowledge.py` before committing
- Use `concepts/marketing-frameworks.md` to match framework to awareness level

## Ad Review Worker

A Cloudflare Worker (`worker/`) serves the ad review UI. It reads generated ad batches from R2 and displays them for review. See [DEPLOY.md](DEPLOY.md) for deployment details.

### Setup

```bash
# Worker (Node.js 22+, pnpm)
cd worker && pnpm install

# Python scripts (requires uv: https://docs.astral.sh/uv/)
cd scripts && uv sync
```

Copy `.env.example` to `.env` in the project root and fill in the Cloudflare, OpenRouter, R2, and Google Drive keys.

### Deploy the worker

```bash
cd worker && pnpm run deploy
```

Some VPNs block Node.js from reaching Cloudflare; if wrangler times out, disconnect the VPN and retry.

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
cd worker && pnpm run dev    # http://localhost:8787
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

- **wrangler fetch failed / ETIMEDOUT:** disconnect your VPN. Node.js TCP to Cloudflare can time out through a VPN even when curl works.
- **sync-knowledge.py R2 error:** check `.env` has `CF_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
- **"No batches found" in review UI:** generate ads with `--upload-r2`, or the batch hasn't been pushed to R2 yet.
