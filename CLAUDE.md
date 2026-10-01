# Psychographic Engine

Markdown knowledge base for creative strategy. AI agents browse this for brand context when writing copy, building briefs, or planning tests.

## Template Model

This is a public template: it carries shared prompts, scripts, frameworks, and the `clients/_template/` scaffold, but no client data. Client work happens in a private copy, with one `clients/{name}/` directory per client; see the README for onboarding a new client. Never add real client data to this repo.

## Where to Start

1. Read `clients/{client}/products/` — understand what's being sold
2. Read `clients/{client}/avatars/core-{name}/sub-{name}/profile.md` — understand the specific sub-avatar you're speaking to
3. Read `clients/{client}/avatars/core-{name}/ranked-angles.md` — prioritized angles to turn into ads
4. Read `clients/{client}/strategy/` — desires, forces, instincts driving purchases
5. Check `clients/{client}/testing/learnings.md` — don't repeat failed approaches
6. Check `clients/{client}/testing/creative-tracker.csv` — see what combinations have already been tried

## Ad Creation Pipeline

Always follow `prompts/README.md`. The required order is:

Sub-Avatar -> Angle Generation -> Angle Brief -> Pick Concepts -> Ad Assembly

After testing: `prompts/testing/process-learnings.md`

Hooks are not pre-written. They emerge when the selected angle collides with a messaging concept during ad assembly.

Before assembling ads, check `clients/{client}/testing/creative-tracker.csv` to avoid duplicating combinations. After assembling, append new rows to the CSV.

## Key Conventions

- **One avatar, one desire, one message per ad** (Rule of One)
- Angle status (`untested` → `testing` → `winner` / `loser`) lives in each angle file's frontmatter
- One concept is one ad set (3:2:2); a format change is its own concept
- Profiles and angles carry YAML frontmatter; run `uv run python scripts/check-knowledge.py` after editing avatars or the tracker
- Batch naming: `test-{batch}-{YYYY-MM-DD}`
- Core avatars: `core-{descriptive-name}`, sub-avatars: `sub-{descriptive-name}`
- kebab-case directories, lowercase filenames

## Structure

- `prompts/` — Reusable AI prompt templates
  - `research/` — Research workflow prompts
  - `angles/` — Angle generation (`generate-angles.md`, `angle-generation.md`, `angle-brief.md`)
  - `testing/` — Test planning prompts and `process-learnings.md`
  - `creative/` — Creative format templates for AI image generation
- `clients/_template/` — Copy this to onboard a new client
- `clients/{name}/` — Per-client brand knowledge
  - `brand/` — Voice, visual identity, no-gos
  - `products/` — Product knowledge with desire mapping and elevation maps
    - `images/` — Product reference photos for AI generation (cutout + styled per product)
  - `offers/` — Bundle/offer positioning
    - `images/` — Offer/bundle reference photos for AI generation
  - `avatars/` — Psychographic profiles, organized hierarchically
    - `core-{name}/` — Core avatar directory
      - `profile.md` — Core 5 psychographic profile
      - `ranked-angles.md` — Evolve-format angle playbook, sub-avatars ranked by strength
      - `sub-{name}/` — Sub-avatar directory
        - `profile.md` — Sub-avatar psychographic profile
        - `angle-{slug}.md` — Individual angle (3 per sub-avatar, 3 hooks each)
    - `summary.md` — Cross-avatar summary tables
    - `research/` — Review mining and research artifacts
  - `strategy/` — Shared strategic concepts (desires, forces, instincts, awareness)
  - `angles/` — Archive of pre-Evolve angles; new angles live under avatars
  - `concepts/` — Method docs (angles-and-testing, execution, copywriting, offer-understanding, belief-framework, marketing-frameworks, desire-forces, workflow) plus `formats/`
  - `testing/` — Winners, losers, and strategic learnings
    - `creative-tracker.csv` — Row-per-ad log, 18 columns (batch, concept, testing method, sub-avatar, angle, product, offer, variation, messaging, visual, format, channel, asset ref, status, result, notes)
    - `creative-tracker.md` — Coverage summary and usage guide

## Review Mining with Playwright

- Client-specific scrapers live in your private copy alongside that client's data (e.g. `scripts/scrape-reviews.py`); follow `prompts/research/review-mining.md` for the workflow
- Analysis output goes to `clients/{client}/avatars/research/review-mining-{YYYY-MM-DD}.md`
- Also check Trustpilot (`uk.trustpilot.com/review/{client-domain}`) for external reviews

## Worktrees

- Worktree directory: `.worktrees/` (project-local)

## What Lives Here vs meta-ads DB

- **Here:** Stable strategic context (brand voice, avatars, angles, product knowledge)
- **meta-ads DB:** Execution artifacts (ad records, metrics, renders, generated copy)
- See `DATABASE-MAPPING.md` for field-level mapping
