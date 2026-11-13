# Psychographic Engine

Markdown knowledge base for creative strategy. AI agents browse it for brand context when writing copy, building briefs, or planning tests.

## Your Private Copy

This repo ships the engine (prompts, scripts, method docs) and a blank brand scaffold (`engine/template/`), but no brand data.

Brand knowledge bases hold confidential material (reviews, briefs, offers, test results), so keep them out of public repos:

1. Clone this repo and push it to a new **private** repository of your own.
2. Add one top-level `{brand}/` folder per brand inside that private copy.
3. To pick up engine improvements later, add this repo as a remote and merge from it:

```bash
git remote add upstream https://github.com/EddyDavies/psychographic-engine.git
git fetch upstream
git merge upstream/main
```

If your copy was made earlier with GitHub's "Use this template" button, it shares no history with this repo, so the first merge needs `git merge upstream/main --allow-unrelated-histories`.

If you improve a prompt, script or method doc and want to send it back, open a pull request against this repo from a branch that contains no brand folders.

## Getting Started With a New Brand

```bash
cp -r engine/template {brand}
git add {brand}
git commit -m "Scaffold {brand}"
```

Then fill in the scaffold, in this order:

1. Fill in `brand/guidelines/voice.md` and `brand/guidelines/visual-identity.md`
2. Add brand no-gos to `brand/no-gos/no-gos.md`
3. Put any existing brand material (briefs, decks, docs) in `research/`
4. Run the `engine/prompts/research/desire-research.md` prompt to identify desires
5. Run `engine/prompts/research/review-mining.md` to extract customer language
6. Populate `products/` with one file per product
7. Build avatars from research (core avatars first, then sub-avatars)
8. Derive angles with `engine/prompts/angles/generate-angles.md`; each sub-avatar gets `angle-{slug}.md` files with frontmatter
9. Document shared mechanisms in `products/shared-mechanisms.md`

## Repo Structure

```
engine/prompts/    Reusable AI prompt templates for research, angles, ad assembly and testing
engine/scripts/    Ad generation, review tooling, and check-knowledge.py (frontmatter and tracker checker)
engine/method/     Method docs shared by every brand: frameworks, copywriting, testing, formats
                   (course-lessons.md: how to get into the full lesson library)
engine/template/   Blank brand scaffold; copy it to onboard a new brand
{brand}/           One folder per brand (keep these in your private copy)
```

A top-level folder counts as a brand when it holds both `brand/` and `avatars/`.

Within each brand folder:

| Directory    | Purpose                                                    |
|--------------|------------------------------------------------------------|
| `brand/`     | Voice, visual identity, no-gos                             |
| `products/`  | Product knowledge with Evolve framework sections            |
| `offers/`    | Offer/bundle positioning                                   |
| `avatars/`   | Psychographic portraits using Core 5 framework              |
| `angles/`    | Archive of pre-Evolve angles; new angles live under avatars  |
| `strategy/`  | Desires, forces, instincts, awareness levels               |
| `testing/`   | Test learnings, next directions, and the creative tracker   |
| `research/`  | Raw research output                                        |
| `ads/`       | Generated ad creatives (gitignored)                        |
| `emails/`    | Generated email creatives                                  |

## Conventions

- **Directory names:** kebab-case, lowercase filenames
- **Batch naming:** `test-{batch}-{YYYY-MM-DD}`
- **Core avatar naming:** `core-{descriptive-name}`
- **Sub-avatar naming:** `sub-{descriptive-name}`
- **Rule of One:** One avatar, one desire, one message per ad

## Working With AI Agents

- Work inside the brand's `{brand}/` folder in your private copy
- Read `products/` + `avatars/` for context before generating copy
- Reference `avatars/core-{name}/ranked-angles.md` for prioritized angles
- Check `testing/learnings.md` before proposing repeat tests
- Check `testing/creative-tracker.csv` to avoid duplicating combinations
- Run `uv run python engine/scripts/check-knowledge.py` before committing
- Use `engine/method/marketing-frameworks.md` to match framework to awareness level

## Scripts

Python scripts run with [uv](https://docs.astral.sh/uv/). From the repo root:

```bash
uv sync
cp .env.example .env    # then fill in OPENROUTER_API_KEY (and the META_ keys to launch ads)
```

Every script that works on one brand takes `--brand {brand}` (`--client` still works as an alias).

### Generate ads

```bash
uv run python engine/scripts/generate-ads.py \
  --brand {brand} \
  --count 6 \
  --sub-avatar sub-NAME \
  --messaging SLUG \
  --workers 4
```

`--count` must be a multiple of 3, `--sub-avatar` is repeatable, and `--messaging` takes one or more messaging concept slugs. Other flags: `--dry-run` (copy only, no images), `--date YYYY-MM-DD`, `--skip N`. Batches land in `{brand}/ads/statics/test-{batch}-{YYYY-MM-DD}/`.

### Review ads

```bash
bash engine/scripts/run-review.sh {brand}/ads/statics --brand {brand}
```

This opens a local review UI. Rejecting an ad regenerates it inline; when all three ads in a set are approved, the set is packaged into `{brand}/ads/ad_sets_{YYYY-MM-DD}/set_XX/` and a row is appended to `upload_spreadsheet.csv` there.

## Launching to Meta

Generated batches go to Meta with `engine/scripts/meta/launch.py`. Each batch becomes one campaign with the daily budget on the campaign (CBO), one ad set per concept with identical targeting, and up to three ads per ad set. Each ad shows the 1x1 image in feeds and the 9x16 image in Stories and Reels, with every Advantage+ creative enhancement off so the copy runs as written.

Setup, once per brand:

1. Copy `engine/template/meta.toml` to `{brand}/meta.toml` and fill in the objective, daily budget (minor units), targeting, landing URL and UTM template, CTA, and DSA names if you target the EU.
2. Add `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID` and optionally `META_INSTAGRAM_ACTOR_ID` to the repo-root `.env`. Credentials never go in `meta.toml`.

Then:

```bash
# Dry run (default): prints the full plan, sends nothing
uv run python engine/scripts/meta/launch.py --brand fernwood --batch fernwood/ads/statics/test-let-down-eco-switcher-2026-10-08

# Create everything PAUSED
uv run python engine/scripts/meta/launch.py --brand fernwood --batch fernwood/ads/statics/test-let-down-eco-switcher-2026-10-08 --live

# Start spend
uv run python engine/scripts/meta/launch.py --brand fernwood --batch fernwood/ads/statics/test-let-down-eco-switcher-2026-10-08 --live --enable

# Read only delivery health: account status, hours with no spend, live hours per ad set, frequency, CTR, CPC, rejected ads
uv run python engine/scripts/meta/health.py --batch fernwood/ads/statics/test-let-down-eco-switcher-2026-10-08
```

Created IDs are saved to `meta-launch.json` in the batch folder after every step, so a rerun skips what already exists. After a live run, each ad gets a row in `{brand}/testing/creative-tracker.csv` with status `testing`. Only entries whose manifest `review_status` is `passed` launch unless you pass `--allow-status`. The agent workflow is `engine/prompts/testing/launch-and-assess.md`; the judging rules are `engine/method/media-buying.md`.
