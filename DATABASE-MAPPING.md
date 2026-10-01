# Database Mapping: This Repo <-> meta-ads App

This repo holds stable strategic context (brand voice, avatar profiles, angle strategy). The meta-ads database holds execution artifacts that change per ad run (ad records, metrics, renders, generated copy). The two systems reference each other but serve different purposes.

## Field Mapping

| This Repo | meta-ads DB | Notes |
|---|---|---|
| `products/` | `products`, `product_images`, `product_renders` | .md has strategic framing; DB has SKU, images, renders. Link via `sku`. |
| `offers/` | `bundles`, `bundle_items` | .md has positioning + target avatars; DB has bundle composition. |
| `brand/` | `brandConfig` in `src/lib/brand/config.ts` | Full voice/visual docs here; app hardcodes colors/fonts/logo. |
| `avatars/` | `ad_analyses.desire_tapped`, `.pain_addressed` | Avatars define desires/pains. Ad analyses reference same concepts. |
| `angles/` | `creative_briefs.what_testing` | Angles = strategic input; briefs = execution output. |
| `concepts/` | `creative_briefs.format` | Frameworks/formats inform brief generation. |
| `testing/` | `brief_runs`, `ad_metrics` | Test plans reference batch IDs -> `brief_runs.id`. Learnings distilled from metrics. |
| `ads/` | `ads`, `generated_ads` | Ad folders mirror DB records. `meta.json` links back to angles/avatars. |
| `research/` | No direct mapping | Pure strategic research -> feeds into avatars/angles/products. |

## Decision Rule

- **If it changes per-ad-run -> DB.** Ad records, metrics, renders, generated copy, brief runs.
- **If it's stable strategic context -> this repo.** Brand voice, product knowledge, avatar profiles, angle strategy, test learnings.

## Linking Records

- **Products:** Match via `sku` field. The product markdown filename should correspond to the SKU stored in the meta-ads `products` table.
- **Offers:** Match via bundle name. The offer markdown filename should match the bundle name in `bundles`.
- **Angles:** Angle names in `angles/angles.md` should match `creative_briefs.what_testing` values in the DB.
- **Test batches:** Reference `brief_runs.id` in `testing/learnings.md` to tie learnings back to specific runs.
