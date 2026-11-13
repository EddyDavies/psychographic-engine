# Psychographic Engine

Markdown knowledge base for creative strategy. AI agents browse this for brand context when writing copy, building briefs, or planning tests.

## Repo Model

This public repo carries the engine (`engine/`: prompts, scripts, method docs, and the `engine/template/` brand scaffold) but no brand data. Brand work happens in a private copy, with one top-level `{brand}/` folder per brand; see the README for onboarding a new brand. Never add real brand data to this repo.

## Where to Start

1. Read `{brand}/products/`: understand what's being sold
2. Read `{brand}/avatars/core-{name}/sub-{name}/profile.md`: understand the specific sub-avatar you're speaking to
3. Read `{brand}/avatars/core-{name}/ranked-angles.md`: prioritized angles to turn into ads
4. Read `{brand}/strategy/`: desires, forces, instincts driving purchases
5. Check `{brand}/testing/learnings.md`: don't repeat failed approaches
6. Check `{brand}/testing/creative-tracker.csv`: see what combinations have already been tried

## Ad Creation Pipeline

Always follow `engine/prompts/README.md`. The required order is:

Sub-Avatar -> Angle Generation -> Angle Brief -> Pick Concepts -> Ad Assembly

After testing: `engine/prompts/testing/process-learnings.md`

Launch and assess: `engine/prompts/testing/launch-and-assess.md` (dry run, live paused, enable, then `engine/scripts/meta/health.py`). Every Meta write (`--live`, `--enable`, pausing, budget changes) needs an explicit yes from the human first.

Hooks are not pre-written. They emerge when the selected angle collides with a messaging concept during ad assembly.

Before assembling ads, check `{brand}/testing/creative-tracker.csv` to avoid duplicating combinations. After assembling, append new rows to the CSV.

## Key Conventions

- **One avatar, one desire, one message per ad** (Rule of One)
- Angle status (`untested` → `testing` → `winner` / `loser`) lives in each angle file's frontmatter
- One concept is one ad set (3:2:2); a format change is its own concept
- Profiles and angles carry YAML frontmatter; run `uv run python engine/scripts/check-knowledge.py` after editing avatars or the tracker
- Batch naming: `test-{batch}-{YYYY-MM-DD}`
- Core avatars: `core-{descriptive-name}`, sub-avatars: `sub-{descriptive-name}`
- kebab-case directories, lowercase filenames
- Meta config lives in `{brand}/meta.toml` (template `engine/template/meta.toml`); credentials only in `.env`. Each launched batch records its Meta IDs in `meta-launch.json` beside its `manifest.json`
- Judge live ads with `engine/method/media-buying.md`: hours live, not calendar days; no kill under 5 times KPI

## Structure

The repo root holds `engine/` plus one folder per brand. A top-level folder is a brand when it contains both `brand/` and `avatars/`.

- `engine/prompts/`: Reusable AI prompt templates
  - `research/`: Research workflow prompts
  - `angles/`: Angle generation (`generate-angles.md`, `angle-generation.md`, `angle-brief.md`)
  - `concepts/`: Ad assembly plus `messaging/` and `visual/` concept libraries (the scripts read these)
  - `testing/`: Test planning prompts and `process-learnings.md`
- `engine/scripts/`: Ad generation, review server, `check-knowledge.py`; `brands.py` finds brand folders
  - `meta/`: `launch.py` (manifest to Meta campaign), `health.py` (read only delivery health), `graph.py` (shared Graph API client)
- `engine/method/`: Method docs shared by every brand (angles-and-testing, execution, copywriting, offer-understanding, belief-framework, marketing-frameworks, desire-forces, workflow) plus `formats/`; `course-lessons.md` points to the full lesson library
- `engine/template/`: Blank brand scaffold; onboard with `cp -r engine/template {brand}`
- `{brand}/`: Per-brand knowledge
  - `brand/`: Voice, visual identity, no-gos
  - `products/`: Product knowledge with desire mapping and elevation maps
    - `images/`: Product reference photos for AI generation (cutout + styled per product)
  - `offers/`: Bundle/offer positioning
    - `images/`: Offer/bundle reference photos for AI generation
  - `avatars/`: Psychographic profiles, organized hierarchically
    - `core-{name}/`: Core avatar directory
      - `profile.md`: Core 5 psychographic profile
      - `ranked-angles.md`: Evolve-format angle playbook, sub-avatars ranked by strength
      - `sub-{name}/`: Sub-avatar directory
        - `profile.md`: Sub-avatar psychographic profile
        - `angle-{slug}.md`: Individual angle (3 per sub-avatar, 3 hooks each)
    - `summary.md`: Cross-avatar summary tables
    - `research/`: Review mining and research artifacts
  - `strategy/`: Shared strategic concepts (desires, forces, instincts, awareness)
  - `angles/`: Archive of pre-Evolve angles; new angles live under avatars
  - `testing/`: Winners, losers, and strategic learnings
    - `creative-tracker.csv`: Row-per-ad log, 18 columns (batch, concept, testing method, sub-avatar, angle, product, offer, variation, messaging, visual, format, channel, asset ref, status, result, notes)
    - `creative-tracker.md`: Coverage summary and usage guide
  - `ads/`: Generated ads (gitignored)

## Review Mining with Playwright

- Brand-specific scrapers live in your private copy alongside that brand's data (e.g. `{brand}/research/scrape-reviews.py`); follow `engine/prompts/research/review-mining.md` for the workflow
- Analysis output goes to `{brand}/avatars/research/review-mining-{YYYY-MM-DD}.md`
- Also check Trustpilot (`uk.trustpilot.com/review/{brand-domain}`) for external reviews

## Worktrees

- Worktree directory: `.worktrees/` (project-local)
