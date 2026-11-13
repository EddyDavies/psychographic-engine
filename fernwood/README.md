# Fernwood (fictional worked example)

**Fernwood is not a real company.** Everything in this folder is invented to show the psychographic engine filled in end to end: the brand, the products, the prices, the customers, the review quotes, the ad comments, the test results and the learnings. No real people, reviews or competitor brands appear here. Do not quote any of it as evidence about a real market.

Use it as a reference when you onboard your own brand: copy `engine/template/` to a new top-level folder and compare each file you fill against the Fernwood version.

## The brand in one paragraph

Fernwood is a small British brand that sells refill cleaning pods. You drop a pod in the spray bottle you already own, add 500ml of tap water, and get a full bottle of cleaner without buying a new plastic bottle. It is positioned as "not another eco spray": the pitch is that the pod cleans like the bottle you gave up, not that it saves the planet.

## What is filled in

| Folder | What it shows |
|---|---|
| `brand/` | Voice, visual identity and no-gos, including the claims a cleaning brand must never make |
| `products/` | One file per pod (all-purpose, glass, bathroom) plus the brand-level mechanisms |
| `offers/` | Two offers: `starter-kit` (the entry offer) and `refill-subscription` (the repeat offer) |
| `strategy/` | Scored desires, forces of change, mass instincts, awareness levels and market sophistication |
| `avatars/` | Two core avatars and five sub-avatars, 19 angle files, a ranked-angles playbook per core avatar grouped by offer, a cross-avatar summary, and the (invented) research behind them |
| `testing/` | A creative tracker with three batch concepts, its coverage summary, and the learnings those batches produced |
| `meta.toml` | Meta launch settings with placeholder pixel and `fernwood.example` URLs; never launch from it |

## How the pieces connect

1. `avatars/research/review-mining-2026-07-20.md` supplies the customer language.
2. `avatars/core-low-waste-household/` and `avatars/core-careful-parent/` turn it into Core 5 profiles and situation-based sub-avatars, each passing the niche gap test.
3. Each sub-avatar has three angles per offer, ranked in `ranked-angles.md`.
4. `testing/creative-tracker.csv` logs three concepts: a Discovery batch (`c01`), a format test (`c02`) and a Deep Iteration (`c03`).
5. `testing/learnings.md` records the outcome: one winner, one execution loss kept alive, one strategy loss retired and replaced.

The worked examples in `engine/prompts/angles/generate-angles.md` and `engine/prompts/testing/process-learnings.md` point at these same files.

## A note on hooks

The pipeline in `engine/prompts/README.md` says hooks are born at ad assembly. The angle template still carries hook slots, so this example fills them with direct hooks to show what a finished angle file looks like. Treat them as a starting point for assembly, not a replacement for it.
