# Creative Tracker

Central log of every ad combination tried. Prevents duplication, reveals gaps, and tracks what's working.

**Source of truth:** `creative-tracker.csv` (same directory) -- one row per ad variant.
**Images live outside the repo.** This tracker records what was made, not the assets themselves.

---

## How to Use

### Adding a new batch

Append rows to `creative-tracker.csv` with these columns:

| Column | Description | Example |
|---|---|---|
| `batch` | Test batch ID | `test-{sub-avatar}-{YYYY-MM-DD}` |
| `date` | Date created | `2026-03-10` |
| `concept` | Batch concept: the big idea of one ad set, numbered. One concept is one ad set (see `concepts/angles-and-testing.md`) | `c01-refill-switchers-discovery` |
| `testing-method` | `discovery` / `deep-iteration` / `ab-split` (see `prompts/testing/methods.md`) | `discovery` |
| `sub-avatar` | Target sub-avatar | `sub-let-down-eco-switcher` |
| `core-avatar` | Parent core avatar | `core-low-waste-household` |
| `angle` | Angle slug | `proves-it-actually-cleans` |
| `product` | Product shown, slug of a file in `products/` | `all-purpose-spray` |
| `offer` | What the ad sells, slug of a file in `products/` or `offers/`; matches the angle's `offer` frontmatter | `starter-kit` |
| `variation` | Which execution of the angle this row is (hook, headline, or cut) | `hook-2` |
| `messaging-concept` | Messaging concept slug from `prompts/concepts/messaging/` | `i-accidentally-achieved-x` |
| `visual-format` | Visual concept slug from `prompts/concepts/visual/` | `annotated-lifestyle-hero` |
| `format` | Delivery format, from `concepts/formats/` | `static` / `video` / `carousel` / `email` |
| `channel` | Where it runs | `meta-paid` / `tiktok-paid` / `email` |
| `asset-ref` | Where the rendered asset lives (repo path, R2 key, or Drive link) | `batches/test-refill-2026-03-10/annotated-lifestyle-hero-hook-2_9x16.png` |
| `status` | `untested` / `testing` / `winner` / `loser` | `untested` |
| `result` | Brief outcome when tested | `2.1% CTR, strong hook` |
| `notes` | Anything else, including the loss type (`strategy` or `execution`) for losers | `Reworked headline after review` |

Leave a column empty rather than dropping it; every row must have all 18 fields. `scripts/check-knowledge.py` checks the header, the field count, and the `status` and `testing-method` values.

### Updating results

When ads go live or results come back, update `status` and `result` in the CSV.

### Reading coverage

Scan the CSV to answer:
- **Which sub-avatars have been tested?** Filter by `sub-avatar`.
- **Which angles are untouched?** Cross-reference against `ranked-angles.md`.
- **Which messaging x visual combos are overused?** Pivot on `messaging-concept` + `visual-format`.
- **Which offers has each sub-avatar seen?** Pivot on `sub-avatar` + `offer`.
- **Has this angle been tried in more than one format?** Filter by `angle`, read `format`. Needed before retiring an angle (see `concepts/execution.md`).
- **What's winning?** Filter `status = winner`.

---

## Coverage Summary

_Update this section as tests accumulate._

### Sub-Avatars Tested

| Sub-Avatar | Core Avatar | Batches | Angles Tried | Status |
|---|---|---|---|---|

### Messaging Concepts Used

| Concept | Times Used |
|---|---|

### Visual Formats Used

| Format | Times Used |
|---|---|

### Products

| Product | Times Used |
|---|---|

### Offers

| Offer | Times Used |
|---|---|

### Formats and Channels

| Format | Channel | Times Used |
|---|---|---|

---

## Rules

- **Update the CSV every time you assemble ads.** The tracker is only useful if it's current.
- **Check before creating.** Before assembling a new batch, filter the CSV to confirm the combination hasn't been tried.
- **Status flow:** `untested` -> `testing` -> `winner` / `loser`
- **One row per ad variant.** If the same angle x messaging x visual is generated with different copy, add a separate row with a new `variation` value.
- **One concept is one ad set.** Rows that share a `concept` share an ad set, so they share one testing method and one format. A format change is its own concept.
