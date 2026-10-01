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
| `sub-avatar` | Target sub-avatar | `sub-let-down-eco-switcher` |
| `core-avatar` | Parent core avatar | `core-low-waste-household` |
| `angle` | Angle slug | `proves-it-actually-cleans` |
| `messaging-concept` | Messaging concept slug | `i-accidentally-achieved-x` |
| `visual-format` | Visual format slug | `annotated-lifestyle-hero` |
| `product-or-offer` | Product or offer used | `starter-kit` |
| `status` | `untested` / `testing` / `winner` / `loser` | `untested` |
| `result` | Brief outcome when tested | `2.1% CTR, strong hook` |
| `notes` | Anything else | `Reworked headline after review` |

### Updating results

When ads go live or results come back, update `status` and `result` in the CSV.

### Reading coverage

Scan the CSV to answer:
- **Which sub-avatars have been tested?** Filter by `sub-avatar`.
- **Which angles are untouched?** Cross-reference against `ranked-angles.md`.
- **Which messaging x visual combos are overused?** Pivot on `messaging-concept` + `visual-format`.
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

### Products / Offers

| Product/Offer | Times Used |
|---|---|

---

## Rules

- **Update the CSV every time you assemble ads.** The tracker is only useful if it's current.
- **Check before creating.** Before assembling a new batch, filter the CSV to confirm the combination hasn't been tried.
- **Status flow:** `untested` -> `testing` -> `winner` / `loser`
- **One row per ad variant.** If the same angle x messaging x visual is generated with different copy, add a separate row with a note.
